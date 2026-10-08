# 07 — Users, Groups & Channels

## Three ways to manage users
1. **Soft certs + flat file**: `makeCert.sh` + `UserManager.jar` → `/opt/tak/UserAuthenticationFile.xml`.
2. **Certificate auto-enrollment** (same flat file, users created in Marti *Manage Users*).
3. **AD/LDAP** backend (see 08). Once LDAP is the backend, UserManager and the Manage Users page no longer manage users/groups. The server accepts **one** auth backend at a time (flat file **or** LDAP).

Default group for everyone: `__ANON__` (double underscores) → everyone shares everything.

## Group roles (one-way traffic model)
| Role | Permission | Marti Client Dashboard arrow |
|---|---|---|
| **IN** | user can **write/send** to the group (not necessarily read) | ← left arrow |
| **OUT** | user can **read/receive** from the group (not necessarily write) | → right arrow |
| **BOTH** | read + write | — |

Example: Shadow in GroupA (both) + IN GroupB → Shadow's events reach Ghost (GroupB), but GroupB's events don't reach Shadow.

## UserManager.jar
```shell
java -jar /opt/tak/utils/UserManager.jar certmod -g  GroupA /opt/tak/certs/files/<cn>.pem   # BOTH
java -jar /opt/tak/utils/UserManager.jar certmod -ig GroupA /opt/tak/certs/files/<cn>.pem   # IN
java -jar /opt/tak/utils/UserManager.jar certmod -og GroupA /opt/tak/certs/files/<cn>.pem   # OUT
java -jar /opt/tak/utils/UserManager.jar certmod -g GroupA -ig GroupB -og GroupC /opt/tak/certs/files/<cn>.pem
java -jar /opt/tak/utils/UserManager.jar certmod -A /opt/tak/certs/files/<cn>.pem           # make admin
```
- No need to reissue a cert to change group membership.
- **Removing** a group = re-run `certmod` listing only the groups to keep.

### UserAuthenticationFile.xml
```xml
<UserAuthenticationFile xmlns="http://bbn.com/marti/xml/bindings">
  <User identifier="Shadow" fingerprint="<fingerprint>" password="<hash>" passwordHashed="true">
    <groupList>GroupA</groupList>
    <groupListOUT>GroupB</groupListOUT>
  </User>
</UserAuthenticationFile>
```
Elements: `groupList` (both), `groupListIN`, `groupListOUT`. Direct edits need a restart; discouraged.

## Manage Users (web)
Marti → **Administrative → Manage Users** (`https://<server>:8443/`). Columns: users | properties | groups. Drag-and-drop groups into IN/OUT/BOTH, *Update* applies immediately. Users created here authenticate with username/password (client still needs the CA `.p12`, ticks *Use Authentication*). Deleting a user does **not** revoke their cert — revoke first.

## Input-based grouping
Create additional server inputs and statically assign groups to every client that connects on that port. Same group name across inputs = one group. Not for WebTAK.

UI: **Configuration → Inputs and Data Feeds → Add Input (Server Port)** — name, protocol (Standard TCP / Secure Streaming TCP (TLS)), auth (None/X509), port, groups → Save (immediate). XML equivalents in 03.

### TCP (anonymous) vs TLS (x509) — tested behaviour
Setup: 8087 Standard TCP/Anonymous; 8088 TLS/X509; 8089 TLS/X509.
- Anonymous TCP clients (Denji on 8087) **send** to authenticated clients but **can't receive** from them.
- Authenticated clients (8088/8089) see each other and see the anonymous client.
- Conclusion: flow depends on the **authentication method**, not the client type. Anonymous TCP is insecure.

## Channels
Channels = groups the client can toggle on/off itself; groups are always-on.
Enable:
```xml
<auth x509useGroupCache="true">
  <File location="UserAuthenticationFile.xml"/>
</auth>
```
then `sudo systemctl restart takserver`.
- Works with flat-file and LDAP backends (LDAP matches on cert CN/subject; with external CAs the CN must match the LDAP username).
- Only for **certificate-enrolled** clients; `makeCert.sh` soft certs get no channels.
- WinTAK: channel selector in the *Manage Server Connections* dock (green dot = active). ATAK 4.7+: icon in the top bar. iTAK supported.
- Since Oct 2024 the old requirement for a `channels.zip` Device Profile is gone. (Archived method: Marti → Administration → Device Profiles → create "channels", type *Apply on Enrollment* (or *on Connection* for existing servers), *Select All* groups, upload `channels.zip`; can push to a client with *Send*.)

## Sources
- https://mytecknet.com/managing-users-and-groups/
- https://mytecknet.com/implementing-channels-in-tak/
- https://mytecknet.com/working-with-channels_archived/
- https://mytecknet.com/lets-build-a-tak-server/
