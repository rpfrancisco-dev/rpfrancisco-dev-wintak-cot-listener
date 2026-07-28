# TAK Device Monitor

Real-time dashboard of every client connected to a TAK Server (ATAK, WinTAK,
iTAK, TAK ICU, …). A Django backend keeps a streaming connection open to the
TAK Server, decodes CoT (protobuf or XML) presence events — including each
device's position, converted to **MGRS** and **Lat/Lon** — and pushes live
device snapshots to a browser dashboard over a second WebSocket.

Works against both **TAK Server** (TAK Product Center, WebSocket API) and
**FreeTAKServer** (raw CoT stream) — see the connection table below.

```text
TAK Server (wss://host:8443/takproto/1, mutual TLS)
        │  TAK protocol v1 protobuf CoT
        ▼
Django + Channels (daphne)  ──►  in-memory device registry + stale sweeper
        │  JSON snapshots over ws://localhost:8000/ws/devices
        ▼
Browser dashboard (plain HTML/JS)
```

## Layout

```text
backend/            Django project (takbridge) + monitor app
  monitor/tak_client.py   TAK Server WebSocket client (p12 → TLS, reconnects)
  monitor/cot.py          CoT protobuf/XML → device dict
  monitor/registry.py     device store, online/stale/offline sweeper, broadcast
  monitor/consumers.py    /ws/devices consumer for the dashboard
frontend/           index.html, app.js, dashboard.css (served by Django)
requirements.txt
.env.example
```

## 1. Configure the TAK Server connection

Copy `.env.example` to `.env` in the repo root and edit:

| Variable | Meaning | Default |
| --- | --- | --- |
| `TAK_WS_URL` | TAK Server streaming endpoint; the scheme picks the transport (see below) | `wss://10.4.1.42:8443/takproto/1` |
| `TAK_CLIENT_P12` | client certificate (PKCS#12) for mutual TLS | WinTAK's `SslCerts\client_39b0d9ef.p12` |
| `TAK_P12_PASSWORD` | p12 password | `atakatak` |
| `TAK_VERIFY_SSL` / `TAK_CA_FILE` | verify the server cert against a CA bundle; leave `false` for self-signed servers | `false` |
| `TAK_UDP_URL` | optional extra CoT source: a UDP listener run alongside the stream (see below); empty to disable | `udp://10.4.1.42:6969` |
| `TAK_OFFLINE_GRACE_SECONDS` | seconds past CoT stale time before a device flips from *stale* to *offline* | `60` |
| `TAK_STATESAVER_PATH` | WinTAK's plotted-object SQLite store, polled read-only for the full current set (see *Plotted objects*); empty to use the live stream only | `%APPDATA%\WinTAK\Databases\statesaver.sqlite` |
| `TAK_STATESAVER_POLL_SECONDS` | how often to re-read the statesaver store | `10` |
| `TAK_MARTI_URL` | TAK Server base URL for the authoritative client list (see *Authoritative presence*); empty to disable | derived from `TAK_WS_URL` host, e.g. `https://10.4.1.42:8443` |
| `TAK_MARTI_POLL_SECONDS` | how often to poll the Marti client list | `15` |
| `TAK_OBJECT_CHECK_SECONDS` | routine plotted-object check interval (see *Routine object check*); `0` to disable | `30` |
| `TAK_OBJECT_CHECK_MISSES` | consecutive failed checks before an *expired* object is pruned (*missing* objects are removed immediately) | `3` |

`TAK_WS_URL` schemes:

| Scheme | Server | Notes |
| --- | --- | --- |
| `wss://host:8443/takproto/1` | TAK Server (TPC) WebSocket API | TAK protocol v1 protobuf frames; mutual TLS with the p12 |
| `tcp://host:8087` | FreeTAKServer plain CoT port | raw XML `<event>` stream, no certificate needed |
| `tls://host:8089` | FreeTAKServer SSL CoT port | raw XML over TLS; presents the p12 client cert |

Authentication is certificate-based (the p12 enrolled with the TAK Server).
The server's self-signed certificate is accepted by default — the client
simply skips verification rather than hard-failing; supply `TAK_CA_FILE` to
turn verification on.

### UDP listener (`TAK_UDP_URL`)

In addition to the server stream, the backend can listen for CoT over UDP and
merge those devices into the same dashboard. Many TAK clients broadcast their
self-position over UDP (WinTAK's *CoT Outputs* often include
`udp://<your-ip>:6969`), and TAK multicast SA uses UDP too.

Bind semantics for `udp://host:port`:

| host | behaviour |
| --- | --- |
| a multicast group (`224.x`–`239.x`) | joins that group on the default interface |
| a local interface IP | binds that interface on the port |
| anything else (e.g. the remote server IP) | binds **all** interfaces on the port, so datagrams sent to any local IP on that port are still received |

The listener parses both XML and TAK-protobuf datagrams. A device seen on
more than one feed shows every transport it arrived on in the **Protocol**
column (e.g. `SSL, UDP`), and for UDP-only devices the datagram's source
address fills in the IP when the CoT carries no usable endpoint. A **UDP**
pill appears in the header when the listener is enabled. Set `TAK_UDP_URL`
empty to turn it off.

### Authoritative presence (`TAK_MARTI_URL`)

The live CoT stream only reveals a client when its SA is *relayed to our
subscription* — which depends on the client's beacon timing and its group. A
client connected in a different group, or one sitting idle, may not appear.

To fix this the backend also polls the TAK Server's **Marti API**
(`/Marti/api/clientEndPoints`) with the same client certificate. That is the
server's **authoritative** list of every client it knows about and each one's
true **Connected / Disconnected** state. The dashboard reconciles it in:

- a client the server reports **Connected** but that we haven't heard from over
  CoT still shows as online (marked `TAK API` in the Protocol column);
- a client the server reports **Disconnected** is **removed from the
  dashboard** regardless of any stale CoT position — the server's state wins
  (it reappears the moment it reconnects);
- the header shows a **TAK API** pill; hovering a device's status shows the raw
  server status.

This works only against a real **TAK Server** (the Marti API); FreeTAKServer
does not expose it, so leave `TAK_MARTI_URL` empty there.

### Plotted objects (markers & drawings)

Beyond live *devices*, the dashboard surfaces *plotted objects* — markers,
shapes, routes, and drawings placed on the WinTAK map — in a separate,
toggleable **Plotted Objects** panel, and serves them as GeoJSON at
**`/api/objects`** (a `FeatureCollection`).

They come from two sources, combined by `uid`:

- **Live CoT stream / UDP** — objects appear/update/delete in real time as
  they're drawn (a `t-x-d-d` CoT removes one). The stream only carries
  *changes*, so a fresh backend wouldn't see pre-existing objects from the
  stream alone.
- **`statesaver.sqlite` poller** — WinTAK persists every map object as CoT in
  `%APPDATA%\WinTAK\Databases\statesaver.sqlite`; polling it read-only
  (`TAK_STATESAVER_PATH`, every `TAK_STATESAVER_POLL_SECONDS`) seeds the
  **complete current set**, including objects created before startup.

#### Routine object check

The stream and statesaver only ever *add* objects, so a marker deleted while
the backend wasn't looking (e.g. across a restart) would linger forever. Every
`TAK_OBJECT_CHECK_SECONDS` (default 30 s) a routine check re-verifies each
object and stamps a verdict, shown in the **Check** column and summarized next
to the panel title:

| Verdict | Meaning |
| --- | --- |
| **Verified** | still visible in WinTAK's statesaver, or refreshed over the CoT stream within the last two check periods |
| **Unverified** | stream-only object the statesaver never held (e.g. plotted by another client while WinTAK was closed); kept until its CoT stale time passes |
| **Missing** | the statesaver used to vouch for it and no longer does — it was deleted on the map |
| **Expired** | past its own CoT stale time |

A **Missing** object is removed from the dashboard immediately (the
statesaver was read successfully and the map no longer has it; if a stale
read ever removes one wrongly, the statesaver poller re-adds it on its next
tick). An **Expired** object is pruned after `TAK_OBJECT_CHECK_MISSES`
consecutive checks (default 3, so ~90 s). Removals are logged. A failed
statesaver read never counts against an object — absence of evidence is
skipped, not punished.

Note on "still on the TAK Server": TAK Server (5.6, verified against this
deployment) keeps no queryable copy of loose markers — `/Marti/api/cot/xml/
<uid>` is 404, a fresh subscription receives no marker replay, and Data Sync
missions are empty. Markers are relayed once and then live only in each
client's local store, so the statesaver + stream + stale time above *are* the
checkable truths; explicit `t-x-d-d` deletes are additionally applied live.

A CoT `a-*` atom is treated as a *device* only when it carries a `<takv>`
block (a real TAK client) or machine-GPS provenance (`how="m-*"`); hand-placed
`a-*` markers (`how="h-*"`, no takv) and all `u-*`/`b-*`/`g-*` types are
plotted objects. Each object exposes geometry (Point/LineString/Polygon),
2525 symbol path, affiliation, MGRS, and remarks. `GET /api/objects` returns
standard GeoJSON, ready to drop onto a Leaflet/MapLibre map.

### FreeTAKServer notes

- FTS re-broadcasts every CoT event to all connected clients, so simply
  connecting to `tcp://<fts-host>:8087` (default `FTS_COT_PORT`) as a
  passive client yields the full live presence/position feed — no REST
  polling or database access required, and it works across FTS versions.
- Position lives in the CoT `<point lat="…" lon="…" hae="…" ce="…" le="…">`
  element of each `a-*` atom event; identity in `<detail><contact
  callsign=…>` and `<takv platform=… device=…>`. That is exactly what
  [backend/monitor/cot.py](backend/monitor/cot.py) extracts.
- Alternative FTS data surfaces (not used here, but available with admin
  access): the REST/Socket.IO API on port 19023 (`Authorization: Bearer
  <APIToken>`; the Socket.IO `users` event / `userUpdate` subscription feeds
  the stock FTS UI's client list) and the SQLite database
  (`FTS_DB_PATH`, e.g. `/opt/fts/FreeTAKServer.db`). The CoT stream is
  preferred: it is push-based, version-stable, and carries positions.
- MGRS conversion uses the `mgrs` package (in `requirements.txt`);
  lat/lon `0,0` and out-of-range sentinels are treated as "no GPS fix" and
  shown as `—` rather than converted to a bogus grid.

## 2. Install dependencies

```powershell
cd d:\dev\wintak-cot-listener
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:CURL_CA_BUNDLE = ""        # this machine has a broken CA bundle env var
pip install -r requirements.txt
```

## 3. Start the backend and open the dashboard

**One command (recommended)** — from the repo root:

```powershell
.\start.ps1
```

`start.ps1` creates the virtualenv and installs dependencies on first run,
starts the backend, waits for it to come up, and opens the dashboard in your
default browser. It is safe to run repeatedly: if the server is already
running it just reopens the dashboard. `start.bat` is a double-click wrapper
for the same script. Flags: `-NoBrowser` (start only), `-Port <n>`.

**Manual** — if you prefer to run the server yourself:

```powershell
cd backend
daphne -b 127.0.0.1 -p 8000 takbridge.asgi:application
```

Either way the TAK stream and stale sweeper start with the first request, and
the dashboard lives at **<http://localhost:8000>** — the frontend is plain
HTML/JS served by Django, so there is no separate frontend build or dev
server to run.

To launch it automatically at login, put a shortcut to `start.bat` in your
Startup folder (Win+R → `shell:startup`).

### Run in Docker

A `Dockerfile` and `docker-compose.yml` are included. The container runs the
same daphne backend and serves the dashboard on port 8000.

```powershell
docker compose up -d --build      # build + start in the background
docker compose logs -f            # follow logs
docker compose down               # stop
```

Then open **<http://localhost:8000>**.

Because the backend reads two files from the WinTAK host and listens for
WinTAK's UDP CoT, the compose file **bind-mounts** them and **publishes** the
UDP port. Override the host paths/credentials by copying
`.env.docker.example` to `.env.docker` and running
`docker compose --env-file .env.docker up -d --build`. The mounts are:

| Container path | Host default | Purpose |
| --- | --- | --- |
| `/certs` (ro) | `%APPDATA%\WinTAK\SslCerts` | client certificate (`TAK_P12_NAME`) |
| `/wintak` (ro) | `%APPDATA%\WinTAK\Databases` | `statesaver.sqlite` for plotted objects |
| `8000/tcp` | published | dashboard |
| `6969/udp` | published | UDP CoT listener |

**Docker Desktop (Windows/macOS) caveats** — the container runs in a Linux VM,
so `network_mode: host` is unavailable and behaviour differs from native Linux:

- **TAK server stream** (`wss://…:8443`) works — outbound traffic is NATed
  out of the VM normally.
- **UDP listener** receives datagrams published to `6969/udp`, but the source
  address is rewritten to the Docker gateway (so a UDP-only device shows the
  gateway IP), and **multicast** groups can't be joined through the NAT. For
  full-fidelity UDP/multicast, run the backend natively (`.\start.ps1`) or use
  native-Linux Docker with `network_mode: host`.
- **`statesaver.sqlite` over the bind mount** is opened read-only, but WinTAK
  keeps it in WAL mode; across the host→VM mount a read can occasionally be
  stale or briefly locked. Plotted objects still arrive live over the CoT
  stream regardless, so this only affects the pre-existing-objects seed.

For a Linux host on the same network as WinTAK/the TAK server, add
`network_mode: host` to the service (and drop the `ports:` block) for
native UDP/multicast.

## 4. Test against a TAK Server

1. Open <http://localhost:8000>. The **TAK server** pill in the header should
   go green ("connected") within a few seconds; the **bridge** pill shows the
   dashboard's own WebSocket.
2. Start a TAK client (e.g. WinTAK) connected to the same TAK Server. Its
   callsign, UID, device, CoT type, **MGRS**, **Lat/Lon**, protocol, IP, and
   last-ping appear in the table within one position/presence broadcast; the
   summary bar counts it as **Online**. Coordinates update in place as the
   device moves (each position CoT overwrites the row via the live
   snapshot push).
3. Close the TAK client. When its last CoT event passes its stale time the
   row flips to **Stale** (amber), and after `TAK_OFFLINE_GRACE_SECONDS`
   more the device is **removed from the dashboard** (with the Marti API
   enabled the server's Disconnected report removes it as soon as it
   registers). The **Removed (offline)** tile counts removals since the
   backend started; a device reappears the moment it is seen again.
4. Headless smoke test without a browser:

   ```powershell
   python -c "import urllib.request, json; print(json.dumps(json.load(urllib.request.urlopen('http://localhost:8000/api/devices')), indent=2))"
   ```

   (`curl.exe` on this machine has broken TLS config; use python urllib.)

## Notes / scope

- MVP: device list, presence, and counts only — no map, filtering, or C2.
- Offline devices are pruned automatically, mirroring the plotted-object
  check: a device the TAK server no longer vouches for (Marti says
  Disconnected, or its CoT lapsed past the grace with no server record)
  leaves the table instead of lingering as an offline row.
- The registry is in-memory (single daphne process, in-memory channel
  layer). Restarting the backend clears device history; devices repopulate
  from the live stream.
- Devices are identified from atom (`a-*`) CoT events; GeoChat and SPI
  events are ignored. Protocol/IP come from the CoT `contact endpoint`
  field — clients connected through the server's streaming port report
  `SSL`.
