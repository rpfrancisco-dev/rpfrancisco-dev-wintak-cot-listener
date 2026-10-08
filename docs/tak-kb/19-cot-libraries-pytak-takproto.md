# 19 — CoT Libraries: PyTAK, takproto, taky

Reference implementations to borrow from or check behaviour against. All are open source and Python.

## PyTAK (snstac/pytak)
An async (asyncio) framework for TAK clients, servers and gateways. Configured with environment variables or an INI file.

### `COT_URL` schemes
| Scheme | Meaning |
|---|---|
| `tcp://host:port` | TCP unicast, plain |
| `tls://host:port` | TLS unicast (mutual TLS to TAK Server 8089) |
| `udp://group:port` | UDP multicast (Mesh SA) |
| `udp://host:port` | UDP unicast |
| `udp+broadcast://net:port` | UDP broadcast |
| `wss://host:8443/takproto/1` | TAK Server WebSocket (protobuf). Set automatically after `tak://` enrollment. |
| `marti://host:8443` / `marti+http://host:8080` | Marti REST: TX POSTs to `/Marti/api/injectors/cot/uid`, RX polls `/Marti/api/cot/sa` |
| `mqtt[s]://host:port/topic` | MQTT |
| `log://stdout` | Print to stdout (debugging) |
| `tak://…` | Enrollment deep link (09 §QR) |

- **Direction modifiers:** `+wo` (write-only; drain inbound, no port bind) and `+ro` (read-only). They apply to `tcp`, `tls`, `ssl`, `udp` and `mqtt[s]`.
- **Default:** `udp+wo://239.2.3.1:6969` (ATAK mesh SA, write-only).

### Defaults (`constants.py`)
| Constant | Value |
|---|---|
| COT port | 8087 |
| ATAK direct-connect port | **4242** |
| Broadcast | 6969 |
| TAK streaming | 8089 |
| Enrollment | 8446 |
| Marti/WebSocket | 8443, path `/takproto/1` |
| Marti poll | every 5 s, 30 s look-back |
| Default stale | 120 s |
| Unknown hae/ce/le | `9999999.0` |
| XML declaration | `<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>` |
| Default `access` | `UNCLASSIFIED` |
| Reconnect | initial 5 s, ×2, jitter 0.2, max 120 s, reset after 300 s healthy |
| Multicast local address | `0.0.0.0` |
| Queues | max out 100, max in 500 |

`TAK_PROTO=0` (XML, recommended) or `1` (protobuf, needs `pytak[with_takproto]`; PyTAK warns that some iTAK versions don't work with it).

### TLS parameters
| Variable | Purpose |
|---|---|
| `PYTAK_TLS_CLIENT_CERT` | PEM cert (with or without the key) |
| `PYTAK_TLS_CLIENT_KEY` | Separate key file |
| `PYTAK_TLS_CLIENT_PASSWORD` | Password for the key or `.p12` |
| `PYTAK_TLS_CLIENT_CAFILE` | PEM CA chain. Needed for private CAs. TAK's is `/opt/tak/certs/files/ca.pem`, or better the intermediate truststore (05). |
| `PYTAK_TLS_DONT_VERIFY` | Skip certificate verification (dev only) |
| `PYTAK_TLS_DONT_CHECK_HOSTNAME` | Skip the hostname/CN check |
| `PYTAK_TLS_SERVER_EXPECTED_HOSTNAME` | Expected CN when hostname checking is on |
| `PYTAK_TLS_CLIENT_CIPHERS` | Cipher list (default `ALL`; FIPS example `ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384`) |
| `PYTAK_TLS_CERT_ENROLLMENT_USERNAME` / `_PASSWORD` / `_PASSPHRASE` | Enrol for a cert via 8446 |

Example server input from the PyTAK docs: `<input auth="x509" _name="tlsx509" protocol="tls" port="8089" archive="false"/>`.

### Behaviours worth knowing
- **Hello event:** on connect PyTAK sends `t-x-d-d` with uid `takPing` (or `COT_HOST_ID`). `tak_pong()` builds a `t-x-d-d` with uid `takPong`. These are `t-x-d-d` with **no `<link>`**, so a listener must not treat every `t-x-d-d` as a delete.
- **Troubleshooting order** (from its docs):
  1. Use `COT_URL=log://stdout` to confirm CoT is being generated.
  2. Connect straight to a device at `tcp://<device-ip>:4242` (ATAK: *Settings → Network → Streaming*).
  3. Check that the switches pass multicast (many managed switches block it by default).
  4. Run with `DEBUG=1`.
- **Common errors:**
  - `Enter PEM pass phrase:` → set `PYTAK_TLS_CLIENT_PASSWORD` (makeCert.sh keys are encrypted, default `atakatak`).
  - `CERTIFICATE_VERIFY_FAILED … self signed certificate in certificate chain` → supply the CA chain.
  - `hostname … doesn't match` → set the expected hostname, or turn off the hostname check.

## takproto (snstac/takproto)
Encodes and decodes TAK protocol v1 (17).

| Function | Purpose |
|---|---|
| `parse_proto(bytearray)` | Auto-detects mesh (`BF 01 BF`) or stream (`BF varint`). Returns a `TakMessage`, or **`-1`** on failure (not an exception). |
| `parse_mesh(msg)`, `parse_stream(msg)` | Force one format |
| `xml2proto(xml, TAKProtoVer.MESH \| STREAM)` | XML CoT to framed protobuf |
| `xml2message(...)` | XML CoT to a `TakMessage` object |
| `msg2proto(msg, ver)` | `TakMessage` to framed bytes |
| `format_time(...)` | Timestamp helper |

| Constant | Value |
|---|---|
| `TAKProtoVer` | `XML=0, MESH=1, STREAM=2` |
| `DEFAULT_MESH_HEADER` | `b"\xbf\x01\xbf"` |
| `DEFAULT_PROTO_HEADER` | `b"\xbf"` |
| `DEFAULT_XML_HEADER` | `b"<?xml"` |

Its generated `*_pb2.py` modules come from the ATAK protos, so they don't include the TAK Server extras (`submissionTime`, `creationTime`, `caveat`, `releaseableTo`). Those fields are skipped as unknown fields, which is harmless.

## taky (tkuester/taky)
A simple CoT server and router. Its source is handy for the behaviour of real clients:
- **Ping/pong:** when it receives `t-x-c-t` it replies `t-x-c-t-r` (uid `takPong`, `how=h-g-i-g-o`, stale +20 s). *"Clients that do not receive a pong in an appropriate amount of time will disconnect."* Ping UIDs end in `-ping`.
- **Client identity:** the first `a-…` event carrying a TAK user detail (`takv`/`contact`/`__group`) identifies the connection.
- **Routing:**
  - GeoChat (`b-t-f`) goes to the destination UID or callsign, or to a team (`__group`).
  - Events with `<marti><dest callsign=…/>` go only to those callsigns.
  - Everything else is broadcast.
- **Persistence:** keeps `a-`, `b-m-p`, `b-r-f-h-c`, `u-d-c`, `u-d-r`, `u-d-f` so new clients get the current picture. The type list in its `persistence.py` docstring is summarised in 16.

## FreeTAKServer / OpenTAKServer
Python TAK servers (FTS: EPL licence; OTS: aimed at Raspberry Pi-class hosts). According to this project's README (tested against FTS, not taken from the FTS source), FTS re-broadcasts every CoT to all connected clients on its plain CoT port (default 8087). That's why a passive `tcp://` listener works against FTS but not against TAK Server (see 07: anonymous inputs can't receive from authenticated clients).

## Sources
- PyTAK — https://github.com/snstac/pytak (docs/configuration.md, docs/troubleshooting.md, src/pytak/constants.py, functions.py, classes.py, client_functions.py)
- takproto — https://github.com/snstac/takproto (takproto/functions.py, takproto/constants.py, docs/tak_protocols.md)
- taky — https://github.com/tkuester/taky (taky/cot/client.py, router.py, persistence.py, models/)
- OpenTAKServer — https://pypi.org/project/OpenTAKServer
- FreeTAKServer — https://github.com/FreeTAKTeam/FreeTakServer
