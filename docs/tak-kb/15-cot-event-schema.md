# 15 — CoT Event Schema (XML)

Primary sources: the MITRE **CoT Base-Event Schema v2.0** (Public Release, MITRE case #11-3895), plus the TAK detail XSDs, both in the ATAK-CIV repo under `takcot/`. TAK uses MITRE CoT 2.0 and adds TAK-specific `<detail>` children.

## 1. Skeleton

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<event version="2.0" uid="ANDROID-589520ccfcd20f01" type="a-f-G-U-C" how="m-g"
       time="2020-12-16T19:50:57.629Z" start="2020-12-16T19:50:57.629Z" stale="2020-12-16T19:56:57.629Z">
  <point lat="38.8977" lon="-77.0365" hae="15.0" ce="9.9" le="9999999.0"/>
  <detail>
    <takv device="SAMSUNG SM-G998U" platform="ATAK-CIV" os="33" version="4.10.0"/>
    <contact callsign="HOPE" endpoint="*:-1:stcp"/>
    <__group name="Cyan" role="Team Member"/>
    <precisionlocation geopointsrc="GPS" altsrc="GPS"/>
    <status battery="88"/>
    <track course="270.0" speed="1.2"/>
    <uid Droid="HOPE"/>
  </detail>
</event>
```
(Illustrative values. The structure and attribute names come from the XSDs below.)

`<event>` holds exactly one `<point>` and at most one `<detail>` (`xs:all`).

## 2. `<event>` attributes

| Attribute | Req | Format / meaning |
|---|---|---|
| `version` | yes | decimal ≥ 2 (`"2.0"`) |
| `uid` | yes | Globally unique ID for *this piece of information*. Several events can share a UID; **the latest (by timestamp) overwrites all previous events for that UID.** |
| `type` | yes | Hierarchical, `-`-delimited, optionally followed by `;<extra>` (regex `\w+(-\w+)*(;[^;]*)?`). See 16. |
| `time` | yes | When the event was generated ("birth"). |
| `start` | yes | Start of the validity interval. |
| `stale` | yes | End of the validity interval. After this the event is no longer valid. |
| `how` | yes | How the coordinates were produced (regex `\w(-\w+)*`). See §4. |
| `access` | no | Free-text access/handling marking (e.g. unrestricted, nato). TAK Server's proto also carries `caveat` and `releaseableTo` (see 17). |
| `qos` | no | `priority-overtaking-assurance`, e.g. `1-r-c` (see §5). |
| `opex` | no | `o[-name]` operations, `e[-nick]` exercise, `s[-nick]` simulation. Absent = "no statement". |

### Times
- ISO 8601 UTC: `CCYY-MM-DDThh:mm:ss[.fff…]Z`. Fractional seconds are optional and can have any number of digits. `2002-10-05T18:00:23Z`, `…23.12Z` and `…23.123456Z` are all valid.
- In CoT 2.0, `time` is when the event was created, and `start`/`stale` give the window when it's valid. Older versions (1.1) used `time`/`stale` for that window instead.
- In TAK protobuf these become `sendTime`/`startTime`/`staleTime` in **milliseconds since the Unix epoch** (17).

## 3. `<point>`

| Attr | Meaning |
|---|---|
| `lat` | WGS-84 decimal degrees, −90…+90 |
| `lon` | WGS-84 decimal degrees, −180…+180 |
| `hae` | Height above the WGS-84 ellipsoid, metres |
| `ce` | Circular error (metres): a radius around the point. When it is an error, it is 1σ. |
| `le` | Linear error (metres) on `hae`. Together with `ce` it defines a cylinder around the point. |

All five are required. TAK's convention for "unknown" is **`9999999.0`** (PyTAK's `DEFAULT_COT_VAL`). The TAK proto comment says `999999`. Treat any value ≥ 999999 as unknown. Control messages (e.g. protocol negotiation, 17) use `lat=0 lon=0 hae=0 ce=999999 le=999999`. A `0,0` position usually means "no fix", not real coordinates.

## 4. `how` codes (MITRE)

| Code | Meaning |
|---|---|
| `h` | human entered or modified |
| `h-e` | estimated (a guess by the user) |
| `h-c` | calculated by hand |
| `h-t` | transcribed (voice, paper…) |
| `h-p` | cut and paste from another window |
| `m` | machine generated |
| `m-i` | mensurated (from imagery) |
| `m-g` | derived from a GPS receiver |
| `m-m` | magnetic sources |
| `m-s` | simulated |
| `m-f` | fused (corroborated from multiple sources) |
| `m-c` | configured (out of a configuration file) |
| `m-p` | predicted (e.g. a tracker) |
| `m-r` | relayed (imported from another system / gateway) |

TAK-observed values not defined in the MITRE list: **`h-g-i-g-o`** is used by ATAK for hand-placed markers in the official example CoT. taky also uses it for its pong. Drawings use **`h-e`**. Self-SA from a device's GPS is normally `m-g`.

## 5. `qos` (MITRE)
`<priority 0-9>-<overtaking>-<assurance>`
- priority: 9 highest … 0 lowest.
- overtaking: `r` replace (new deletes old), `f` follow (keep order), `i` independent.
- assurance: `g` guaranteed, `d` deadline (drop only after stale), `c` congestion (drop when congested).
Example from the schema: a blue-force tracker sends `1-r-c` routinely, `5-r-d` occasionally, and `9-r-g` for a mayday.

## 6. `<detail>`
MITRE leaves `<detail>` open (`xs:any`, lax). TAK defines children in `takcot/xsd/details/*.xsd`. The ones a listener most often needs:

| Element | Attributes (req **bold**) | Notes |
|---|---|---|
| `<contact>` | **`callsign`**, `endpoint`, `emailAddress`, `phone`, `xmppUsername` | `endpoint` looks like `host:port:proto`, e.g. `192.168.1.10:4242:tcp`. Over a server connection, `*:-1:stcp` is commonly seen. That's an observed convention, not part of the schema. |
| `<__group>` | **`name`**, **`role`** | Team colour and role (valid values in 00 §8 / 08). |
| `<takv>` | **`platform`**, **`version`**, `device`, `os` | Marks a real TAK client (ATAK-CIV, WinTAK-CIV, iTAK, …). |
| `<track>` | **`course`**, **`speed`**, `slope` | course in degrees, speed in m/s. |
| `<status>` | `battery` (int), `readiness` (bool) | |
| `<precisionlocation>` | **`altsrc`**, `geopointsrc`, `PRECISE_IMAGE_FILE*` | altsrc values: `???`, `DTED0-3`, `LIDAR`, `USER`, `GPS`, `SRTM1`, `COT`, `CALC`, `ESTIMATED`, `RTK`, `DGPS`, `GPS_PPS` |
| `<uid>` | **`Droid`**, `nett` | `Droid` = the callsign/device name. |
| `<link>` | **`uid`**, **`type`**, **`relation`**, `parent_callsign`, `production_time`, `callsign`, `remarks`, `point` | Ties an object to its creator (`relation="p-p"` = parent/producer) or holds route/shape points (`point="lat,lon[,hae]"`). For `t-x-d-d` deletes it points at the UID being deleted. |
| `<remarks>` | text content; `source`, `sourceID`, `time`, `to` | Free text (also carries GeoChat message bodies). |
| `<usericon>` | **`iconsetpath`** | 2525 markers: `COT_MAPPING_2525B/a-<affil>/a-<affil>-…`; spot markers: `COT_MAPPING_SPOTMAP/b-m-p-s-m/<int RGB>`; icon sets: `<iconset-uid>/<group>/<file>.png` |
| `<color>` | **`argb`** (signed int) | Marker colour. |
| `<strokeColor>`, `<fillColor>`, `<strokeWeight>`, `<labels_on>` | `value` | Drawing styling (seen in the official examples). |
| `<shape>` | `<polyline closed=…><vertex lat lon hae/>…` **or** `<ellipse major minor angle/>` + `<link …><Style><LineStyle/><PolyStyle/></Style></link>` | Circles/ellipses (`u-d-c-c`, `u-r-b-c-c`). |
| `<archive/>` | — | Tells clients to keep the object (persist it). |
| `<emergency>` | text; `type`, `cancel` (bool) | 911 / emergency alerts (16). |
| `<__chat>` | **`chatroom`**, **`groupOwner`**, **`id`**, **`senderCallsign`**, `parent`, `messageId`, `deleteChild`; child `<chatgrp uid0 uid1 … id>` | GeoChat (`b-t-f`). |
| `<__video>` | **`url`** | Video feed link. |
| `<__geofence>` | — | Geofence on a drawing. |
| `<marti><dest callsign="…"/></marti>` | — | Directed delivery: the server sends only to the listed destinations (also `uid=` and `mission=` forms). TAK Server removes `<marti>` before storing or relaying. |

Typical `<detail>` children by object type, from the official "CoT Types Data Package" examples:

| Type | Detail children |
|---|---|
| Marker (`a-u-G`, `a-n-G`, `b-m-p-s-m`) | `archive, color, contact, link, precisionlocation, remarks, status, usericon` |
| Route `b-m-r` | `__navcues, __routeinfo, archive, color, contact, labels_on, link (one per point), link_attr, remarks, strokeColor, strokeWeight` |
| Circle `u-d-c-c` | `shape(ellipse+link/Style), archive, color, contact, fillColor, labels_on, precisionlocation, remarks, strokeColor, strokeWeight` (+`__geofence` when it's a geofence) |
| Rectangle `u-d-r` | `link (corner points), archive, contact, fillColor, labels_on, precisionlocation, remarks, strokeColor, strokeWeight, tog` |
| Free-form `u-d-f` / telestration `u-d-f-m` | `link (vertices), archive, color, contact, fillColor, labels_on, remarks, strokeColor, strokeWeight` |
| R&B line `u-rb-a` | `range, rangeUnits, bearing, bearingUnits, inclination, northRef, color, contact, labels_on, remarks, strokeColor, strokeWeight` |
| Bullseye `u-r-b-bullseye` | `bullseye, archive, contact, precisionlocation, remarks` |

## 7. Parsing rules worth enforcing
- Key everything on `uid`. A newer event for the same UID replaces the old one.
- Use `stale` to decide when something has expired. A device that stops reporting just stops sending, with no "goodbye" message, so `stale` is the only built-in way to tell it went offline.
- Allow a `;…` suffix on `type`, and don't reject unknown `<detail>` children.
- Treat `9999999`/`999999` in `hae`/`ce`/`le` as unknown.
- `<detail>` is optional. In protobuf, part of it can arrive as typed fields and the rest in `xmlDetail` (17 §5).

## Sources
- MITRE CoT Base-Event Schema v2.0 — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/takcot/mitre (`CoT Base-Event Schema (PUBLIC RELEASE).xsd`)
- TAK detail XSDs — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/takcot/xsd/details
- TAK object XSDs (`Marker - 2525/Spot/Icon Set`, `Drawing Shapes - *`, `Route`, `Range & Bearing - *`) — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/takcot/xsd
- Example CoT — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/blob/main/takcot/examples/CoT%20Types%20Data%20Package.zip
- `<marti>` stripping — TAK Server `CotApi.java` (src/takserver-core/takserver-war/.../sync/api/CotApi.java)
- PyTAK unknown-value constant — https://github.com/snstac/pytak/blob/main/src/pytak/constants.py
