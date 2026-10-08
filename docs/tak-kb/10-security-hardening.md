# 10 — Security & Hardening

Starting-point guidance, not a definitive standard.

## Framework
- **CIA triad**: Confidentiality (only authorized access), Integrity (data unaltered), Availability (accessible when needed).
- Control types: **Administrative** (policy/procedure), **Technical** (firewalls, AV), **Physical** (fences, locks).
- Control functions: prevent, detect, correct, deter, compensate. *Mitigate* = reduce; *remediate* = remove.
- **Defense in depth** layers: physical → network → endpoint → application → users → data.

## Boundary
- Expose only required ports (table in 02). Use a DMZ (single or dual firewall), port forwarding/DNAT, ACLs.
- Prefer a **VPN** for client access; combine with source-restricted firewall zones (e.g. only VPN pool + LAN).
- Put a **reverse proxy** in front of WebTAK for external access.

## Server
- Apply a hardening baseline: **CIS Benchmarks** or **DISA STIGs/SRGs** — test in a lab first; overly strict policies can lock you out.
- Disable `root`; use a sudo-capable admin (check group via `visudo`, e.g. `wheel`):
  ```shell
  sudo useradd -aG wheel <user>   # as published; standard form is: sudo useradd -G wheel <user>  (or usermod -aG for existing users)
  sudo groups <user>
  sudo passwd <user>
  # log in as the new user, test sudo, then:
  sudo passwd -l root
  ```
- Host firewall: allow only required ports, ideally per-source zones (see 02).
- SSH: key-based auth; change port from 22 in `/etc/ssh/sshd_config`; set `PermitRootLogin no`; `sudo systemctl restart sshd`.
- **Change the default cert password `atakatak`** (`cert-metadata.sh`). Note older certs keep the old password — remember when troubleshooting.
- Prefer **auto-enrollment** over shipping client certs in data packages (only the CA password is shared; client keys are generated per device). Optionally use per-cert random passwords (13).
- Move client CSRs/keys off the server; keep only CA files (`truststore-*.jks`, CA keys). Bring files back only for revocation/renewal.
- Don't use a public CA to authenticate clients.
- Anonymous TCP/UDP inputs (8087/8088) and plaintext 8080 should be removed in production.

## Clients
- Same OS hardening; host firewall per the port table.
- Device encryption (BitLocker / Linux FDE / Android & iOS encryption).
- **MDM** for ATAK/iTAK: enforce config baselines, remote wipe, wipe after failed passcodes, locate lost devices, push mission packages to secure folders.
- Consider insider threat — one compromised client compromises the network.
- When testing on public servers, disable GPS/location first.

## Sources
- https://mytecknet.com/tak-security-best-practices/
- https://mytecknet.com/random-client-certificate-passwords/
- https://mytecknet.com/lets-sign-our-tak-server/
- https://mytecknet.com/what-is-tak/
