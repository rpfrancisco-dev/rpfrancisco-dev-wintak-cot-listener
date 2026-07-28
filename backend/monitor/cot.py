"""Decode CoT frames (TAK protobuf or XML) into flat device dicts."""
from __future__ import annotations

import ipaddress
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

log = logging.getLogger("monitor.cot")

try:
    import takproto
except ImportError:  # pragma: no cover
    takproto = None

try:
    from takproto.proto import TakMessage
except ImportError:  # pragma: no cover
    TakMessage = None

try:
    import mgrs as _mgrs_lib

    _MGRS = _mgrs_lib.MGRS()
except ImportError:  # pragma: no cover
    _MGRS = None

# Endpoint suffix -> display protocol. "stcp" is TAK's streaming CoT, which
# rides the server's TLS connection.
_PROTO_MAP = {
    "stcp": "SSL",
    "tls": "SSL",
    "ssl": "SSL",
    "tcp": "TCP",
    "udp": "UDP",
}


def _parse_endpoint(endpoint: str | None):
    """'192.168.1.10:4242:tcp' or '*:-1:stcp' -> (ip, protocol).

    The host slot is only kept when it's a real IP address; TAK also uses
    keyword hosts like 'tcpsrcreply' (reply on the source connection) and '*',
    which are not addresses and must not be shown as one.
    """
    if not endpoint:
        return None, None
    parts = endpoint.split(":")
    ip = parts[0] if parts and _is_ip(parts[0]) else None
    proto = None
    if len(parts) >= 3:
        proto = _PROTO_MAP.get(parts[2].lower(), parts[2].upper())
    return ip, proto


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _norm_point(lat, lon):
    """Treat the 0,0 'no GPS fix' sentinel as no position (both -> None)."""
    if lat is None or lon is None:
        return None, None
    if lat == 0 and lon == 0:
        return None, None
    return lat, lon


def _iso_to_ms(value: str | None) -> int | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def classify(uid: str, cot_type: str, how: str, has_takv: bool) -> str | None:
    """Route a CoT event: 'device' | 'object' | 'delete' | None (ignore).

    Live clients ('device') are atoms that carry a <takv> block (a real TAK
    client) or machine-GPS provenance (how 'm-*'). Hand-placed atoms without
    takv, plus drawings/shapes/markers, are plotted 'object's. 't-x-d-d' is a
    delete. GeoChat, SPI pointers, pings, and file/ack traffic are ignored.
    """
    if not uid or not cot_type:
        return None
    if uid.startswith("GeoChat") or ".SPI" in uid or uid.endswith("-ping"):
        return None
    if cot_type.startswith("t-x-d-d"):
        return "delete"
    if cot_type.startswith(("b-t-f", "b-f-t", "y-", "t-x-c")):
        return None  # chat, file transfer, acks, control
    if cot_type.startswith("a-"):
        return "device" if (has_takv or (how or "").startswith("m")) else "object"
    if cot_type.startswith(("u-", "b-", "g-")):
        return "object"  # drawings/shapes, markers/routes, geofences
    return None


def _decode_takmessage(data: bytes):
    """Bytes -> TakMessage (mesh-framed or bare), or None."""
    msg = None
    if takproto is not None:
        try:
            msg = takproto.parse_proto(bytearray(data))
        except Exception:
            msg = None
    if (msg is None or msg == -1) and TakMessage is not None:
        try:
            candidate = TakMessage()
            candidate.ParseFromString(bytes(data))
            if candidate.cotEvent.uid:
                msg = candidate
        except Exception:
            return None
    return None if (msg is None or msg == -1) else msg


def _device_from_pb(ev) -> dict:
    contact, takv, group = ev.detail.contact, ev.detail.takv, ev.detail.group
    ip, proto = _parse_endpoint(contact.endpoint or None)
    lat, lon = _norm_point(ev.lat or None, ev.lon or None)
    return {
        "uid": ev.uid,
        "cot_type": ev.type,
        "callsign": contact.callsign or None,
        "ip": ip,
        "protocol": proto,
        "platform": takv.platform or None,
        "device": takv.device or None,
        "os": takv.os or None,
        "version": takv.version or None,
        "team": group.name or None,
        "role": group.role or None,
        "lat": lat,
        "lon": lon,
        "stale_at": ev.staleTime or None,
        "start_at": ev.startTime or None,
    }


def _device_from_xml(root) -> dict:
    detail = root.find("detail")
    contact = detail.find("contact") if detail is not None else None
    takv = detail.find("takv") if detail is not None else None
    group = detail.find("__group") if detail is not None else None
    point = root.find("point")
    ip, proto = _parse_endpoint(contact.get("endpoint") if contact is not None else None)

    def _f(el, attr):
        return el.get(attr) if el is not None else None

    lat = float(point.get("lat")) if point is not None else None
    lon = float(point.get("lon")) if point is not None else None
    lat, lon = _norm_point(lat, lon)
    return {
        "uid": root.get("uid", ""),
        "cot_type": root.get("type", ""),
        "callsign": _f(contact, "callsign"),
        "ip": ip,
        "protocol": proto,
        "platform": _f(takv, "platform"),
        "device": _f(takv, "device"),
        "os": _f(takv, "os"),
        "version": _f(takv, "version"),
        "team": _f(group, "name"),
        "role": _f(group, "role"),
        "lat": lat,
        "lon": lon,
        "stale_at": _iso_to_ms(root.get("stale")),
        "start_at": _iso_to_ms(root.get("start")),
    }


def parse_protobuf(data: bytes) -> dict | None:
    """Decode a binary TAK protocol frame into a device dict, or None."""
    msg = _decode_takmessage(data)
    if msg is None:
        return None
    ev = msg.cotEvent
    if classify(ev.uid, ev.type, ev.how, bool(ev.detail.takv.platform)) != "device":
        return None
    return _device_from_pb(ev)


def parse_xml(text: str) -> dict | None:
    """Decode a CoT XML <event> into a device dict, or None."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    if root.tag != "event":
        return None
    has_takv = root.find("detail/takv") is not None
    if classify(root.get("uid", ""), root.get("type", ""), root.get("how", ""), has_takv) != "device":
        return None
    return _device_from_xml(root)


# --- plotted objects -> GeoJSON Feature ------------------------------------
_AFFIL = {
    "f": "friendly", "h": "hostile", "n": "neutral", "u": "unknown",
    "p": "pending", "a": "assumed", "s": "suspect", "j": "joker", "k": "faker",
}


def _affiliation(cot_type: str) -> str:
    parts = cot_type.split("-")
    if len(parts) > 1 and parts[0] == "a":
        return _AFFIL.get(parts[1], "other")
    return "n/a"


def _link_vertices(detail) -> list[list[float]]:
    """<link point='lat,lon'> vertices (drawings/routes) as [lon, lat] pairs."""
    if detail is None:
        return []
    verts = []
    for link in detail.findall("link"):
        p = link.get("point")
        if not p:
            continue
        try:
            lat, lon, *_ = p.split(",")
            verts.append([float(lon), float(lat)])
        except ValueError:
            continue
    return verts


def _ms_to_iso(ms: int | None) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _feature_from_event(root) -> dict | None:
    """Build a GeoJSON Feature from a CoT <event> element, or None."""
    if root is None or root.tag != "event":
        return None
    cot_type = root.get("type", "")
    detail = root.find("detail")
    point = root.find("point")

    verts = _link_vertices(detail)
    if len(verts) >= 2:
        area = cot_type.startswith(("u-d-f", "u-d-r", "u-d-c", "u-d-p"))
        closed = verts[0] == verts[-1]
        if (area or closed) and len(verts) >= 3:
            ring = verts if closed else verts + [verts[0]]
            geom = {"type": "Polygon", "coordinates": [ring]}
        else:
            geom = {"type": "LineString", "coordinates": verts}
    elif point is not None:
        try:
            lat, lon = _norm_point(float(point.get("lat")), float(point.get("lon")))
        except (TypeError, ValueError):
            lat = lon = None
        if lat is None:
            return None
        geom = {"type": "Point", "coordinates": [lon, lat]}
    else:
        return None

    # Representative point (label / MGRS): the point, or the vertex centroid.
    if geom["type"] == "Point":
        clon, clat = geom["coordinates"]
    else:
        ring = geom["coordinates"][0] if geom["type"] == "Polygon" else geom["coordinates"]
        clon = sum(c[0] for c in ring) / len(ring)
        clat = sum(c[1] for c in ring) / len(ring)

    contact = detail.find("contact") if detail is not None else None
    usericon = detail.find("usericon") if detail is not None else None
    remarks = detail.findtext("remarks") if detail is not None else None
    color = detail.find("color") if detail is not None else None
    stroke = detail.find("strokeColor") if detail is not None else None

    return {
        "type": "Feature",
        "geometry": geom,
        "properties": {
            "uid": root.get("uid"),
            "cot_type": cot_type,
            "callsign": (contact.get("callsign") if contact is not None else None) or None,
            "kind": "drawing" if geom["type"] != "Point" or cot_type.startswith("u-") else "marker",
            "affiliation": _affiliation(cot_type),
            "how": root.get("how") or None,
            "symbol_2525": usericon.get("iconsetpath") if usericon is not None else None,
            "remarks": (remarks or "").strip() or None,
            "color": (color.get("argb") or color.get("value")) if color is not None
                     else (stroke.get("value") if stroke is not None else None),
            "lat": round(clat, 7),
            "lon": round(clon, 7),
            "mgrs": to_mgrs(clat, clon),
            "stale_at": _iso_to_ms(root.get("stale")),
        },
    }


def feature_from_xml(text: str) -> dict | None:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    return _feature_from_event(root)


def feature_from_protobuf(data: bytes) -> dict | None:
    msg = _decode_takmessage(data)
    if msg is None:
        return None
    ev = msg.cotEvent
    detail_xml = ev.detail.xmlDetail or ""
    # Structured contact isn't in xmlDetail; splice it in for the label.
    if ev.detail.contact.callsign and "<contact" not in detail_xml:
        detail_xml += f'<contact callsign="{ev.detail.contact.callsign}"/>'
    xml = (
        f'<event uid="{ev.uid}" type="{ev.type}" how="{ev.how}" '
        f'stale="{_ms_to_iso(ev.staleTime)}">'
        f'<point lat="{ev.lat}" lon="{ev.lon}"/>'
        f"<detail>{detail_xml}</detail></event>"
    )
    return feature_from_xml(xml)


def _deleted_uid(root) -> str | None:
    """UID targeted by a t-x-d-d delete event (from its <link uid=…>)."""
    if root is None:
        return None
    link = root.find("detail/link")
    return link.get("uid") if link is not None else root.get("uid")


def parse_frame(frame) -> tuple[str, object] | None:
    """Unified dispatch: ('device', dict) | ('object', feature) | ('delete', uid).

    `frame` is protobuf bytes or an XML string.
    """
    if isinstance(frame, (bytes, bytearray)):
        msg = _decode_takmessage(frame)
        if msg is None:
            return None
        ev = msg.cotEvent
        cat = classify(ev.uid, ev.type, ev.how, bool(ev.detail.takv.platform))
        if cat == "device":
            return ("device", _device_from_pb(ev))
        if cat == "object":
            feat = feature_from_protobuf(frame)
            return ("object", feat) if feat else None
        if cat == "delete":
            return ("delete", ev.uid)
        return None
    try:
        root = ET.fromstring(frame)
    except ET.ParseError:
        return None
    if root.tag != "event":
        return None
    cat = classify(
        root.get("uid", ""), root.get("type", ""), root.get("how", ""),
        root.find("detail/takv") is not None,
    )
    if cat == "device":
        return ("device", _device_from_xml(root))
    if cat == "object":
        feat = _feature_from_event(root)
        return ("object", feat) if feat else None
    if cat == "delete":
        return ("delete", _deleted_uid(root))
    return None


def to_mgrs(lat, lon) -> str | None:
    """Lat/lon -> spaced MGRS string ('51P TS 86963 16019'), 1 m precision.

    CoT uses 0,0 and out-of-range sentinels (e.g. 9999999) for 'no GPS fix';
    those return None rather than a bogus grid off the coast of Africa.
    """
    if _MGRS is None or lat is None or lon is None:
        return None
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    try:
        raw = _MGRS.toMGRS(lat, lon, MGRSPrecision=5)  # e.g. 51PTS8696316019
    except Exception:
        return None
    m = re.match(r"^(\d{1,2}[A-Z])([A-Z]{2})(\d+)$", raw)
    if not m:
        return raw
    digits = m.group(3)
    half = len(digits) // 2
    return f"{m.group(1)} {m.group(2)} {digits[:half]} {digits[half:]}"


def utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)
