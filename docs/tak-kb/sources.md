# Sources

All TAK-related pages on mytecknet.com (sitemap + TAK tag pages, 2 pages, checked 2026-10-07).

| Page | Published | Updated | Used in |
|---|---|---|---|
| [What is TAK?](https://mytecknet.com/what-is-tak/) | 2022-12-12 | 2023-09-24 | 01, 10, 14 |
| [[Archived] Let's build a TAK Server – RPM Edition](https://mytecknet.com/lets-build-a-tak-server_archived/) | 2023-01-05 | 2024-10-14 | 00, 02, 03, 04, 05, 09, 12 |
| [Using External CAs to sign your TAK Server](https://mytecknet.com/lets-sign-our-tak-server/) | 2023-01-28 | 2024-10-27 | 03, 06, 10 |
| [Making TAK User Accounts Easy](https://mytecknet.com/making-user-accounts-easy/) | 2023-01-31 | 2023-09-17 | 13 |
| [Managing users and groups in TAK](https://mytecknet.com/managing-users-and-groups/) | 2023-03-09 | 2024-01-19 | 00, 02, 03, 05, 07, 08, 09, 11, 12 |
| [Creating Custom AD Attributes for ATAK](https://mytecknet.com/creating-custom-ad-ldap-attributes-for-atak/) | 2023-03-17 | 2023-09-17 | 08 |
| [TAK then and now (blog)](https://mytecknet.com/blog/why-tak/) | 2023-03-18 | 2023-10-13 | 01 |
| [Creating Data Packages for TAK Configuration/Enrollment](https://mytecknet.com/creating-tak-data-packages-for-enrollment/) | 2023-03-22 | 2024-10-23 | 00, 09, 13 |
| [TAK Security Best Practices](https://mytecknet.com/tak-security-best-practices/) | 2023-03-29 | 2023-12-26 | 00, 02, 10 |
| [[Archived] Implementing Channels](https://mytecknet.com/working-with-channels_archived/) | 2023-08-25 | 2024-10-14 | 07 |
| [TAK Visio Stencils](https://mytecknet.com/tak-visio-stencils/) | 2023-09-14 | 2023-09-16 | 13 |
| [Random Client Certificate Passwords](https://mytecknet.com/random-client-certificate-passwords/) | 2023-09-23 | 2023-09-24 | 10, 13 |
| [Revoking TAK Client Certificates Easy](https://mytecknet.com/revoking-tak-certificates-easy/) | 2023-09-30 | 2023-09-30 | 13 |
| [Certificate error: peer not verified;](https://mytecknet.com/tak-certificate-error-peer-not-verified/) | 2023-10-29 | 2024-02-05 | 00, 05, 12 |
| [TAK References](https://mytecknet.com/tak-references/) | 2023-11-12 | 2024-01-13 | 00, 01, 14 |
| [Let's Build a TAK Server](https://mytecknet.com/lets-build-a-tak-server/) | 2024-01-07 | 2024-10-14 | 00–05, 07, 09, 11, 12 |
| [Implementing Channels in TAK](https://mytecknet.com/implementing-channels-in-tak/) | 2024-10-14 | 2024-10-14 | 00, 03, 07 |
| [Universal TAK Server Installer](https://mytecknet.com/installtak/) | 2024-11-28 | 2025-02-08 | 04 |
| [TAK PKI: Rotating Intermediate CAs](https://mytecknet.com/tak-pki-intermediateca/) | 2025-03-08 | 2025-04-27 | 03, 05 |
| [QR Code Registrations with TAK](https://mytecknet.com/tak-qr-codes/) | 2025-07-06 | 2025-07-14 | 00, 09 |
| [TAK CoreConfig viewer](https://mytecknet.com/tak-coreconfig/) | — | — | 03 (no schema loaded) |
| [Links](https://mytecknet.com/links/) | 2023-05-09 | 2024-10-23 | 14 |

## Primary sources (files 15–20, retrieved 2026-10-07)

| Source | What was used | Used in |
|---|---|---|
| [ATAK-CIV `commoncommo/.../protobuf/protocol.txt`](https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/blob/main/commoncommo/core/impl/protobuf/protocol.txt) | TAK protocol v0/v1, headers, varint, stream and mesh negotiation | 16, 17 |
| [ATAK-CIV `*.proto`](https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/commoncommo/core/impl/protobuf) | TakMessage, TakControl, CotEvent, Detail and sub-messages | 17 |
| [ATAK-CIV `takcot/mitre/*.xsd`](https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/takcot/mitre) | MITRE CoT Base-Event Schema 2.0 (type/how/qos/opex/time/point) | 15, 16 |
| [ATAK-CIV `takcot/xsd/**`](https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/tree/main/takcot/xsd) | TAK detail elements; drawing/route/marker type codes | 15, 16 |
| [ATAK-CIV CoT Types Data Package](https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/blob/main/takcot/examples/CoT%20Types%20Data%20Package.zip) | Real example events (type, how, detail children) | 15, 16 |
| [TAK Server `takserver-protobuf/*.proto`](https://github.com/TAK-Product-Center/Server/tree/main/src/takserver-protobuf/src/main/proto) | Server proto extensions | 17 |
| TAK Server `StreamingProtoBufProtocol`, `StreamingProtoBufOrCoTProtocol`, `StreamingProtoBufHelper`, `TakProtoBufProtocol`, `TransportCotEvent` | Framing, negotiation messages, XML↔proto mapping rules, input protocols, federation framing | 17 |
| TAK Server `CoreConfig.xsd` | `<input>` attributes and defaults, auth enum, `<announce>`, WebSocket buffer settings | 16, 17, 18 |
| TAK Server `WebSocketConfiguration`, `TakProtoWebSocketHandler`, `WebsocketMessagingBroker`, `SocketAuthHandshakeInterceptor` | `/takproto/1` and `/payload/1/*` behaviour | 18 |
| TAK Server `security-context.xml` | URL→role rules, role hierarchy | 18 |
| TAK Server `ContactManagerApi`, `CotApi`, `CotQueryApi`, `SubscriptionApi`, `GroupsApi`, `VersionApi`, `RepeaterApi`, `ClientEndpoint`, `DistributedSubscriptionManager` | Marti REST endpoints and parameters; mission/chat types | 16, 18 |
| [PyTAK](https://github.com/snstac/pytak) (docs/configuration.md, docs/troubleshooting.md, constants.py, functions.py, classes.py, client_functions.py) | URL schemes, TLS vars, defaults, hello/pong, Marti polling | 15, 19 |
| [takproto](https://github.com/snstac/takproto) (functions.py, constants.py, docs/tak_protocols.md) | Parse/encode API, header constants | 17, 19 |
| [taky](https://github.com/tkuester/taky) (cot/client.py, router.py, persistence.py, models/) | Ping/pong, routing, persisted types, type notes | 16, 19 |

TAK Server files are on the `main` branch of `TAK-Product-Center/Server`. Behaviour may differ on older releases.

Skipped (not TAK): Exporting AD public certificates (PowerShell), Facebook Cyber Awareness, Steps Recorder, Minecraft server, RSS/I'm back posts, FAQ (membership only).
