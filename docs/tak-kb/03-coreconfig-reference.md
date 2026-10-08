# 03 — CoreConfig.xml Reference

## Files & workflow
- `/opt/tak/CoreConfig.xml` — **active** running config.
- `/opt/tak/CoreConfig.example.xml` — **baseline/startup** template. If `CoreConfig.xml` is missing, it is regenerated from the example on service start.
- Web-UI changes write into `CoreConfig.xml` only. Copy them into the example file (or copy the whole file over it) to keep a known-good baseline.
- Always edit as the `tak` user (`sudo su tak`) to avoid permission issues; if edited as root, run `sudo chown -R tak:tak /opt/tak`.
- Back up both files outside `/opt/tak` before editing.
- Validate before restarting (must run from `/opt/tak`):
  ```shell
  cd /opt/tak && ./validateConfig.sh
  ```
- Apply: `sudo systemctl restart takserver`. Every CoreConfig change needs a restart.
- Reset to baseline (archived method): delete `CoreConfig.xml` and `CoreConfig.xml.backup`, then restart.
- (A `/tak-coreconfig/` page on the site embeds a CoreConfig.xsd viewer, but it had no schema loaded at extraction time.)

## `<network>`
```xml
<network multicastTTL="5" serverId="2983626fa9c54c0d8078ddd0534e59ca" version="4.8-RELEASE-31-HEAD">
  <input _name="stdssl" protocol="tls" port="8089"/>
  <input auth="anonymous" _name="StdTCPwGroups" protocol="tcp" port="8087" archive="true" anongroup="false" archiveOnly="false" coreVersion="2" coreVersion2TlsVersions="TLSv1.2,TLSv1.3">
    <filtergroup>GroupA</filtergroup>
    <filtergroup>GroupD</filtergroup>
  </input>
  <input auth="x509" _name="StdSSLwGroups" protocol="tls" port="8088" archive="true" anongroup="false" archiveOnly="false" coreVersion="2" coreVersion2TlsVersions="TLSv1.2,TLSv1.3">
    <filtergroup>GroupA</filtergroup>
  </input>
  <connector port="8443" _name="https"/>
  <connector port="8446" clientAuth="false" _name="cert_https"/>
  <announce/>
</network>
```

### `<input>` attributes observed
| Attribute | Values / meaning |
|---|---|
| `_name` | unique input name |
| `protocol` | `tcp`, `udp`, `stcp` (streaming TCP), `tls`, `mcast` |
| `port` | listening port |
| `auth` | `anonymous`, `x509`, `ldap` (commented example `sslauth` on 8090 uses `auth="ldap"`) |
| `group` | multicast group (with `mcast`) |
| `proxy` | `true` for multicast proxy inputs |
| `archive` | `true` = store traffic |
| `archiveOnly` | `false` (the site's example once misspelled it `archieveOnly`) |
| `anongroup` | `false` |
| `coreVersion` | `2` |
| `coreVersion2TlsVersions` | `TLSv1.2,TLSv1.3` |

Child elements: `<filtergroup>name</filtergroup>` (static groups for every client on that input); `<filter><geospatialFilter><boundingBox minLongitude=".." minLatitude=".." maxLongitude=".." maxLatitude=".."/></geospatialFilter></filter>`.

Commented multicast examples in default config:
```xml
<input _name="SAproxy" protocol="mcast" group="239.2.3.1" port="6969" proxy="true" auth="anonymous"/>
<input _name="GeoChatproxy" protocol="mcast" group="224.10.10.1" port="17012" proxy="true" auth="anonymous"/>
<announce enable="true" uid="Marti1" group="239.2.3.1" port="6969" interval="1" ip="192.168.1.137"/>
```

### `<connector>` (web) examples
```xml
<connector port="8443" _name="https"/>
<connector port="8451" _name="https" enableAdminUI="true"  enableWebtak="false"/>
<connector port="8452" _name="https" enableAdminUI="false" enableWebtak="true"/>
<connector port="8453" _name="https" enableAdminUI="false" enableWebtak="false" enableNonAdminUI="false"/>
<connector port="8446" clientAuth="false" _name="cert_https" enableWebtak="false"/>
<connector port="8444" useFederationTruststore="true" _name="fed_https"/>   <!-- legacy federation; remove -->
<connector port="8080" tls="false" _name="http_plaintext"/>                 <!-- plaintext; remove -->
<!-- Custom keystore on a connector (Let's Encrypt on 8446) -->
<connector port="8446" clientAuth="false" _name="LetsEncrypt" keystore="JKS" keystoreFile="certs/files/takserver-le.jks" keystorePass="atakatak"/>
```

## `<security>`
```xml
<security>
  <tls context="TLSv1.2" keymanager="SunX509" keystore="JKS"
       keystoreFile="certs/files/takserver.jks" keystorePass="atakatak"
       truststore="JKS" truststoreFile="certs/files/truststore-TAK-ID-CA-01.jks" truststorePass="atakatak">
    <crl _name="TAKServer CA" crlFile="certs/files/TAK-ID-CA-01.crl"/>
  </tls>
</security>
```
- `keystoreFile` = the server's identity (default `takserver.jks`; becomes `<IP>.jks` if you named the server cert by IP).
- `truststoreFile` = CAs the server trusts for client certs. **Must be changed from `truststore-root.jks` to `truststore-<IntermediateCA>.jks`** after `makeCert.sh ca`.
- To add a CRL, break the self-closing `<tls .../>` and insert `<crl .../>` before `</tls>`.
- Change `keystorePass`/`truststorePass` if you changed the cert password in `cert-metadata.sh`.

## `<auth>`
```xml
<!-- Flat-file (default) with channels + revocation checking -->
<auth x509useGroupCache="true" x509checkRevocation="true">
  <File location="UserAuthenticationFile.xml"/>
</auth>
```
- `x509useGroupCache="true"` — enables **channels**.
- `x509checkRevocation="true"` — enables revoked-cert checking (not added automatically by enrollment setup).
- LDAP/AD variants (`default="ldap"`, `x509groups`, `x509addAnonymous`, `<ldap .../>`) → see 08-ad-ldap-integration.md.

## `<federation>`
```xml
<federation>
  <federation-server port="9000">   <!-- 9001 in the external-CA guide -->
    <tls context="TLSv1.2" keymanager="SunX509" keystore="JKS"
         keystoreFile="certs/files/takserver.jks" keystorePass="atakatak"
         truststore="JKS" truststoreFile="certs/files/fed-truststore.jks" truststorePass="atakatak"/>
  </federation-server>
</federation>
```
When re-signing the server, update `keystoreFile` in **both** `<security>` and `<federation>`; truststore only in `<security>`.

## `<certificateSigning>` (auto-enrollment)
```xml
<certificateSigning CA="TAKServer">
  <certificateConfig>
    <nameEntries>
      <nameEntry name="O"  value="myTeckNet"/>
      <nameEntry name="OU" value="TAK"/>
    </nameEntries>
  </certificateConfig>
  <TAKServerCAConfig keystore="JKS" keystoreFile="certs/files/TAK-ID-CA-01-signing.jks"
      keystorePass="atakatak" validityDays="30" signatureAlg="SHA256WithRSA"
      CAkey="/opt/tak/certs/files/TAK-ID-CA-01" CAcertificate="/opt/tak/certs/files/TAK-ID-CA-01"/>
</certificateSigning>
```
- Default subject is `O=TAK, OU=TAK`.
- `CAkey`/`CAcertificate` need **full paths** (no extension) or the CRL won't update on UI revocations.
- **Bug:** multiple `OU` nameEntries break iTAK / iTAK Tracker.
- Microsoft CA variant:
```xml
<certificateSigning CA="MicrosoftCA">
  <MicrosoftCAConfig username="takcertreq" password="..." truststore="certs/files/keystore.jks" truststorePass="atakatak"
     svcUrl="https://pki.mytecknet.labs/entca_CES_UsernamePassword/service.svc" templateName="TAKClient"/>
</certificateSigning>
```

## Useful sed one-liners from the guides
```shell
sed -i 's/truststore-root/truststore-TAK-ID-CA-01/g' /opt/tak/CoreConfig.example.xml
sed -i 's/takserver/192.168.178.188/g' /opt/tak/CoreConfig.example.xml          # server cert named by IP
sed -i 's/TAK-ID-CA-01/TAK-ID-CA-02/g' CoreConfig.example.xml CoreConfig.xml     # CA rotation
grep -Eo ".+password=\".+/>" /opt/tak/CoreConfig.example.xml                     # show DB connection line/password
```

## Sources
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/lets-build-a-tak-server_archived/
- https://mytecknet.com/managing-users-and-groups/
- https://mytecknet.com/implementing-channels-in-tak/
- https://mytecknet.com/lets-sign-our-tak-server/
- https://mytecknet.com/tak-pki-intermediateca/
- https://mytecknet.com/tak-coreconfig/
