# 05 — TAK Server Built-in PKI & Certificates

Applies when the TAK Server is its own CA (the default). External/public CAs → 06.

## Concepts
- **Two-tier hierarchy**: self-signed **root CA** → **intermediate (issuing/signing) CA** → server & client certs.
- **Keystore** = identity presented (server: `takserver.jks`; client: `<name>.p12`).
- **Truststore** = library of CAs trusted. Server truststore (`truststore-<CA>.jks`) decides which client certs are accepted; client truststore (`truststore-<CA>.p12`, commonly renamed `caCert.p12`) decides whether the client trusts the server.
- Server is "a client of itself" and must trust its own signer.
- Mutual TLS handshake: hello exchange → server presents cert → client validates chain, validity and revocation → client presents cert → server validates → shared symmetric session key.

### Default validity
| Cert | Validity |
|---|---|
| Root CA | 10 years (3652 days) |
| Intermediate CA | 2 years (730 days) |
| Server / client certs | 2 years (730 days) |

The intermediate CA and server cert issued the same day **expire together**, taking the server down — track these dates.

## Setup sequence (order matters)
```shell
sudo su tak
cd /opt/tak/certs
vi cert-metadata.sh
```
`cert-metadata.sh` key fields:
```bash
COUNTRY=US                      # never blank ("XX" allowed)
STATE=${STATE}
CITY=${CITY}
ORGANIZATION=${ORGANIZATION:-TAK}
ORGANIZATIONAL_UNIT=${ORGANIZATIONAL_UNIT}
CAPASS=${CAPASS:-atakatak}      # CA password
PASS=${PASS:-$CAPASS}           # all other certs
DIR=files
```
Quote values with spaces (`STATE="New York"`). Change the default password.

```shell
./makeRootCa.sh --ca-name TAK-ROOT-CA-01      # 1. root CA (no spaces in names)
./makeCert.sh ca TAK-ID-CA-01                 # 2. intermediate; answer y to "move the files around"
./makeCert.sh server takserver                # 3. server cert (CN 'takserver' is the CoreConfig default)
sed -i 's/truststore-root/truststore-TAK-ID-CA-01/g' /opt/tak/CoreConfig.example.xml   # 4. trust the intermediate
cat /opt/tak/CoreConfig.example.xml | grep truststore-
```
Optional: name the server cert by IP (`./makeCert.sh server 192.168.178.188`) then `sed -i 's/takserver/<IP>/g' /opt/tak/CoreConfig.example.xml`. Or keep `takserver` and add a hosts-file entry on clients to avoid name-mismatch errors.

## Admin certificate
```shell
sudo su tak && cd /opt/tak/certs
./makeCert.sh client webadmin
java -jar /opt/tak/utils/UserManager.jar certmod -A /opt/tak/certs/files/webadmin.pem
exit
sudo cp -v /opt/tak/certs/files/webadmin.p12 ~ && sudo chown -R <user>:<group> /home/<user>
scp <user>@<takserver>:~/webadmin.p12 .
```
Import `webadmin.p12` into the browser (Firefox has its own store; Windows/Edge/Chrome use the OS store — also move the CA certs into *Trusted Root Certification Authorities*; macOS Keychain → set root to *Always Trust*). Browse `https://<server>:8443/Marti`. Landing on WebTAK instead of Metrics = the `-A` admin flag wasn't applied.

## Soft (manual) client certificates
```shell
sudo su tak && cd /opt/tak/certs
./makeCert.sh client wintak
java -jar /opt/tak/utils/UserManager.jar certmod -g __ANON__ /opt/tak/certs/files/wintak.pem
exit
sudo cp -v /opt/tak/certs/files/wintak.p12 .
sudo cp -v /opt/tak/certs/files/truststore-TAK-ID-CA-01.p12 .
```
Without the `UserManager certmod` step the client still lands in `__ANON__` but won't appear in the Marti UI. Give each device a unique cert; no spaces in CNs.

## Certificate auto-enrollment (TAK Server CA)
1. Find signing keystore: `ls -l /opt/tak/certs/files/*-signing.jks`
2. Marti → **Configuration → Security and Authentication → Edit Security** → *Enable Certificate Enrollment* → *TAK Server CA*:
   - Signing Keystore File: `certs/files/<CA>-signing.jks` (path relative to `/opt/tak`)
   - Signing Keystore Password: `atakatak` (or yours)
   - Validity Days: after expiry the user re-enters credentials to get a new cert.
3. In `CoreConfig.xml` add `CAkey`/`CAcertificate` (full paths) to `TAKServerCAConfig` and `x509checkRevocation="true"` to `<auth>` (see 03).
4. `./validateConfig.sh`, restart, open **8446/tcp**.
5. Create users in **Administrative → Manage Users**. Users get `caCert.p12` + username/password, and tick *Enroll for Client Certificate* + *Use Authentication*.
6. Issued certs are listed under **Administrative → Client Certificates** (filter Active/Expired/Revoked/Replaced).

## Revocation & CRL
Manual (soft certs):
```shell
openssl x509 -text -in /opt/tak/certs/files/<cn>.pem | grep -Eo "Issuer:.+"     # who signed it
sudo su tak && cd /opt/tak/certs
./revokeCert.sh /opt/tak/certs/files/<cn> /opt/tak/certs/files/ca-do-not-share /opt/tak/certs/files/ca
openssl crl -in /opt/tak/certs/files/ca.crl -inform PEM -text -noout             # view CRL
openssl crl -in /opt/tak/certs/files/ca.crl -inform PEM -text -noout | grep <serial>
```
Publish the CRL inside `<tls>`: `<crl _name="TAKServer CA" crlFile="certs/files/<CA>.crl"/>`, validate, restart.
UI revocation (enrolled certs): *Client Certificates* → *Revoke Selected* → restart the service to refresh the CRL.
Offboarding: revoke the cert **then** delete the user. Deleting a user alone doesn't kill an active cert.

Archived alternative syntax: `./revokeCert.sh files/<cn> files/TAK-CA-01 files/TAK-CA-01`. Renew a client = revoke, then `makeCert.sh client <same cn>` and answer `Y` to overwrite.

## Rotating the intermediate CA (root still valid)
```shell
sudo su tak && cd /opt/tak/certs
cp files/root-ca.pem files/ca.pem
cp files/root-ca-do-not-share.key files/ca-do-not-share.key
cp files/root-ca-trusted.pem files/ca-trusted.pem
echo y | ./makeCert.sh ca TAK-ID-CA-02
echo y | ./makeCert.sh server takserver
keytool -v -list -keystore /opt/tak/certs/files/takserver.jks    # check new dates
cd /opt/tak
sed -i 's/TAK-ID-CA-01/TAK-ID-CA-02/g' CoreConfig.example.xml
sed -i 's/TAK-ID-CA-01/TAK-ID-CA-02/g' CoreConfig.xml
exit
sudo cp -v /opt/tak/certs/files/truststore-TAK-ID-CA-02.p12 ./caCert.p12 && sudo chown takadmin:takadmin caCert.p12
sudo systemctl restart takserver     # cutover happens here — distribute files first
```
If the **old** CA is still valid (overlap period), also:
```shell
keytool -import -trustcacerts -file files/TAK-ID-CA-01.pem -keystore files/truststore-TAK-ID-CA-02.jks -alias "TAK-ID-CA-01" -deststorepass atakatak
openssl x509 -trustout -in /opt/tak/certs/files/TAK-ID-CA-01.pem > ./caBundle.pem
cat /opt/tak/certs/files/TAK-ID-CA-02.pem >> ./caBundle.pem
openssl pkcs12 -export -in caBundle.pem -out caBundle.p12 -nokeys
```
Client impact: manual certs → new `caCert.p12` (or `caBundle.p12`) + new client cert; enrollment / Quick Connect → delete and recreate the server connection (data kept). Lab trick: `sudo date -s "07 July 2023 21:52:00"` to simulate expiry. Assumes no `--fips` flag was used.

## Renewing a CA keeping the same key (archived, lab-tested only)
Re-sign the existing CSR to preserve signatures (so existing client certs stay valid):
```shell
openssl x509 -sha256 -req -days 730 -in TAK-CA-01.csr -CA root-ca.pem -CAkey root-ca-do-not-share.key -out new-TAK-CA-01.pem -set_serial ${RANDOM} -extensions v3_ca -extfile ../config.cfg
openssl x509 -in new-TAK-CA-01.pem -addtrust clientAuth -addtrust serverAuth -setalias TAK-CA-01 -out new-TAK-CA-01-trusted.pem
keytool -import -alias new-TAK-CA-01 -file new-TAK-CA-01-trusted.pem -keystore truststore-TAK-CA-01.jks
cat root-ca.pem >> new-TAK-CA-01.pem ; cat root-ca-trusted.pem >> new-TAK-CA-01-trusted.pem
openssl verify -CAfile new-TAK-CA-01.pem -verbose takserver.pem
openssl pkcs12 -export -in new-TAK-CA-01-trusted.pem -out truststore-new-TAK-CA-01.p12 -nokeys
keytool -import -trustcacerts -file new-TAK-CA-01.pem -keystore truststore-new-TAK-CA-01.jks -noprompt
openssl pkcs12 -export -in new-TAK-CA-01.pem -inkey TAK-CA-01.key -out new-TAK-CA-01-signing.p12 -name new-TAK-CA-01
keytool -importkeystore -destkeystore new-TAK-CA-01-signing.jks -srckeystore new-TAK-CA-01-signing.p12 -srcstoretype PKCS12 -alias new-TAK-CA-01
# Root renewal
openssl x509 -x509toreq -sha256 -in root-ca.pem -signkey root-ca-do-not-share.key -out new-root-ca.csr
openssl x509 -sha256 -req -days 3652 -extensions v3_ca -extfile ../config.cfg -in new-root-ca.csr -signkey root-ca-do-not-share.key -out new-root-ca.pem
openssl x509 -in new-root-ca.pem -addtrust clientAuth -addtrust serverAuth -setalias TAK-ROOT-CA-01 -out new-root-ca-trusted.pem
openssl pkcs12 -export -in new-root-ca-trusted.pem -out truststore-new-root.p12 -nokeys -caname TAK-ROOT-CA-01
keytool -import -trustcacerts -file new-root-ca.pem -keystore truststore-new-root.jks -alias TAK-ROOT-CA-01 -noprompt
openssl verify -CAfile new-root-ca.pem -verbose TAK-CA-01.pem
```

## Files in `/opt/tak/certs/files` (as referenced on the site)
`root-ca.pem`, `root-ca-do-not-share.key`, `root-ca-trusted.pem`, `ca.pem`, `ca-do-not-share.key`, `ca-trusted.pem`, `ca.crl`, `<CA>.pem/.key/.crl`, `<CA>-trusted.pem`, `<CA>-signing.jks`, `truststore-root.jks/.p12`, `truststore-<CA>.jks/.p12`, `takserver.jks/.pem`, `fed-truststore.jks`, `<client>.pem/.key/.csr/.jks/.p12`.
Best practice: move client CSRs/private keys offline; keep only CA material on the server.

## Inspection commands
```shell
keytool -v -list -keystore /opt/tak/certs/files/takserver.jks
openssl pkcs12 -info -in /opt/tak/certs/files/truststore-root.p12
openssl x509 -text -in <cert>.pem
```

## Sources
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/lets-build-a-tak-server_archived/
- https://mytecknet.com/tak-pki-intermediateca/
- https://mytecknet.com/managing-users-and-groups/
- https://mytecknet.com/tak-certificate-error-peer-not-verified/
- https://mytecknet.com/tak-security-best-practices/
