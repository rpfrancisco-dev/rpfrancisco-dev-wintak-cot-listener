# 09 — Client Onboarding (WinTAK, ATAK, iTAK, TAK Tracker, Data Packages, QR)

## What a client needs
| Method | Files/credentials |
|---|---|
| Soft cert | `caCert.p12` (server truststore, e.g. `truststore-TAK-ID-CA-01.p12` renamed) + `clientCert.p12` + cert password |
| Auto-enrollment | `caCert.p12` + username/password |
| Quick Connect / Connect with Credentials | credentials only — server must use a publicly trusted cert (e.g. Let's Encrypt on 8446) or a CA already in the device store |

Default: SSL/TLS on **8089**.

## WinTAK
≡ → Settings → Network Preferences → Manage Server Connections → *Add Item* (or click the red cloud/TAK Network Status icon).
Description, Protocol **SSL**, Host (IP/FQDN/hostname), Port **8089** → *Install Certificate Authority* (`caCert.p12`) → *Install Client Certificate* (`clientCert.p12`). For enrollment tick *Enroll for Client Certificate* and *Use Authentication* instead of a client cert. Icon turns green when connected. Supports drag-and-drop data package import.

## ATAK
≡ → Settings → Network Preferences → Network Connection Preferences → Manage Server Connections → ⋮ → Add.
Name, Host, tick *Advanced Options*, Streaming Protocol **SSL**, Port **8089**, untick *Use default SSL/TLS Certificates*, *Import Trust Store*, *Import Client Certificate*.

## iTAK
Settings ⚙ → Network → Servers → ➕ *Add TAK Server*, three options:
- **Connect with Credentials** (like ATAK Quick Connect; needs a cert the iPhone trusts).
- **Upload Server Package** (most common for non-public servers).
- **Scan QR Code**.
iTAK did not support cert auto-enrollment at time of writing.

## TAK Tracker
One-way SA reporting + two-way chat.
- **ATAK-Tracker**: Callsign, Team, Role, Host, Port 8089, *Use SSL*, Cert PW, Cert (client `.p12`), trust (`caCert.p12`).
- **iTAK-Tracker**: *Data Package* → select zip → auto-configured.
Verify in Marti → Monitoring → Client Dashboard.

## Data packages for enrollment
Structure (ATAK/WinTAK):
```
dataPackage/
├── certs/
│   ├── config.pref
│   ├── caCert.p12
│   └── clientCert.p12      (soft-cert only)
├── MANIFEST/
│   └── manifest.xml
├── maps/      (optional, e.g. sGoogleMaps.xml, sBingMaps.xml)
└── plugins/   (optional)
```
Zip the folders and name the zip to match the manifest `name`. Import with *Import File*.

### config.pref — soft cert
```xml
<?xml version='1.0' encoding='ASCII' standalone='yes'?>
<preferences>
  <preference version="1" name="cot_streams">
    <entry key="count" class="class java.lang.Integer">1</entry>
    <entry key="description0" class="class java.lang.String">TAK Server</entry>
    <entry key="enabled0" class="class java.lang.Boolean">true</entry>
    <entry key="connectString0" class="class java.lang.String">TAKSERVER:8089:ssl</entry>
  </preference>
  <preference version="1" name="com.atakmap.app_preferences">
    <entry key="displayServerConnectionWidget" class="class java.lang.Boolean">true</entry>
    <entry key="caLocation" class="class java.lang.String">cert/caCert.p12</entry>
    <entry key="caPassword" class="class java.lang.String">PASSWORD</entry>
    <entry key="clientPassword" class="class java.lang.String">PASSWORD</entry>
    <entry key="certificateLocation" class="class java.lang.String">cert/clientCert.p12</entry>
    <entry key="locationCallsign" class="class java.lang.String">CALLSIGN</entry>
    <entry key="locationTeam" class="class java.lang.String">Green</entry>
    <entry key="atakRoleType" class="class java.lang.String">Team Lead</entry>
  </preference>
</preferences>
```

### config.pref — auto-enrollment (per-connection keys, multi-server safe)
```xml
<preference version="1" name="cot_streams">
  <entry key="count" class="class java.lang.Integer">1</entry>
  <entry key="description0" class="class java.lang.String">TAK Server</entry>
  <entry key="enabled0" class="class java.lang.Boolean">true</entry>
  <entry key="connectString0" class="class java.lang.String">TAKSERVER:8089:ssl</entry>
  <entry key="caLocation0" class="class java.lang.String">cert/caCert.p12</entry>
  <entry key="caPassword0" class="class java.lang.String">PASSWORD</entry>
  <entry key="enrollForCertificateWithTrust0" class="class java.lang.Boolean">true</entry>
  <entry key="useAuth0" class="class java.lang.Boolean">true</entry>
  <entry key="cacheCreds0" class="class java.lang.String">Cache credentials</entry>
</preference>
```
plus `com.atakmap.app_preferences` with `displayServerConnectionWidget`, `locationCallsign`, `locationTeam`, `atakRoleType`. The `cert/` prefix matters: ATAK copies package certs into `atak/cert` and imports them; a wrong path falls back to default credentials. ATAK 5.x warning: global (non-indexed) cert prefs can affect other server connections.

Lock-down prefs: `hidePreferenceItem_locationCallsign`, `hidePreferenceItem_networkGpsCategory` (Boolean true). Full list: AndroidTacticalAssaultKit-CIV `atak/docs/SupportedPreferenceDisable.txt`; an "ATAK Preferences Key 4.8" spreadsheet is linked on the site.

### MANIFEST/manifest.xml
```xml
<MissionPackageManifest version="2">
  <Configuration>
    <Parameter name="uid" value="<your-own-UUID>"/>
    <Parameter name="name" value="TAK_Server.zip"/>
    <Parameter name="onReceiveDelete" value="true"/>
  </Configuration>
  <Contents>
    <Content ignore="false" zipEntry="certs/config.pref"/>
    <Content ignore="false" zipEntry="certs/caCert.p12"/>
    <Content ignore="false" zipEntry="certs/clientCert.p12"/>
  </Contents>
</MissionPackageManifest>
```
- `uid` required since ATAK 4.10.0.x (otherwise a hash is used to detect uniqueness). Generate a fresh UUID — don't reuse the sample `a647112f-...`.
- `onReceiveDelete="true"` deletes the package after import.
- `zipEntry` paths are relative to the zip root.

### iTAK packages
Files at the **zip root** only: `config.pref`, `caCert.p12`, `clientCert.p12` (no folders). Same soft-cert pref content. Pro tip: one universal package = iTAK root layout + `MANIFEST/` + extra files.

## QR code onboarding (ATAK 5.1+ `tak://` URIs)
| URI | Params |
|---|---|
| `tak://com.atakmap.app/enroll?host={takserver}&username={u}&token={pw}` | host (IP/FQDN), username, token/password — plaintext creds; only for controlled, audited emergency use; not with channels |
| `tak://com.atakmap.app/import?url={URL-encoded link}` | downloads a package/map source/imagery, e.g. `url=https%3A%2F%2Fdomain%2Fpath%2Fdatapackage.zip` |
| `tak://com.atakmap.app/preference?key1=..&type1=..&value1=..` | indexed `key[n]`, `type[n]` (string/boolean/long/int), `value[n]` |
Example: `...preference?key1=locationTeam&type1=string&value1=Dark Blue&key2=atakRoleType&type2=string&value2=Team Member&key3=coord_display_pref&type3=string&value3=UTM&key4=alt_display_agl&type4=boolean&value4=true`
iTAK QR (plain text): `serverDescription,serverURL,port,protocol` → `TAK Server,my.takserver.us,8089,ssl` (prompts for credentials).
Requires a public-facing server with ports reachable. Generator suggested: QRCode-Monkey.

## Sources
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/lets-build-a-tak-server_archived/
- https://mytecknet.com/creating-tak-data-packages-for-enrollment/
- https://mytecknet.com/tak-qr-codes/
- https://mytecknet.com/managing-users-and-groups/
