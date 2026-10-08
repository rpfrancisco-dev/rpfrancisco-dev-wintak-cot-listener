# 11 — Marti Admin Dashboard

URL: `https://<takserver>:8443/Marti` (admin client cert required; non-admin certs land on WebTAK).

## Metrics Dashboard (default landing page)
- **Server Start Time / Up Time** — Zulu format `yyyy-MM-ddTHH:mm:ss.SSSZ`.
- **CPU Usage** — cores and usage.
- **Heap Usage** — server runs in one or more JVMs.
- **Clients Connected**.
- **Network Input/Output**.
- **Queues**: Submission, Broker, Repository.

## Menu (≡, top right)
**Data**
- CoT Query — send stored CoT events from the server to a device as CoT messages.
- File Manager — (formerly Enterprise Sync) files uploaded as data packages or via DataSync.
- Send Mission Package — upload & send a data package to connected clients.
- Video Feed Manager — publish video feed URLs to clients.
- Mission Manager — manage DataSync missions.
- ExCheck — manage ExCheck templates.

**Situational Awareness**
- Export Mission — export stored CoT as KMZ/KML.
- KML SA Feed — streaming KML (e.g. Google Earth).
- WebTAK — browser TAK client.

**Configuration**
- Inputs and Data Feeds — create input ports for pushing CoT to the server.
- Federation — server-to-server connections.
- Federate Certificate Authorities — public CAs used for federation.
- Injectors — inject CoT, Sensor, and SPI.
- Security and Authentication — view config; set up cert enrollment or AD/LDAP.

**Administrative**
- Database — DB config and maintenance.
- Data Retention — CoT retention policies, archive missions.
- Manage Users — flat-file users/groups (default backend).
- Client Certificates — enrolled certs; revoke (then restart).
- Device Logs — client debug/error log upload.
- Device Profiles — push data packages/configs to groups at enrollment or connection.
- File Config — upload size limit.
- VBM Configuration — VisiBellum MCS for external COP managers.

**Monitoring**
- Alarms.
- Metrics Dashboard.
- Client Dashboard — connected clients, federations, subscriptions, group arrows (← IN, → OUT).

**Plugins** — installed TAK Server plugins.

## Sources
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/managing-users-and-groups/
