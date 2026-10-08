# 16 — CoT Type Codes

The `type` attribute is a hierarchical "hint": fields separated by `-`, optionally followed by `;extra`. **The meaning of each field depends on the fields before it.** Source: MITRE CoT Base-Event Schema v2.0, plus the TAK-specific codes from the ATAK schemas, the TAK Server source and taky.

## 1. First field (MITRE)

| Code | Group | Meaning |
|---|---|---|
| `a` | Atoms | An actual *thing*: unit, vehicle, person, aircraft, marker. |
| `b` | Bits | Meta-information about data sources and products (imagery, sensor detections, map points, chat, alerts). |
| `r` | Reservation/Restriction/References | Area notices: `r-u` unsafe, `r-o` occupied, `r-c` contaminated (`r-c-c` chemical…), `r-f` flight restrictions. |
| `t` | Tasking | Requests and orders: `t-s` surveillance, `t-r` relocate, `t-e` engage, `t-m` mensurate. TAK also uses `t-x-…` for control traffic (§4). |
| `c` | Capability | Applied to an area: `c-s` surveillance, `c-r` rescue, `c-f` fires (`c-f-d` direct, `c-f-i` indirect), `c-l` logistics (`c-l-f` fuel), `c-c` communications. |
| `u` | (TAK) user drawings / tools | Not defined by MITRE. TAK uses it for drawings and range-and-bearing tools (§3). |

## 2. Atoms: `a-<affiliation>-<battle dimension>-<function…>`

### Affiliation (MITRE)
| Code | Affiliation |
|---|---|
| `p` | Pending |
| `u` | Unknown |
| `a` | Assumed friend |
| `f` | Friend |
| `n` | Neutral |
| `s` | Suspect |
| `h` | Hostile |
| `j` | Joker |
| `k` | Faker |
| `o` | None specified |
| `x` | Other |

### Battle dimension and function
- Both come from **MIL-STD-2525B**: one upper-case battle-dimension letter, then the 2525 *function ID* split into one character per field. The 2525 form `"12 34 56"` becomes `1-2-3-4-5-6`.
- **Upper case means the field is a 2525 code. Lower case means a CoT/local extension.** Examples from the schema:
  - `a-h-X-X-X-X-X-i`: the 2525 type `X-X-X-X-X`, extended with `i` for "Israeli manufacture".
  - `a-h-G-p-i`: a purely CoT-defined type (all lower case after the dimension).
- Common battle dimensions (MIL-STD-2525B; not listed in the CoT XSD itself):

| Code | Dimension |
|---|---|
| `P` | Space |
| `A` | Air |
| `G` | Ground |
| `S` | Sea surface |
| `U` | Sea subsurface |
| `F` | SOF |
| `X` | Other |

### Atoms seen in TAK sources

| Type | Meaning | Source |
|---|---|---|
| `a-f-G-U-C` | Friendly ground unit, combat. **The default self-SA type for ATAK/WinTAK users.** | ATAK marker XSD docs; taky ("User Update") |
| `a-u-G`, `a-n-G` | Unknown / neutral ground marker (hand-placed, `how=h-g-i-g-o`) | ATAK example CoT; taky ("Marker") |
| `a-h-G-U-C-R` | Hostile ground unit (combat, recon) | TAK Server source |
| `a-f-A-M-F-F` | Friendly air, military fixed wing… The **default `svctype` of TAK Server's `<announce>`** beacon | `CoreConfig.xsd` |
| `a-f-G` | Friendly ground (generic) | TAK Server source |

A device is a "live client" when it's an `a-…` atom that **also** carries `<takv>`. Hand-placed atoms (`how=h-…`, no `<takv>`) are map markers, not devices.

## 3. TAK `b-…` and `u-…` objects (plotted on the map)

| Type | Object | Source |
|---|---|---|
| `b-m-p-s-m` | Spot map marker (colour in `usericon`/`color`) | ATAK `Marker - Spot` XSD + example |
| `b-m-p-w-GOTO` | "Go to" waypoint | taky |
| `b-m-p-s-p-i` | Digital pointer (cue point) | taky |
| `b-m-p…` | Generic map point prefix | taky |
| `b-m-r` | Route (points as `<link>` children) | ATAK `Route` XSD |
| `b-r-f-h-c` | CASEVAC / MEDEVAC request | taky |
| `b-f-t-r` | File transfer request (e.g. picture / data package download) | taky |
| `u-d-c-c` | Drawing: circle / ellipse | ATAK `Drawing Shapes - Circle` XSD |
| `u-d-r` | Drawing: rectangle | ATAK `Drawing Shapes - Rectangle` XSD |
| `u-d-f` | Drawing: free-form line / polygon | ATAK `Drawing Shapes - Free Form` XSD |
| `u-d-f-m` | Drawing: telestration (freehand) | ATAK `Drawing Shapes - Telestration` XSD |
| `u-rb-a` | Range & bearing line | ATAK `Range & Bearing - Line` XSD |
| `u-r-b-c-c` | Range & bearing circle | ATAK `Range & Bearing - Circle` XSD |
| `u-r-b-bullseye` | Bullseye | ATAK `Range & Bearing - Bullseye` XSD |

taky persists `a-`, `b-m-p`, `b-r-f-h-c`, `u-d-c`, `u-d-r` and `u-d-f` because they are the long-lived broadcast objects. Everything else is transient.

## 4. Messaging, alerts and control (`b-t-…`, `b-a-…`, `t-x-…`)

| Type | Meaning | Source / behaviour |
|---|---|---|
| `b-t-f` | **GeoChat** message (`<__chat>`, `<remarks>`, `<link>`) | taky; TAK Server. TAK Server sends the sender a delivery-failure notice if a `b-t-f*` recipient is offline (except `b-t-f-s`). |
| `b-t-f-s` | GeoChat variant excluded from offline-delivery failure notices | TAK Server `DistributedSubscriptionManager` |
| `b-a-o-tbl` | **Emergency / 911 alert** | taky |
| `b-a-o-can` | Emergency **cancelled** | taky |
| `t-x-c-t` | **Ping** (client keep-alive). UID is commonly `<client-uid>-ping`. | taky (replies with a pong) |
| `t-x-c-t-r` | **Pong** (reply). taky sends `uid="takPong"`, `how="h-g-i-g-o"`, stale +20 s. *"Clients that do not receive a pong in an appropriate amount of time will disconnect."* | taky `client.py` |
| `t-x-d-d` | **Delete**: remove the object named by `<link uid=…>` | TAK clients. PyTAK also sends a `t-x-d-d` "hello"/"takPong" with no link, so ignore deletes that have no target. |
| `t-x-takp-v` | TAK protocol support **announce** (server → client) | `protocol.txt` (17) |
| `t-x-takp-q` | TAK protocol **request** (client → server) | `protocol.txt` |
| `t-x-takp-r` | TAK protocol **response** (server → client) | `protocol.txt` |
| `t-x-m-n` | Data Sync mission **created** | TAK Server |
| `t-x-m-d` | Mission **deleted** | TAK Server |
| `t-x-m-i` | Mission **invite** | TAK Server |
| `t-x-m-r` | Mission **role change** | TAK Server |
| `t-x-m-c` | Mission **content** change | TAK Server |
| `t-x-m-c-l` | Mission log change | TAK Server |
| `t-x-m-c-k` | Mission keyword change | TAK Server |
| `t-x-m-c-k-u` | Mission UID-keyword change | TAK Server |
| `t-x-m-c-k-c` | Mission resource-keyword change | TAK Server |
| `t-x-m-c-m` | Mission metadata change | TAK Server |
| `t-x-m-c-e` | Mission external-data change | TAK Server |
| `t-x-m-c-h` | Mission layer change | TAK Server |

## 5. Classifying traffic in a listener (recommended)
1. `t-x-takp-*` is protocol negotiation. Handle it at the transport layer and never show it.
2. `t-x-c-t*` is ping/pong. Use it for liveness only and drop it.
3. `t-x-d-d` with a `<link uid>` means delete that UID. Without a link, ignore it.
4. `t-x-m-*` are mission notifications. Optional.
5. `b-t-f*` is chat, and `b-a-o-*` is an alert.
6. `a-*` **with** `<takv>` is a live device. Take position, callsign, group, battery and course/speed from it.
7. Everything else (`a-*` without takv, `b-m-*`, `u-*`, `b-r-*`) is a plotted object. Respect `stale` and delete events.

Affiliation for map styling = the field after `a-` (`f` blue, `h` red, `n` green, `u` yellow by 2525 convention).

## Sources
- MITRE CoT Base-Event Schema v2.0 (`type` taxonomy) — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/takcot/mitre
- ATAK object XSDs with fixed `type` values — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/takcot/xsd
- ATAK example CoT package — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/blob/main/takcot/examples/CoT%20Types%20Data%20Package.zip
- TAK Server mission/chat types — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/com/bbn/marti/service/DistributedSubscriptionManager.java
- TAK Server `<announce svctype>` default — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-common/src/main/xsd/CoreConfig.xsd
- Negotiation types — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/blob/main/commoncommo/core/impl/protobuf/protocol.txt
- taky type notes and ping/pong — https://github.com/tkuester/taky/blob/main/taky/cot/persistence.py , https://github.com/tkuester/taky/blob/main/taky/cot/client.py
- PyTAK hello/pong — https://github.com/snstac/pytak/blob/main/src/pytak/functions.py
- Battle dimensions — MIL-STD-2525B (referenced by the CoT XSD; letters listed here from the standard, verify against 2525B/C if critical)
