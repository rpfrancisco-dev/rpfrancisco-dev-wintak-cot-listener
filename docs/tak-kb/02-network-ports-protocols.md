# 02 — Network Ports, Protocols & Firewall

## Master port table (defaults)

| Service | Protocol | Port | Source → Destination | Direction |
|---|---|---|---|---|
| TAK Signaling (client streaming) | TCP/S (TLS) | 8089 | Client → Server | IN |
| TAK API / Web UI / WebTAK | TCP/S | 8443 | Client → Server | IN |
| Federation | TCP/S | 8444 (legacy), 9000 (v1), 9001 (v2) | Server → Server | IN |
| Certificate provisioning (enrollment) | TCP/S | 8446 | Client → Server | IN |
| TAK SA (multicast) | UDP | 6969 | 239.2.3.1 ↔ 239.2.3.1 | BOTH |
| GeoChat (multicast) | UDP | 18740 | 224.10.10.1 ↔ 224.10.10.1 | BOTH |
| Federation Hub Web UI | TCP/S | 9100 | Client → Server | IN |
| Federation Hub federation | TCP/S | 9102 (v2) | Server → Server | IN |
| PostgreSQL (two-server) | TCP | 5432 | Core → DB | IN on DB |
| Let's Encrypt HTTP-01 challenge | TCP | 80 | LE → Server | IN (only during issuance/renewal) |

TCP/S = TLS/SSL over TCP. Clients use **ephemeral source ports** to the fixed destination port (not 1:1).

### Non-secure inputs present in the default example config
| Name | Protocol | Port | Auth |
|---|---|---|---|
| stdtcp | tcp | 8087 | anonymous |
| stdudp (`stdupd` in file) | udp | 8087 | anonymous |
| streamtcp | stcp | 8088 | anonymous |
| http_plaintext connector | http | 8080 | none (`tls="false"`) |

The archived build guide removes all of these for a secure baseline. Note the GeoChat proxy example in the archived config uses port **17012** vs **18740** in the security port table — confirm against your TAK version.

### Connection flow for a standard client
- Streaming CoT over **TLS on 8089** using the server's public CA + issued client cert.
- **8443**: secure API for config updates.
- With auto-enrollment: client first talks to **8446** and **8443** to get its cert, then connects on **8089**.
- Non-standard ports need extra config (not covered on the site).

## Firewall commands

### Rocky/RHEL (firewalld)
```shell
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --zone=public --add-port 8089/tcp --add-port 8443/tcp --permanent
sudo firewall-cmd --zone=public --add-port 8446/tcp --permanent   # enrollment
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
```
Restricting to a trusted network with a dedicated zone:
```shell
firewall-cmd --new-zone=takserver-access --permanent
sudo firewall-cmd --zone=takserver-access --add-source=192.168.0.0/24 --permanent
sudo firewall-cmd --zone=takserver-access --add-port 8089/tcp --permanent
sudo firewall-cmd --zone=takserver-access --add-port 8443/tcp --permanent
sudo firewall-cmd --reload
```
DB server (two-server): open 5432/tcp, optionally `--add-source <core-ip>/32`.

### Ubuntu/Raspberry Pi OS (ufw)
```shell
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8089/tcp
sudo ufw allow 8443/tcp
sudo ufw allow 8446/tcp
sudo ufw allow from <core-ip>/32 proto tcp to any port 5432   # DB server
sudo ufw enable
```

## Finding a free port for a new input
```shell
sudo lsof -i -P -n | grep LISTEN
sudo netstat -tulpn | grep LISTEN
sudo ss -tulpn | grep LISTEN
```
Then open it in the host firewall (e.g. `--add-port 8087/tcp`) and any upstream firewall/port-forward.

## Boundary options
- DMZ (single or dual firewall), port forwarding / DNAT, ACLs on network devices.
- VPN (point-to-point tunnel) — can be combined with source-restricted firewall zones.
- Reverse proxy in front of WebTAK for external access.

## Sources
- https://mytecknet.com/tak-security-best-practices/
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/lets-build-a-tak-server_archived/
- https://mytecknet.com/managing-users-and-groups/
- https://mytecknet.com/lets-sign-our-tak-server/
