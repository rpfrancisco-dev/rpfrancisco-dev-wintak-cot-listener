# 12 — Troubleshooting

## Logs
- `/opt/tak/logs/takserver-messaging.log` — streaming/CoT side (may take a while to appear after first start).
- `/opt/tak/logs/takserver-api.log` — web/API side.
```shell
tail -f /opt/tak/logs/takserver-messaging.log
```

## Healthy startup lines
```
INFO c.b.marti.nio.netty.NioNettyBuilder - Successfully Started Netty Server for TlsServerInitializer on Port 8089 with watermark WriteBufferWaterMark(low: 2048, high: 4096)
INFO com.bbn.marti.nio.server.NioServer - Server started
INFO com.bbn.marti.util.VersionBean - TAK Server version 5.0-RELEASE-29-HEAD
[main] INFO o.s.b.w.e.tomcat.TomcatWebServer - Tomcat initialized with port(s): 8443 (https) 8446 (https)
```

## "Certificate error: peer not verified;"
```
ERROR c.b.m.n.n.h.NioNettyHandlerBase - NioNettyServerHandler error. Cause: javax.net.ssl.SSLHandshakeException: General OpenSslEngine problem. Additional info: Remote address: 192.168.100.10; Remote port: 56640; Local port: 8089; Certificate error: peer not verified;
```
Cause: the client was given the wrong public CA (usually `truststore-root.p12`) while the server cert is signed by the intermediate. Client can't verify the server and sends FIN.
Fix: give the client `truststore-<IntermediateCA>.p12`; confirm CoreConfig `truststoreFile` points at `truststore-<IntermediateCA>.jks`.
```shell
keytool -v -list -keystore /opt/tak/certs/files/takserver.jks    # Owner vs Issuer
openssl pkcs12 -info -in /opt/tak/certs/files/truststore-root.p12
```

## Revoked certificate attempts
Client cycles connect/disconnect; log shows:
```
ERROR c.b.m.nio.codec.impls.X509AuthCodec - X509 auth exception info: CN: myTeckNet. Message: Attempt to use revoked certificate : OU=TAK,O=TAK,CN=myTeckNet
com.bbn.marti.remote.exception.RevokedException: Attempt to use revoked certificate ...
INFO c.b.m.s.DistributedSubscriptionManager - Added Subscription: id=tls:19 source=192.168.178.177
INFO c.b.m.s.DistributedSubscriptionManager - Removed Subscription: tls:19
```
(The `tls:N` id increments on each attempt.)

## Common problems & fixes
| Symptom | Fix |
|---|---|
| Browser `NET::ERR_CERT_AUTHORITY_INVALID` / name mismatch | Import CA certs into OS/browser trust; issue server cert with IP/FQDN or add hosts entry for `takserver` |
| Admin lands on WebTAK, not Metrics | `UserManager.jar certmod -A <cert>.pem` |
| Server won't start after edit | `./validateConfig.sh` in `/opt/tak`; restore `CoreConfig.example.xml` baseline |
| Permission errors | Edit as `tak` user; `sudo chown -R tak:tak /opt/tak` |
| `keytool error: ... keystore password was incorrect` on RHEL/Fedora | Java FIPS: set `security.useSystemPropertiesFile=false` in `java.security` |
| Enrollment fails | Open 8446/tcp; check signing keystore path/password |
| Revocation not enforced | Add `<crl>` in `<tls>`, `x509checkRevocation="true"`, `CAkey`/`CAcertificate` paths; restart |
| AD groups not populated | Configure LDAP in CoreConfig instead of the UI; `default="ldap"`; `groupBaseRDN` = OU path only |
| iTAK enrollment problems | Avoid multiple OU nameEntries; iTAK lacked enrollment support at time of writing |
| All clients drop on one day | Intermediate CA + server cert expired (2-year default) → rotate CA (05) |
| macOS `zsh: no matches found` with scp wildcard | Escape: `takserver-5.\*.rpm` |
| Apt key errors on minimal installs | `sudo apt install gnupg -y` |
| New input port unreachable | Check `ss -tulpn`, open host + upstream firewall |

## Sources
- https://mytecknet.com/tak-certificate-error-peer-not-verified/
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/lets-build-a-tak-server_archived/
- https://mytecknet.com/managing-users-and-groups/
- https://mytecknet.com/lets-sign-our-tak-server/
