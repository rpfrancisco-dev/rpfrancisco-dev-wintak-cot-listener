# 06 — External CAs & Let's Encrypt

Goal: give TAK Server a certificate from an enterprise or public CA for trusted connections.

**Warning from the site:** a *public* CA like Let's Encrypt must not be what authenticates clients — anyone could obtain a cert from it and connect. Use it for the public-facing enrollment/login connector (8446), keep client auth on your own CA.

## 1. Create a CSR (any host with OpenSSL; the private key is what matters)
Method 1 — one line:
```shell
openssl req -new -newkey rsa:2048 -sha256 -keyout takserver.key -out takserver.csr -subj /CN=<FQDN>
```
Method 2 — config file with SANs (`config.cnf`):
```text
[req]
prompt=no
distinguished_name=dn
req_extensions=ext

[dn]
CN=tak.mytecknet.labs
OU=PKI
O=myTeckNet
C=US

[ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = tak.mytecknet.labs
DNS.2 = taksvr01.mytecknet.labs
IP.1 = 192.168.255.240
```
```shell
openssl req -new -newkey rsa:2048 -sha256 -config config.cnf -keyout takserver.key -out takserver.csr
openssl req -text -in takserver.csr -noout -verify
cat takserver.csr
```

## 2. Get it signed
- **Web enrollment** (`https://<ca>/certsrv`): *Request a certificate* → submit base-64 CSR → choose template → download **Base-64 certificate chain** (`.p7b`).
- **CLI (Windows CA)**:
  ```shell
  certreq -submit -attrib "CertificateTemplate:TAKServer" takserver.csr
  certutil -retrieve <ID>      # if pending approval
  ```
- The server template **must include both Server and Client Authentication** EKUs, or federation will fail. Recommended: a TAK Server template (client+server auth) and a TAK Client template (client auth only).
- If you only get the leaf cert, export intermediate/root via the Windows cert viewer (*Certification Path → View Certificate → Details → Copy to File → Base-64 X.509*) and build `ca-truststore-bundle.pem` with intermediates first, root last.

PEM chain order: private key → issued cert → intermediate(s) → root.

## 3. Convert to PKCS12
From `.p7b`:
```shell
openssl pkcs7 -print_certs -in takserver.p7b -out takserver.cer
openssl pkcs12 -export -out takserver.p12 -inkey takserver.key -in takserver.cer -name <FriendlyName> -passin pass:<pw> -passout pass:<pw>
openssl pkcs12 -info -in takserver.p12
```
From PEM + bundle:
```shell
openssl pkcs12 -export -certfile ca-truststore-bundle.pem -out takserver.p12 -inkey takserver.key -in takserver.cer -name <FriendlyName> -passin pass:<pw> -passout pass:<pw>
```

## 4. Convert to Java keystores
Keystore (server identity):
```shell
keytool -importkeystore -srcstoretype PKCS12 -destkeystore takserver.jks -srckeystore takserver.p12 -alias <FriendlyName> -srcstorepass <p12pw> -deststorepass <jkspw> -destkeypass <jkspw>
```
Truststore (CAs only — strip the leaf cert):
```shell
openssl pkcs7 -inform PEM -outform PEM -in takserver.p7b -print_certs > ca-truststore-bundle.cer
# edit: remove the first (leaf) certificate, keep intermediate + root; append any extra CAs to trust
```
Import every cert in a PEM into a JKS — the site shares a small `installPEM.sh` (credited to Josh Blomberg; original author unknown). Logic: count `END CERTIFICATE` markers, split the file with `awk` per cert, and `keytool -noprompt -import -trustcacerts -alias <file>-<n> -keystore <jks> -storepass <pw>` each one. Usage: `./installPEM.sh ca-truststore-bundle.cer atakatak takserver-truststore.jks`.

## 5. Apply
```shell
cp -v takserver.jks /opt/tak/certs/files/takserver-signed.jks
cp -v takserver-truststore.jks /opt/tak/certs/files/takserver-truststore.jks
sudo chown -R tak:tak /opt/tak
cd /opt/tak && sudo systemctl stop takserver
cp CoreConfig.xml ~ ; cp CoreConfig.example.xml ~      # backups
```
Edit both config files: `keystoreFile` → `takserver-signed.jks` in `<security>` **and** `<federation>`; `truststoreFile` → `takserver-truststore.jks` in `<security>` only. Then `sh validateConfig.sh`, `chown`, restart. Expect in `takserver-api.log`: `Tomcat initialized with port(s): 8443 (https) 8446 (https)`.
A new admin cert from the new CA is required afterwards (client-auth template; P12 is enough, no JKS).

**Hybrid challenge (publicly signed server, TAK Server still issuing client certs):** add the TAK CA to the server truststore, and give clients a new `caCert.p12` containing both the external and internal CA chains.

## Let's Encrypt on the 8446 connector
```shell
sudo yum install epel-release && sudo yum install snapd
sudo systemctl enable --now snapd.socket
sudo ln -s /var/lib/snapd/snap /snap
sudo firewall-cmd --zone=public --add-port 80/tcp --permanent && sudo firewall-cmd --reload   # needed for the challenge (port-forward 80 if behind NAT)
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot certonly --standalone
openssl x509 -text -in /etc/letsencrypt/live/<fqdn>/fullchain.pem -noout
sudo certbot renew --dry-run
sudo openssl pkcs12 -export -in /etc/letsencrypt/live/<fqdn>/fullchain.pem -inkey /etc/letsencrypt/live/<fqdn>/privkey.pem -out takserver-le.p12 -name <fqdn>
sudo keytool -importkeystore -destkeystore takserver-le.jks -srckeystore takserver-le.p12 -srcstoretype pkcs12
sudo mv takserver-le.jks /opt/tak/certs/files && sudo chown -R tak:tak /opt/tak
```
CoreConfig:
```xml
<connector port="8446" clientAuth="false" _name="LetsEncrypt" keystore="JKS" keystoreFile="certs/files/takserver-le.jks" keystorePass="atakatak"/>
<!-- <connector port="8446" clientAuth="true" _name="cert_https"/> -->
```
Result: unprovisioned clients can use **Quick Connect** (credentials only) without being handed the self-signed CA. (The article states LE certs are valid 30 days; LE's standard lifetime is 90 days — verify.)

## Sources
- https://mytecknet.com/lets-sign-our-tak-server/
- https://mytecknet.com/managing-users-and-groups/
