# TAK Knowledge Base — extracted from myTeckNet.com

Knowledge base for the **TAK Cursor-on-Target (CoT) listener** project, built from every TAK-related page on <https://mytecknet.com> (author: "JR"). Organized by topic so Claude Code can load only what a task needs.

Extracted: 2026-10-07. Site content dates range Dec 2022 – Jul 2025 (TAK Server 4.8 → 5.x era). Verify version-sensitive details against the official TAK Server Configuration Guide on tak.gov.

## How to use this in Claude Code

- Drop the `tak-kb/` folder into your repo (e.g. `docs/tak-kb/`).
- Point `CLAUDE.md` at it, e.g.:
  `For TAK/CoT protocol, ports, TLS and server config facts, read docs/tak-kb/00-cot-listener-quick-reference.md first, then the topic file it links.`
- Files are self-contained; each ends with its sources.

## Files

| # | File | What's in it |
|---|------|--------------|
| 00 | [00-cot-listener-quick-reference.md](00-cot-listener-quick-reference.md) | **Start here.** Everything on the site that matters for building a CoT listener: ports, transports, multicast groups, input definitions, auth behaviour, TLS, log signals, and what the site does *not* cover |
| 01 | [01-tak-overview.md](01-tak-overview.md) | What TAK is, client family, architecture, alternative servers (PyTAK, FreeTAKServer, taky) |
| 02 | [02-network-ports-protocols.md](02-network-ports-protocols.md) | Master port/protocol table, firewall commands, checking listening ports |
| 03 | [03-coreconfig-reference.md](03-coreconfig-reference.md) | `CoreConfig.xml` element-by-element: `<network>`, `<input>`, `<connector>`, `<security>`, `<auth>`, `<federation>`, `<certificateSigning>`, `<crl>` |
| 04 | [04-server-installation.md](04-server-installation.md) | Installing TAK Server (single & two-server, RPM/DEB), prerequisites, starting, updating, installTAK script |
| 05 | [05-pki-certificates.md](05-pki-certificates.md) | Built-in PKI: root/intermediate CA, server & client certs, keystores vs truststores, auto-enrollment, revocation & CRL, CA rotation/renewal |
| 06 | [06-external-ca-and-letsencrypt.md](06-external-ca-and-letsencrypt.md) | CSR, enterprise CA signing, PEM/P12/JKS conversion, Let's Encrypt on 8446 |
| 07 | [07-users-groups-channels.md](07-users-groups-channels.md) | IN/OUT/BOTH groups, UserManager.jar, input-based grouping, TCP vs TLS behaviour, channels |
| 08 | [08-ad-ldap-integration.md](08-ad-ldap-integration.md) | AD/LDAP auth config, group prefix, `_READ`/`_WRITE` groups, MS CA enrollment, custom AD attributes for ATAK |
| 09 | [09-client-onboarding.md](09-client-onboarding.md) | WinTAK/ATAK/iTAK/TAK Tracker connection, data packages (`config.pref`, `MANIFEST.xml`), QR code URIs |
| 10 | [10-security-hardening.md](10-security-hardening.md) | Security best practices: boundary, OS, SSH, certs, clients |
| 11 | [11-admin-dashboard.md](11-admin-dashboard.md) | Marti web UI: metrics, every menu item |
| 12 | [12-troubleshooting.md](12-troubleshooting.md) | Log locations, healthy/error log lines, "peer not verified", revoked-cert behaviour, diagnostic commands |
| 13 | [13-admin-scripts.md](13-admin-scripts.md) | myTeckNet helper scripts (user creation, revocation, random cert passwords) — logic summaries |
| 14 | [14-references-and-resources.md](14-references-and-resources.md) | Curated external links: official, community, CoT libraries, training, TAK-as-a-Service |
| 15 | [15-cot-event-schema.md](15-cot-event-schema.md) | CoT XML: `<event>`/`<point>`/`<detail>` attributes, time semantics, `how`/`qos`/`opex`, TAK detail elements, and which detail children each object type uses |
| 16 | [16-cot-type-codes.md](16-cot-type-codes.md) | `type` taxonomy: atoms and affiliations, 2525 mapping, TAK drawings/markers/routes, chat/emergency, ping/pong, delete, negotiation, mission types; a classification recipe |
| 17 | [17-tak-protocol-framing.md](17-tak-protocol-framing.md) | TAK protocol v0/v1: mesh and stream headers, varint, XML→protobuf negotiation, server input `protocol=` values, `.proto` messages, the xmlDetail mapping trap |
| 18 | [18-tak-server-websocket-and-marti-api.md](18-tak-server-websocket-and-marti-api.md) | `/takproto/1` WebSocket behaviour (framing, auth, groups, drop policy) and the Marti REST endpoints with required roles |
| 19 | [19-cot-libraries-pytak-takproto.md](19-cot-libraries-pytak-takproto.md) | PyTAK (URL schemes, TLS vars, defaults), takproto API, taky ping/pong and routing, FTS/OTS |
| 20 | [20-listener-design-checklist.md](20-listener-design-checklist.md) | **Decision checklist** for this listener, with notes on this repo |
| — | [sources.md](sources.md) | Every page used, with publish/update dates |

Files 15–20 were added on 2026-10-07 from **primary sources**: the TAK protocol spec, `.proto` files and CoT XSDs in the ATAK-CIV repo; the TAK Server source (`TAK-Product-Center/Server`, `main`); and the PyTAK, takproto and taky sources. They fill the gaps listed in 00 §9.
