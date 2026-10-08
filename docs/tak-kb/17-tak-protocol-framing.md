# 17 — TAK Protocol: Framing, Negotiation & Protobuf

Primary source: `commoncommo/core/impl/protobuf/protocol.txt` and the `.proto` files in the ATAK-CIV repo, cross-checked against the TAK Server implementation (`StreamingProtoBufProtocol`, `StreamingProtoBufOrCoTProtocol`, `StreamingProtoBufHelper`, `TransportCotEvent`).

## 1. Versions at a glance

| Version | Encoding | Mesh (UDP / one-shot TCP) | Streaming (server TCP/TLS) |
|---|---|---|---|
| **0** "Traditional" | CoT XML | One XML `<event>` per datagram | `<?xml …?>` + newline + `<event>…</event>`, repeated with **no gap**. Split on `</event>`. |
| **1** TAK Protocol | protobuf `TakMessage` | `0xBF 0x01 0xBF` + payload | `0xBF <varint length>` + payload |

Ground rules:
- A client that sends version V can also decode V.
- **Every client must decode version 0 (XML).**
- The payload is the same in mesh and streaming. Only the header differs.

## 2. Headers

**Mesh header:** `<0xBF> <version varint> <0xBF>`. For v1 that's the 3 bytes `BF 01 BF` (decimal `191 1 191`).

**Streaming header:** `<0xBF> <payload length varint>`. There's no version byte, because the version was agreed for the whole connection.

**Varint:** an unsigned protobuf varint. Take 7 bits at a time, least significant first, and set the high bit on every byte except the last. At most 10 bytes (64-bit). TAK Server writes it with `CodedOutputStream.writeUInt32NoTag`.

```
stream frame:  BF | varint(len(payload)) | TakMessage bytes
mesh  frame:   BF | 01 | BF | TakMessage bytes
```

### Minimal Python decoder (stream)
```python
def read_varint(buf, i):
    shift = val = 0
    while True:
        b = buf[i]; i += 1
        val |= (b & 0x7F) << shift
        if not b & 0x80:
            return val, i
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")

def split_stream(buf: bytes):
    """Yield complete TakMessage payloads; return leftover bytes."""
    out, i = [], 0
    while i < len(buf):
        if buf[i] != 0xBF:
            raise ValueError("lost sync: no magic byte")
        try:
            n, j = read_varint(buf, i + 1)
        except IndexError:
            break                      # header incomplete, wait for more data
        if j + n > len(buf):
            break                      # payload incomplete
        out.append(buf[j:j + n]); i = j + n
    return out, buf[i:]
```
TAK Server logs `Failed to find magic byte, instead found …` and drops the connection when the magic byte is missing.

## 3. Streaming negotiation (XML → protobuf)

On a TAK Server `protocol="tls"` input, the connection **starts in XML** and can upgrade to v1:

1. Connect. If the server requires an auth message, it must be the client's first message. The server may send CoT XML at any time.
2. Both sides speak XML.
3. The server **announces** support, at most once per connection:
```xml
<event version='2.0' uid='{protouid}' type='t-x-takp-v' time='…' start='…' stale='…' how='m-g'>
  <point lat='0.0' lon='0.0' hae='0.0' ce='999999' le='999999'/>
  <detail><TakControl>
    <TakProtocolSupport version='1'/>
    <TakServerVersionInfo serverVersion='5.x-RELEASE-…' apiVersion='…'/>   <!-- TAK Server adds this -->
  </TakControl></detail>
</event>
```
   TAK Server sends this with a fresh UUID and a stale time of **now + 60 s**.
4. Both sides keep speaking XML.
5. The client **requests** an upgrade, reusing the server's `protouid`. It must only send this after seeing step 3:
```xml
<event version='2.0' uid='{protouid}' type='t-x-takp-q' … how='m-g'>
  <point lat='0.0' lon='0.0' hae='0.0' ce='999999' le='999999'/>
  <detail><TakControl><TakRequest version='1'/></TakControl></detail>
</event>
```
6. From then on the client **sends nothing more in XML**, but it must still read incoming XML. It waits at least 1 minute for the response:
```xml
<event … type='t-x-takp-r' …><detail><TakControl><TakResponse status='true'/></TakControl></detail></event>
```
7. `status='true'`: from the next byte on, **both directions** use streaming v1 frames (§2). `status='false'`: stay on XML (the client may retry).
   - If no response arrives before the timeout, the client disconnects and starts again.

The server only accepts a request for about 1 minute after its announce (`TIMEOUT_MILLIS = 60000`). A client that never sends `t-x-takp-q` simply stays on XML for the whole session. That's valid.

**Mesh negotiation (UDP):** each v1-capable device broadcasts a `TakControl` (min/max version it can *decode*) at least every 60 s. Senders use the **highest version every known contact supports**, falling back to XML. A contact that hasn't sent `TakControl` for 2 minutes reverts to the version of its last message. So a mesh listener must accept **both** XML and `BF 01 BF` datagrams on the same port.

## 4. TAK Server input `protocol` values

From the `TransportCotEvent` enum (enum name → CoreConfig `protocol=` value). The UDP and multicast rows are explicit in the enum's protocol wiring. The TCP/TLS rows are **inferred from the enum names**, because their codecs are wired elsewhere in the Netty server.

| `protocol=` | Enum | Encoding on the wire |
|---|---|---|
| `udp` | `UDP` | one message per datagram, **protobuf or XML** (`SingleProtobufOrCotProtocol`) |
| `cotmcast` | `MUDP` | multicast, **XML only** (`SingleCotProtocol`) |
| `mcast` | `COTPROTOMUDP` | multicast, **protobuf or XML** (`SingleProtobufOrCotProtocol`). This is the SA proxy form. |
| `tcp` | `TCP` | plain TCP CoT (XML) |
| `stcp` | `STCP` | streaming TCP CoT (XML) |
| `ssl` | `SSL` | TLS CoT (legacy name) |
| `cottls` | `TLS` | TLS, CoT XML only |
| `prototls` | `PROTOTLS` | TLS, protobuf only |
| `tls` | `COTPROTOTLS` | TLS, **XML then negotiated to protobuf** (§3, `StreamingProtoBufOrCoTProtocol`). This is the standard 8089 input. |

Other `<input>` attributes from `CoreConfig.xsd`:
- `auth`: `ldap|file|anonymous|x509`, default `x509`
- `archive`: default `true`
- `archiveOnly`
- `federated`, `federateOnly`
- `anongroup`
- `iface`, `group` (for multicast)
- `coreVersion`: default `2`
- `coreVersion2TlsVersions`: default `TLSv1.2,TLSv1.3`
- `maxMessageReadSizeBytes`: default **2048**
- `syncCacheRetentionSeconds`: default 3600
- `binaryPayloadWebsocketOnly`
- `quicConnectionTimeoutSeconds`
- child `<filtergroup>`, child `<filter>`

## 5. Protobuf messages (proto3, package `atakmap.commoncommo.protobuf.v1`)

```proto
message TakMessage {
  TakControl takControl = 1;     // optional; omitted = keep last control info
  CotEvent   cotEvent   = 2;     // optional
  uint64 submissionTime = 3;     // TAK Server only (ms)
  uint64 creationTime   = 4;     // TAK Server only (ms)
}
message TakControl {
  uint32 minProtoVersion = 1;    // 0 => treat as 1
  uint32 maxProtoVersion = 2;    // 0 => treat as 1
  string contactUid      = 3;    // ATAK proto only; omit when paired with a CotEvent
}
message CotEvent {
  string type = 1;  string access = 2;  string qos = 3;  string opex = 4;
  string uid  = 5;
  uint64 sendTime = 6;  uint64 startTime = 7;  uint64 staleTime = 8;   // ms since epoch
  string how  = 9;
  double lat = 10; double lon = 11; double hae = 12; double ce = 13; double le = 14;
  Detail detail = 15;
  string caveat = 16;  string releaseableTo = 17;    // TAK Server proto only
}
message Detail {
  string xmlDetail = 1;                       // leftover <detail> children as XML
  Contact contact = 2;                        // <contact callsign endpoint>
  Group group = 3;                            // <__group name role>
  PrecisionLocation precisionLocation = 4;    // <precisionlocation geopointsrc altsrc>
  Status status = 5;                          // <status battery>
  Takv takv = 6;                              // <takv device platform os version>
  Track track = 7;                            // <track speed course>
}
message Contact { string endpoint = 1; string callsign = 2; }
message Group { string name = 1; string role = 2; }
message PrecisionLocation { string geopointsrc = 1; string altsrc = 2; }
message Status { uint32 battery = 1; }
message Takv { string device = 1; string platform = 2; string os = 3; string version = 4; }
message Track { double speed = 1; double course = 2; }
```
The ATAK and TAK Server protos are wire-compatible. The server only adds fields (3, 4 on `TakMessage`; 16, 17 on `CotEvent`). A client built from the ATAK protos just ignores them.

### XML ↔ typed-field mapping: the trap
TAK Server only moves a `<detail>` child into its typed field when **the element has exactly the expected attributes**:

| Element | Becomes typed field only if… |
|---|---|
| `<contact>` | it has `callsign`, plus at most `endpoint`, and nothing else |
| `<__group>` | it has exactly `name` + `role` |
| `<precisionlocation>` | it has exactly `geopointsrc` + `altsrc` |
| `<status>` | it has exactly `battery` |
| `<takv>` | it has **all four**: `device`, `platform`, `os`, `version`, and nothing else |
| `<track>` | it has exactly `speed` + `course` |

Anything else, **including a `<takv>` with a missing `os` or a `<contact>` with an extra `phone`**, stays as raw XML in `xmlDetail`. A listener must therefore:
1. Read the typed fields, **and**
2. Wrap `xmlDetail` as `<detail>…</detail>`, parse it, and fall back to its `<takv>`, `<contact>`, `<__group>` and so on.

If an element shows up in both places (a broken sender), the spec says **keep the `xmlDetail` copy and ignore the typed one**. Receivers rebuild the document as `<?xml version="1.0" encoding="UTF-8"?><detail>` + xmlDetail + `</detail>`, then merge in the typed fields.

Other conversion rules from the protos:
- Times are ms since epoch.
- 999999 means unknown for hae/ce/le.
- A missing "required" field makes the sender fall back to the raw XML form.

## 6. Federation (server ↔ server) is different
`TakProtoBufProtocol` (federation v2) frames `FederatedEvent` messages with a **4-byte big-endian length prefix**, not `0xBF`/varint. Don't point a client-style decoder at a federation port.

## 7. Libraries
- **takproto** (Python, snstac): `parse_proto(bytearray)` auto-detects mesh/stream; `parse_mesh()`, `parse_stream()`, `xml2proto(xml, TAKProtoVer.MESH|STREAM)`, `msg2proto()`. Constants: `DEFAULT_MESH_HEADER = b"\xbf\x01\xbf"`, `DEFAULT_PROTO_HEADER = b"\xbf"`, `TAKProtoVer {XML=0, MESH=1, STREAM=2}`.
- **PyTAK**: `TAK_PROTO=0` (XML, the default and recommended setting) or `1` (protobuf, needs `pytak[with_takproto]`). PyTAK warns that v1 doesn't work with every client (notably some iTAK versions).

## Sources
- TAK protocol spec — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/blob/main/commoncommo/core/impl/protobuf/protocol.txt
- ATAK protos — https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/commoncommo/core/impl/protobuf
- TAK Server protos — https://github.com/TAK-Product-Center/Server/tree/main/src/takserver-protobuf/src/main/proto
- Stream framing — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/com/bbn/marti/nio/protocol/connections/StreamingProtoBufProtocol.java
- Negotiation implementation — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/com/bbn/marti/nio/protocol/connections/StreamingProtoBufOrCoTProtocol.java
- XML→proto mapping rules — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-plugins/src/main/java/tak/server/proto/StreamingProtoBufHelper.java
- Input protocols — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/com/bbn/marti/service/TransportCotEvent.java ; `CoreConfig.xsd` (`input` complexType)
- Federation framing — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/com/bbn/marti/nio/protocol/connections/TakProtoBufProtocol.java
- takproto — https://github.com/snstac/takproto (docs/tak_protocols.md, takproto/functions.py, takproto/constants.py)
- PyTAK `TAK_PROTO` — https://github.com/snstac/pytak/blob/main/docs/configuration.md
