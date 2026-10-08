# 00 — CoT Listener Quick Reference

Distilled from all myTeckNet TAK articles: the facts that bear directly on building a custom Cursor-on-Target listener. Topic files have the full detail.

## 1. Where CoT flows in a TAK network

- TAK clients on the **same subnet need no server** — they discover/share via **multicast**. The TAK Server acts like a router to connect clients on *different* networks. (Let's Build a TAK Server)
- A TAK Server can **inject external data as CoT** to feed connected clients, and **clients can ingest CoT directly** when no server is in use. (Let's Build a TAK Server — Communications Architecture)
- Clients can connect to **multiple TAK Servers**; servers connect to each other via **federation**.

So a listener can sit in one of three positions:
1. **Multicast/mesh listener** on the LAN (join the SA multicast group).
2. **Server-side input** — your app *is* (or emulates) a server input that clients stream to.
3. **Client of a TAK Server** — connect to 8089 (TLS) like ATAK/WinTAK and receive the CoT stream for your groups.

## 2. Ports & transports (defaults)

| Purpose | Transport | Port | Notes |
|---|---|---|---|
| SA multicast (mesh) | UDP multicast | **6969**, group **239.2.3.1** | bidirectional |
| GeoChat multicast | UDP multicast | **18740**, group **224.10.10.1** | security article table; archived CoreConfig comment shows a `GeoChatproxy` on port **17012** — treat as version-dependent, verify |
| Plain TCP CoT input | TCP | **8087** | `protocol="tcp"`, `auth="anonymous"` — default in example config, insecure |
| Plain UDP CoT input | UDP | **8087** | `protocol="udp"`, anonymous — default in example config |
| Streaming TCP input | TCP (stcp) | **8088** | `protocol="stcp"`, anonymous — default in example config |
| **Client streaming (standard)** | **TLS** | **8089** | `protocol="tls"`, X.509 mutual auth — what ATAK/WinTAK/iTAK use |
| API / Web UI / WebTAK | HTTPS | 8443 | client→server config/API |
| Cert enrollment / WebTAK login | HTTPS | 8446 | `cert_https`, `clientAuth="false"`; not open in firewall by default |
| Federation | TLS | 8444 (legacy), 9000 (v1), 9001 (v2) | server↔server |
| Federation Hub | TLS | 9100 (web UI), 9102 (v2 fed) | |
| Database | TCP | 5432 | core ↔ PostgreSQL in two-server setups |

Client connect string format (from `config.pref`): `HOST:8089:ssl` — i.e. `host:port:protocol`.
iTAK QR format: `description,host,port,protocol` e.g. `TAK Server,my.takserver.us,8089,ssl`.

## 3. Defining a CoT input on TAK Server (`<network>` in CoreConfig.xml)

Default example config ships with (archived guide recommends removing the anonymous ones in production):

```xml
<input _name="stdtcp"    protocol="tcp"  port="8087" auth="anonymous"/>
<input _name="stdupd"    protocol="udp"  port="8087" auth="anonymous"/>
<input _name="streamtcp" protocol="stcp" port="8088" auth="anonymous"/>
<input _name="stdssl"    protocol="tls"  port="8089"/>
```

Full-attribute examples from the site:

```xml
<!-- Anonymous plain TCP input, clients placed into fixed groups -->
<input auth="anonymous" _name="StdTCPwGroups" protocol="tcp" port="8087"
       archive="true" anongroup="false" archiveOnly="false"
       coreVersion="2" coreVersion2TlsVersions="TLSv1.2,TLSv1.3">
  <filtergroup>GroupA</filtergroup>
  <filtergroup>GroupD</filtergroup>
</input>

<!-- TLS input with X.509 auth -->
<input auth="x509" _name="StdSSLwGroups" protocol="tls" port="8088"
       archive="true" anongroup="false" archiveOnly="false"
       coreVersion="2" coreVersion2TlsVersions="TLSv1.2,TLSv1.3">
  <filtergroup>GroupA</filtergroup>
</input>

<!-- Geospatial filter on an input (commented example in default config) -->
<input _name="stdtcpwithfilters" protocol="tcp" port="8087" auth="anonymous">
  <filter>
    <geospatialFilter>
      <boundingBox minLongitude="-80" minLatitude="34" maxLongitude="-70" maxLatitude="36"/>
    </geospatialFilter>
  </filter>
</input>

<!-- Multicast proxies (commented in default config) -->
<input _name="SAproxy" protocol="mcast" group="239.2.3.1" port="6969" proxy="true" auth="anonymous"/>
<input _name="GeoChatproxy" protocol="mcast" group="224.10.10.1" port="17012" proxy="true" auth="anonymous"/>
<announce enable="true" uid="Marti1" group="239.2.3.1" port="6969" interval="1" ip="192.168.1.137"/>
```

Protocol values seen on the site: `tcp`, `udp`, `stcp`, `tls`, `mcast`. Auth values: `anonymous`, `x509`, `ldap`. Inputs can also be added in the web UI: **Configuration → Inputs and Data Feeds → Add Input (Server Port)** (Protocol e.g. "Standard TCP" / "Secure Streaming TCP (TLS)"; Auth "None (Anonymous)" / "X509").

`<network>` element attributes seen: `multicastTTL="5"`, `serverId`, `version`.

## 4. Behaviour your listener must expect

- **Unauthenticated (anonymous TCP) clients can SEND to authenticated clients but cannot RECEIVE from them.** Authenticated clients see the anonymous client; the anonymous client doesn't see them. Switching the input to TLS+X.509 restores two-way flow. (Managing users and groups)
- Groups on an input apply to **all** clients on that port; same group name across inputs = one shared group.
- Input-based grouping does **not** apply to WebTAK.
- Group semantics: **IN** = write-to group, **OUT** = read-from group, **BOTH** = read/write. Default group is `__ANON__`.
- **Channels** (user-toggleable groups) need `<auth x509useGroupCache="true">` and only work for cert-**enrolled** clients, not `makeCert.sh` soft certs.
- Client Dashboard shows subscriptions like `id=tls:19 source=<ip>`.

## 5. TLS / mutual-auth facts for a TLS client-style listener

- Port 8089 does **two-way (mutual) TLS**: server presents its cert; client must present a cert signed by a CA in the server truststore.
- Client needs: **truststore** (server's issuing CA, `truststore-<CA>.p12`, often renamed `caCert.p12`) + **client cert** (`<name>.p12`). Default password `atakatak` (change it!).
- Server cert CN defaults to `takserver`; connecting by IP yields name mismatch unless the cert was issued with the IP/hostname.
- Classic failure: wrong truststore (root instead of intermediate) → server log `Certificate error: peer not verified;` on Local port 8089.
- Server TLS context in config: `TLSv1.2`; inputs may declare `coreVersion2TlsVersions="TLSv1.2,TLSv1.3"`.
- Revoked client certs are rejected at handshake (`RevokedException`) when CRL checking is configured.
- Do **not** use a public CA (e.g. Let's Encrypt) to authenticate clients — anyone could get a cert. Let's Encrypt is only for the 8446 enrollment/login page.

## 6. Healthy-start signals (takserver-messaging.log)

```
INFO c.b.marti.nio.netty.NioNettyBuilder - Successfully Started Netty Server for TlsServerInitializer on Port 8089 with watermark WriteBufferWaterMark(low: 2048, high: 4096)
INFO com.bbn.marti.nio.server.NioServer - Server started
INFO com.bbn.marti.util.VersionBean - TAK Server version 5.0-RELEASE-29-HEAD
```
API side (takserver-api.log): `Tomcat initialized with port(s): 8443 (https) 8446 (https)`

## 7. Server features that produce/consume CoT (Marti UI)

- **Data → CoT Query**: send stored CoT events from server to a device.
- **Configuration → Injectors**: inject CoT, Sensor, SPI.
- **Configuration → Inputs and Data Feeds**: new input ports for pushing CoT to the server.
- **Situational Awareness → Export Mission** (CoT → KMZ/KML), **KML SA Feed** (streaming KML).
- **Administrative → Data Retention**: CoT retention policies.

## 8. Client identity data relevant to CoT

- ATAK prefs: `locationCallsign`, `locationTeam`, `atakRoleType` (see 09).
- Valid team colors: Black, Blue, Brown, Cyan, Dark Blue, Dark Green, Green, Magenta, Maroon, Orange, Purple, Red, Teal, White, Yellow.
- Valid roles: Team Member, Team Lead, HQ, Sniper, Medic, Forward Observer, K9, RTO.

## 9. Gaps — NOT covered on myTeckNet

The site is a TAK **Server administration** resource. It does not document:
- The CoT XML event schema (`<event>`, `<point>`, `<detail>`, `type`/`how`/`uid`/`time`/`start`/`stale`).
- TAK Protocol (protobuf) framing / version negotiation on streaming connections.
- CoT type codes (e.g. `a-f-G-...`).

For those, the site points to: **PyTAK** (Python lib for CoT clients/servers/gateways, incl. serialization & send/receive), **FreeTAKServer**, **taky**, **ampledata.org / github.com/ampledata** (CoT projects), and the open-source TAK Server repo (github.com/TAK-Product-Center/Server). See 14-references-and-resources.md.

**Now covered from primary sources:**
- CoT schema → [15](15-cot-event-schema.md)
- Type codes → [16](16-cot-type-codes.md)
- Protobuf framing and negotiation → [17](17-tak-protocol-framing.md)
- WebSocket `/takproto/1` and the Marti API → [18](18-tak-server-websocket-and-marti-api.md)
- Libraries → [19](19-cot-libraries-pytak-takproto.md)
- Listener decisions → [20](20-listener-design-checklist.md)

## Sources
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/lets-build-a-tak-server_archived/
- https://mytecknet.com/managing-users-and-groups/
- https://mytecknet.com/tak-security-best-practices/
- https://mytecknet.com/implementing-channels-in-tak/
- https://mytecknet.com/creating-tak-data-packages-for-enrollment/
- https://mytecknet.com/tak-qr-codes/
- https://mytecknet.com/tak-certificate-error-peer-not-verified/
- https://mytecknet.com/tak-references/
