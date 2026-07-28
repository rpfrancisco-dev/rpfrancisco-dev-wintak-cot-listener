"""In-memory device registry + status sweeper + snapshot broadcast."""
from __future__ import annotations

import asyncio
import logging

from channels.layers import get_channel_layer
from django.conf import settings

from .cot import _iso_to_ms, to_mgrs, utc_now_ms

log = logging.getLogger("monitor.registry")

GROUP = "devices"

STATUS_ONLINE = "online"
STATUS_STALE = "stale"
STATUS_OFFLINE = "offline"


class DeviceRegistry:
    def __init__(self):
        self.devices: dict[str, dict] = {}
        self.tak_state = "connecting"
        self.tak_error: str | None = None
        self.udp_state = "disabled"
        self.udp_error: str | None = None
        self.marti_state = "disabled"
        self.marti_error: str | None = None
        self.removed_total = 0
        self._dirty = asyncio.Event()

    # -- updates from a CoT source --------------------------------------
    def upsert(
        self,
        parsed: dict,
        transport: str | None = None,
        src_ip: str | None = None,
    ) -> None:
        """Merge one CoT event.

        `transport` is how *this* monitor observed the device ("SSL", "UDP",
        …); a device seen on several feeds accumulates them, shown joined in
        the protocol column. `src_ip` is a datagram source address, used as a
        fallback when the CoT itself carries no endpoint IP.
        """
        now = utc_now_ms()
        record = self.devices.get(parsed["uid"])
        if record is None:
            record = {"first_seen": now, "transports": []}
            self.devices[parsed["uid"]] = record
        # Presence pings can omit detail fields a full update carried.
        for key, value in parsed.items():
            if value is not None or key not in record:
                record[key] = value
        if src_ip and not record.get("ip"):
            record["ip"] = src_ip
        record["last_seen"] = now
        if parsed.get("lat") is not None or "mgrs" not in record:
            record["mgrs"] = to_mgrs(record.get("lat"), record.get("lon"))

        # Display protocol: prefer observed transports; fall back to the
        # endpoint-derived protocol from the CoT itself.
        transports = record.setdefault("transports", [])
        if transport and transport not in transports:
            transports.append(transport)
        if transports:
            record["protocol"] = ", ".join(transports)

        record["status"] = self._status_of(record, now)
        self._dirty.set()

    def set_tak_state(self, state: str, error: str | None = None) -> None:
        if (state, error) != (self.tak_state, self.tak_error):
            self.tak_state = state
            self.tak_error = error
            self._dirty.set()

    def set_udp_state(self, state: str, error: str | None = None) -> None:
        if (state, error) != (self.udp_state, self.udp_error):
            self.udp_state = state
            self.udp_error = error
            self._dirty.set()

    def set_marti_state(self, state: str, error: str | None = None) -> None:
        if (state, error) != (self.marti_state, self.marti_error):
            self.marti_state = state
            self.marti_error = error
            self._dirty.set()

    # -- authoritative client list from the Marti API -------------------
    def merge_marti(self, endpoints: list[dict]) -> None:
        now = utc_now_ms()
        seen = set()
        for e in endpoints:
            uid = e.get("uid")
            if not uid:
                continue
            seen.add(uid)
            record = self.devices.get(uid)
            if record is None:
                # Never resurrect a client the server itself reports gone —
                # offline devices are pruned, and re-adding Disconnected
                # entries here would bring them straight back.
                if e.get("lastStatus") == "Disconnected":
                    continue
                record = {"first_seen": now, "transports": []}
                self.devices[uid] = record
            record["marti"] = True
            record["server_status"] = e.get("lastStatus")  # Connected/Disconnected
            record["username"] = e.get("username") or record.get("username")
            # The server's label/team/role fill in when CoT hasn't provided them.
            if e.get("callsign") and not record.get("callsign"):
                record["callsign"] = e["callsign"]
            if e.get("team"):
                record.setdefault("team", e["team"])
            if e.get("role"):
                record.setdefault("role", e["role"])
            last_event = _iso_to_ms(e.get("lastEventTime"))
            record["server_last_event"] = last_event
            # Marti-only client (no CoT yet): seed last_seen from the server.
            if "last_seen" not in record:
                record["last_seen"] = last_event or now
            record["status"] = self._status_of(record, now)

        # Clients that dropped off the server list: a Marti-only entry is gone,
        # so remove it; one we've also seen via CoT reverts to CoT-based status.
        for uid in list(self.devices):
            record = self.devices[uid]
            if record.get("marti") and uid not in seen:
                if not record.get("transports") and record.get("lat") is None:
                    del self.devices[uid]
                else:
                    record["marti"] = False
                    record["server_status"] = None
        self._dirty.set()

    # -- status ----------------------------------------------------------
    def _status_of(self, record: dict, now: int) -> str:
        base = self._cot_status(record, now)
        # The Marti API's connection state is authoritative when present.
        server = record.get("server_status")
        if server == "Disconnected":
            return STATUS_OFFLINE
        if server == "Connected" and base == STATUS_OFFLINE:
            return STATUS_ONLINE
        return base

    def _cot_status(self, record: dict, now: int) -> str:
        stale_at = record.get("stale_at")
        grace_ms = settings.TAK_OFFLINE_GRACE_SECONDS * 1000
        last_seen = record.get("last_seen", now)
        # No stale time on record: fall back to time-since-last-update.
        if not stale_at:
            age = now - last_seen
            if age < grace_ms:
                return STATUS_ONLINE
            return STATUS_STALE if age < 2 * grace_ms else STATUS_OFFLINE
        if now < stale_at:
            return STATUS_ONLINE
        if now < stale_at + grace_ms and now - last_seen < 5 * grace_ms:
            return STATUS_STALE
        return STATUS_OFFLINE

    def _refresh_statuses(self) -> bool:
        now = utc_now_ms()
        changed = False
        for uid, record in list(self.devices.items()):
            status = self._status_of(record, now)
            if status == STATUS_OFFLINE:
                # Offline means the server no longer vouches for the device
                # (Marti says Disconnected, or its CoT lapsed past the grace)
                # — remove it, mirroring the plotted-object check. It comes
                # back the moment it reconnects.
                del self.devices[uid]
                self.removed_total += 1
                log.info(
                    "pruned offline device %s (%s)", uid, record.get("callsign")
                )
                changed = True
            elif status != record.get("status"):
                record["status"] = status
                changed = True
        return changed

    # -- snapshot --------------------------------------------------------
    def snapshot(self) -> dict:
        devices = sorted(
            self.devices.values(),
            key=lambda d: (
                {STATUS_ONLINE: 0, STATUS_STALE: 1}.get(d.get("status"), 2),
                (d.get("callsign") or d.get("uid") or "").lower(),
            ),
        )
        online = sum(1 for d in devices if d["status"] == STATUS_ONLINE)
        stale = sum(1 for d in devices if d["status"] == STATUS_STALE)
        offline = sum(1 for d in devices if d["status"] == STATUS_OFFLINE)
        removed = self.removed_total
        return {
            "type": "snapshot",
            "now": utc_now_ms(),
            "tak": {
                "state": self.tak_state,
                "url": settings.TAK_WS_URL,
                "error": self.tak_error,
            },
            "udp": {
                "state": self.udp_state,
                "url": settings.TAK_UDP_URL,
                "error": self.udp_error,
            },
            "marti": {
                "state": self.marti_state,
                "url": settings.TAK_MARTI_URL,
                "error": self.marti_error,
            },
            "summary": {
                "total": len(devices),
                "online": online,
                "stale": stale,
                "offline": offline,
                "removed": removed,
                "objects": object_registry.count(),
            },
            "objcheck": object_registry.check_summary(),
            "devices": devices,
            "objects": object_registry.to_featurecollection(),
        }

    # -- broadcast loop --------------------------------------------------
    async def broadcast(self) -> None:
        layer = get_channel_layer()
        await layer.group_send(GROUP, {"type": "devices.update", "payload": self.snapshot()})

    async def run_sweeper(self) -> None:
        """Re-evaluate stale/offline every second; push on any change."""
        while True:
            try:
                await asyncio.wait_for(self._dirty.wait(), timeout=1.0)
                data_changed = True
            except asyncio.TimeoutError:
                data_changed = False
            self._dirty.clear()
            status_changed = self._refresh_statuses()
            if data_changed or status_changed:
                await self.broadcast()
                await asyncio.sleep(0.5)  # coalesce bursts of CoT updates


registry = DeviceRegistry()


class ObjectRegistry:
    """Plotted map objects (markers, drawings) as GeoJSON features, by uid.

    Fed by both the live CoT stream and the statesaver poller. Shares the
    device registry's dirty flag so a change here also triggers a broadcast.
    """

    def __init__(self):
        self.features: dict[str, dict] = {}
        self.check_state = "disabled"
        self.check_error: str | None = None
        self.last_check: int | None = None
        self.removed_total = 0

    def upsert(self, feature: dict | None, source: str | None = None) -> None:
        if not feature:
            return
        props = feature.get("properties", {})
        uid = props.get("uid")
        if not uid:
            return
        now = utc_now_ms()
        props["last_seen"] = now
        # Carry check bookkeeping across re-parses (the statesaver poller
        # rebuilds the feature every tick) and stamp which feed vouched for it.
        old = self.features.get(uid)
        if old is not None:
            props.setdefault("sources", old["properties"].get("sources", {}))
            props.setdefault("check", old["properties"].get("check"))
        if source:
            props.setdefault("sources", {})[source] = now
        self.features[uid] = feature
        registry._dirty.set()

    def remove(self, uid: str | None) -> None:
        if uid and self.features.pop(uid, None) is not None:
            registry._dirty.set()

    def count(self) -> int:
        return len(self.features)

    # -- routine check ---------------------------------------------------
    def reconcile(
        self,
        statesaver_uids: set[str] | None,
        fresh_ms: int,
        max_misses: int,
        error: str | None = None,
    ) -> list[str]:
        """One routine-check pass over every plotted object.

        `statesaver_uids` is the set of uids currently visible in WinTAK's
        statesaver (None if the read failed — absence then proves nothing).
        Each object gets a `check` verdict in its properties:

        - ``verified``   still in the statesaver, or refreshed over the CoT
                         stream within `fresh_ms`
        - ``unverified`` stream-only object the statesaver never held; kept
                         until its CoT stale time passes
        - ``expired``    past its CoT stale time
        - ``missing``    the statesaver used to vouch for it and no longer does

        A ``missing`` object is pruned immediately — the statesaver was read
        successfully and the map no longer has it. ``expired`` objects get
        `max_misses` consecutive passes of grace first. Pruned uids are
        returned. (A wrongly-pruned object self-heals: the statesaver poller
        re-adds it on its next tick.)
        """
        now = utc_now_ms()
        self.last_check = now
        self.check_error = error
        self.check_state = "error" if error else "ok"

        removed = []
        for uid, feature in list(self.features.items()):
            props = feature["properties"]
            check = props.get("check") or {"misses": 0}
            sources = props.get("sources", {})
            stale_at = props.get("stale_at")

            in_saver = statesaver_uids is not None and uid in statesaver_uids
            stream_fresh = any(
                now - ts < fresh_ms
                for src, ts in sources.items()
                if src != "statesaver"
            )
            expired = bool(stale_at) and stale_at < now
            saver_backed = "statesaver" in sources

            if in_saver or (stream_fresh and not expired):
                check.update(state="verified", misses=0)
            elif expired:
                check.update(state="expired", misses=check.get("misses", 0) + 1)
            elif statesaver_uids is None:
                # Statesaver unreadable this pass: keep the previous verdict,
                # never count a miss on missing evidence.
                check.setdefault("state", "unverified")
            elif saver_backed:
                check.update(state="missing", misses=check.get("misses", 0) + 1)
            else:
                check.update(state="unverified", misses=0)

            check["checked_at"] = now
            props["check"] = check
            if check["state"] == "missing" or check.get("misses", 0) >= max_misses:
                del self.features[uid]
                removed.append(uid)

        self.removed_total += len(removed)
        registry._dirty.set()
        return removed

    def check_summary(self) -> dict:
        counts = {"verified": 0, "unverified": 0, "missing": 0, "expired": 0}
        for feature in self.features.values():
            state = (feature["properties"].get("check") or {}).get("state")
            if state in counts:
                counts[state] += 1
        return {
            "state": self.check_state,
            "error": self.check_error,
            "last_check": self.last_check,
            "interval": settings.TAK_OBJECT_CHECK_SECONDS,
            "counts": counts,
            "removed_total": self.removed_total,
        }

    def to_featurecollection(self) -> dict:
        return {
            "type": "FeatureCollection",
            "features": sorted(
                self.features.values(),
                key=lambda f: (
                    f["properties"].get("kind") or "",
                    (f["properties"].get("callsign") or f["properties"].get("uid") or "").lower(),
                ),
            ),
        }


object_registry = ObjectRegistry()
