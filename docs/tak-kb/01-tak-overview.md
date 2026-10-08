# 01 — TAK Overview

## What TAK is
- **TAK** = *Team Awareness Kit* (civilian) / *Tactical Assault Kit* (military/federal). Same core capabilities either way.
- Variants carry suffixes: **-Civ**, **-Gov**, **-Mil**.
- Core: a **geospatial mapping and situational-awareness (SA)** tool, extensible through **plugins** that add or enable capabilities. Used as a flexible command-and-control platform.
- Government open-source software — you can build your own plugins.

## Product family
| Product | Notes |
|---|---|
| **ATAK** | Android. ATAK-CIV on Google Play (`com.atakmap.app.civ`); source at github.com/deptofdefense/AndroidTacticalAssaultKit-CIV |
| **iTAK** | iOS (App Store id1561656396) |
| **WinTAK** | Windows (from tak.gov) |
| **WebTAK** | Browser client served by TAK Server (8443/8446); the only client supporting CAC/token auth at time of writing |
| **TAK Tracker** | Lightweight client: one-way SA reporting to the server + bidirectional chat (Android `gov.tak.taktracker`, iOS) |
| **TAK Server** | Hub that connects clients across networks, stores data (PostgreSQL/PostGIS), federation, web admin ("Marti"). Download from tak.gov; open-source at github.com/TAK-Product-Center/Server |
| **Federation Hub** | Server-to-server federation hub (ports 9100/9102) |

## Who uses it
U.S. military primarily; also law enforcement, recreational users, U.S. Forest Service, DHS, CBP, Colorado Center of Excellence for Advanced Technology Aerial Firefighting, CalFire. The TAK Syndicate maintains a map of registered organizations using TAK.

## Architecture (how CoT moves)
- Same subnet: clients find each other via **multicast**, no server needed.
- Across networks: a **TAK Server** routes between them; clients connect to a local server, which can federate with other servers. Clients may connect to several servers at once.
- The server can **inject external data as Cursor-on-Target (CoT)**; clients can also ingest CoT directly without a server.
- Deployments: **single-server** (core + DB on one host — most common) or **two-server** (core and DB separate).

## Getting it / learning
- tak.gov (account required for server and most downloads, plus documentation).
- CivTAK (civtak.org): community info and public test servers. **Caution:** turn off GPS/location sharing before joining open public servers.

## Alternative server implementations (from TAK References)
- **PyTAK** — Python module for TAK clients, servers & gateways; handles CoT & non-CoT data, CoT serialization, sending/receiving over the network.
- **FreeTAKServer (FTS)** — Python 3 TAK Server, cross-platform, Eclipse Public License.
- **taky** — simple CoT server for TAK clients.

## Background (author's perspective, "TAK then and now")
In DoD use, operating TAK required an **ATO** (Authority to Operate, DoDI 8500 series) and registration of TAK's ports with DISA under **DoDI 8551 (PPSM)** — took ~5 months; ATO obtained mid/late 2021. Ongoing barriers were "not a program of record" objections and slow acquisition.

## Sources
- https://mytecknet.com/what-is-tak/
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/tak-references/
- https://mytecknet.com/blog/why-tak/
