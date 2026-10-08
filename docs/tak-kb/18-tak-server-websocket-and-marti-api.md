# 18 — TAK Server WebSocket Stream & Marti REST API

Both are served by the TAK Server **API process** on the HTTPS connector (default **8443**) and authenticated by the **client certificate** used in the TLS handshake. Everything below comes from the open-source TAK Server (`TAK-Product-Center/Server`, `main` branch). Check against your server version if something doesn't match.

## 1. WebSocket endpoints

| Path | Handler | Purpose |
|---|---|---|
| **`/takproto/1`** | `TakProtoWebSocketHandler` | Live CoT stream as **TAK protocol v1 protobuf**. This is what WebTAK uses and what a listener can use instead of the 8089 socket. |
| `/payload/1/{clientUid}` | `BinaryPayloadWebSocketHandler` | Messages that carry binary payloads. The last path segment is stored as `clientUid`. |
| `/Marti/api/cop` | STOMP over SockJS | COP/web UI messaging (uses `SocketAuthHandshakeInterceptor`). Not needed for CoT. |

### How `/takproto/1` behaves
- **Access:** `/takproto/**` needs `ROLE_ANONYMOUS`, the base role. In TAK Server's role hierarchy *every* authenticated user has it (`ROLE_ADMIN > ROLE_READONLY > ROLE_ANONYMOUS`, `ROLE_WEBTAK > ROLE_ANONYMOUS`, `ROLE_NON_ADMIN_UI > ROLE_ANONYMOUS`). **A normal (non-admin) client cert is enough.**
- **No XML phase and no negotiation.** Frames are protobuf from the first message.
- **Each binary WebSocket message is one stream frame:** `0xBF <varint len> <TakMessage>` (`StreamingProtoBufProtocol.convertCotToProtoBufBytes(data, true)`; see 17 §2). Strip the `0xBF` and varint before calling `TakMessage.ParseFromString`. Or use `takproto.parse_proto()`, which detects the header itself.
  - Large messages are **not** turned into file-transfer requests on WebSockets (`sendLargeMessages=true`).
- **Text frames are rejected:** any text frame closes the session with **1003 NOT_ACCEPTABLE, "Text messages not supported"**. Send binary only.
- **Groups:**
  - When the socket opens, the server looks up the user's groups for the HTTP session and builds **IN and OUT group bit-vectors**. It then creates a subscription from them (`createWebsocketSubscription`).
  - **You receive only traffic from groups you have OUT/read access to** (07).
  - Membership is re-checked each time the client *sends* a binary frame. A listener that never sends anything keeps the groups it had at connect time, so **reconnect after changing the listener cert's groups**.
- **Per-message filter:** each outbound message also passes `mds().isAllowed(messageType, publisherId, connectionId)` before it's sent.
- If no messaging node will take the subscription, the session is closed straight away. That looks like a connect followed by an instant close.
- **Slow consumers lose data.** Each session is wrapped in a `ConcurrentWebSocketSessionDecorator` with `OverflowStrategy.DROP`:
  - send timeout `websocketSendTimeoutMs`, default **5000 ms**
  - buffer limit `websocketSendBufferSizeLimit`, default **65536 bytes**

  If the client reads too slowly, messages are **dropped silently** rather than queued. Keep the receive loop fast and do heavy work elsewhere.
- **Other limits** (on the `<buffer><queue>` config element in `CoreConfig.xsd`):
  - `websocketMaxBinaryMessageBufferSize` default 65536
  - `websocketMaxSessionIdleTimeout` default −1 (container default)
  - `websocketCompression` default false
- **Allowed origins** come from the first `<connector allowOrigins=…>`, or `*` if `<network allowAllOrigins="true">`. Browsers are affected, native clients aren't.

### Python client sketch
```python
import ssl, websockets, takproto
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.load_cert_chain("client.pem", "client.key", password="…")   # from the .p12
ctx.load_verify_locations("ca-chain.pem")    # intermediate + root (05/12)
ctx.check_hostname = False                    # server cert CN is usually 'takserver' (05)
async with websockets.connect("wss://tak.example:8443/takproto/1", ssl=ctx, max_size=2**22) as ws:
    async for frame in ws:                    # bytes
        msg = takproto.parse_proto(bytearray(frame))   # TakMessage or -1
```
PyTAK uses the same endpoint by default after `tak://` enrollment: `wss://<host>:8443/takproto/1` (`DEFAULT_WS_PATH`, `DEFAULT_WS_PORT`).

## 2. Marti REST API (base `https://<server>:8443/Marti/api`)

Required role per the server's `security-context.xml`. "any user" = `ROLE_ANONYMOUS`, which every authenticated cert has.

| Endpoint | Method | Role | What it returns |
|---|---|---|---|
| `/clientEndPoints` | GET | any user | Known clients (`ClientEndpoint`): `callsign, uid, username, team, role, lastEventTime, lastStatus, groups`. Params: `secAgo` (long, 0=all), `showCurrentlyConnectedClients` (bool), `showMostRecentOnly` (bool), `group` (repeatable). |
| `/contacts/**` | GET | any user | Contact listings |
| `/cot/xml/{uid}` | GET | any user | **Latest stored** CoT for that UID, from the database, as XML. **404 if no row exists in a group you can see.** |
| `/cot/xml/{uid}/all` | GET | any user | All stored events for that UID. Params: `secago` or `start`/`end` (ISO date-time). |
| `/cot/sa` | GET | any user | SA events in a time window. **`start` and `end` are required; the window must be ≤ 24 h.** Optional bbox `left,bottom,right,top`, `isFiltered` (default true). PyTAK's `marti://` reader polls this. |
| `/cot/matchUid?search=` | GET | any user | UID search |
| `/cot/search/**` | GET | **admin** | Saved CoT queries |
| `/subscriptions/all` | GET | any user | Live subscriptions (`dn, callsign, clientUid, lastReportMilliseconds, takClient, takVersion, username, groups, metrics…`). Params: `sortBy` (default CALLSIGN), `direction`, `page`, `limit`. |
| `/subscription/{uid}` | GET | any user | One subscription |
| `/subscriptions/add`, `/subscriptions/delete/{uid}` | POST/DELETE | **admin** | Static subscriptions |
| `/subscriptions/{clientUid}/filter` | GET/POST/DELETE | any user | Per-client subscription filter |
| `/groups/all` | GET | any user | Groups (`useCache`, `sendLatestSA` params) |
| `/groups/{name}/{direction}` | GET | any user | One group (direction IN/OUT) |
| `/groups/user?username=` | GET | **admin** | A user's groups |
| `/groups/groupCacheEnabled` | GET | any user | Whether channels/group cache is on |
| `/users/all`, `/users/{connectionId}` | GET | **admin** (no explicit rule, so `/Marti/**` applies) | Users and their groups (`GroupsApi`) |
| `/version`, `/version/info`, `/version/config`, `/node/id` | GET | any user | Server version / config summary. Handy as a health check. |
| `/repeater/list`, `/repeater/period` | GET | (falls under `/Marti/**` → **admin**) | Repeated (e.g. emergency) messages |
| `/injectors/cot/uid` | POST | any user (DELETE admin) | Inject CoT (PyTAK `marti://` writer) |
| `/inputs/**`, `/config`, `/retention/**`, `/certadmin/**`, `/federat*/**` | * | **admin** | Server administration |

Rules to remember:
- **`/clientEndPoints` is filtered by *your* OUT (read) groups.** It's built from the caller's OUT group bit-vector. If you pass `group=…`, it must be a subset of your groups, or you get **403** ("Illegal attempt to set query groups!", "Missing groups for user!"). So it's only "authoritative" *for the groups your cert can read*. Give the listener read access to every group (07) to see everyone.
- **`/cot/xml/{uid}` reads the CoT archive in the database.** Nothing is stored if the input has `archive="false"` or the data is past the Data Retention policy (11). A 404 means "not archived, or not visible to your groups". It doesn't prove the server never relayed the object. `b-t-f` chat is post-processed, and `<marti>` routing details are removed from the result.
- Anything not listed falls through to `/Marti/** → ROLE_ADMIN`. `DELETE` and `OPTIONS` on `/Marti/**` are blocked by default (`ROLE_NONEXISTENT`) except where explicitly allowed.
- `/Marti/api/tls/*` enrollment endpoints (`makeClientKeyStore`, `signClient`, `signClient/v2`, `config`, `profile/enrollment`) need `ROLE_NO_CLIENT_CERT`. They're for username/password enrollment on 8446 (05, 09).

## 3. Choosing a feed for a listener

| Need | Use | Why |
|---|---|---|
| Real-time positions/objects | `/takproto/1` (WebSocket) or 8089 `tls` | Push-based. The WebSocket has no negotiation and is always protobuf. |
| "Who is connected right now" | `/clientEndPoints?showCurrentlyConnectedClients=true` or `/subscriptions/all` | Server-side state, including clients that are silent on the stream. Limited to the groups you can read. |
| Pre-existing objects after a restart | `/cot/sa?start=…&end=…` (≤ 24 h windows) | Comes from the archive. Needs `archive="true"` on the inputs. |
| Last known state of one UID | `/cot/xml/{uid}` | Comes from the archive, filtered by group. |
| Server liveness / version | `/version`, `/version/info` | Cheap check that works for any user. |

## Sources
- WebSocket registration — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/tak/server/config/WebSocketConfiguration.java
- `/takproto/1` handler — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/com/bbn/marti/nio/websockets/TakProtoWebSocketHandler.java
- WebSocket payload encoding — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/com/bbn/marti/service/WebsocketMessagingBroker.java
- Handshake cert binding — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/java/tak/server/config/websocket/SocketAuthHandshakeInterceptor.java
- URL→role rules and role hierarchy — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/resources/security-context.xml
- `clientEndPoints` — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/takserver-war/src/main/java/com/bbn/marti/network/ContactManagerApi.java ; `ClientEndpoint` fields: src/takserver-common/src/main/java/com/bbn/marti/remote/ClientEndpoint.java
- CoT endpoints — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/takserver-war/src/main/java/com/bbn/marti/sync/api/CotApi.java
- Subscriptions — .../sync/api/SubscriptionApi.java ; Groups — .../groups/GroupsApi.java ; Version — .../util/VersionApi.java ; Repeater — .../repeater/RepeaterApi.java ; CoT search — .../cot/search/api/CotQueryApi.java
- WebSocket buffer config defaults — https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-common/src/main/xsd/CoreConfig.xsd
- PyTAK WebSocket/Marti defaults — https://github.com/snstac/pytak/blob/main/src/pytak/constants.py , https://github.com/snstac/pytak/blob/main/docs/configuration.md
