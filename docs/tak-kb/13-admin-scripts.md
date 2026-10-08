# 13 — myTeckNet Admin Scripts (summaries)

All three assume TAK Server is the CA. Each self-elevates (`[ "$UID" -eq 0 ] || exec sudo "$0" "$@"`), uses `dir=/opt/tak`, `certs=$dir/certs/files`, and copies output to the invoking user's home via `curuser=$(printenv SUDO_USER)`. Full source is on each article — copy from there rather than retyping.

## makeCert.sh wrapper — "Making TAK User Accounts Easy" (v1.5)
Usage: `./makeCert.sh <commonname> [<certdays>] [<group>] [admin]` (use `0` as placeholder to keep defaults).
Logic:
1. No args / `-h` → usage.
2. `certdays` must be numeric; temporarily `sed`s `-days 730` → `-days N` in `/opt/tak/certs/makeCert.sh`, then restores 730.
3. Group → `UserManager.jar certmod -g <group>` (default `__ANON__`).
4. `admin` → `UserManager.jar certmod -A`.
5. Runs `makeCert.sh client <cn>`, `chown -R tak:tak /opt/tak`, copies `<cn>.p12` to home and fixes ownership.
Examples: `./makeCert.sh ATAK01 30 Group2`, `./makeCert.sh ATAK02 0 0 admin`.
Source: https://mytecknet.com/making-user-accounts-easy/

## revokeCert.sh wrapper — "Revoking TAK Client Certificates Easy" (v1.0)
Usage: `./revokeCert.sh <client>` (prompts if omitted).
Logic:
1. Sources `cert-metadata.sh`.
2. Finds issuer CN via `openssl x509 -text -in files/<client>.pem | grep -Eo "CN=.+"`.
3. Warns (yellow) if `CoreConfig.xml` has no `<crl .../>` element and prints the line to add.
4. If `files/<issuer>.pem` exists, uses it as CA and key; else falls back to `ca` / `ca-do-not-share`.
5. Calls the stock `/opt/tak/certs/revokeCert.sh files/<client> files/<key> files/<ca>`.
6. Optionally deletes `<client>.{pem,key,csr,jks}` and restarts `takserver`.
Source: https://mytecknet.com/revoking-tak-certificates-easy/

## genRandpwdCert.sh — "Random Client Certificate Passwords" (v1.1)
Purpose: re-export a cert P12 with a unique random password so no shared password is distributed.
Logic:
1. Random password: `openssl rand -base64 16 | tr -dc '<allowed chars>'`.
2. Detect OpenSSL 3 legacy provider (`openssl list -providers`) → add `-legacy`.
3. Input `truststore-root` → export `ca-trusted.pem` with `-nokeys`.
4. Input `truststore-<CA>` → strip first 11 chars to get `<CA>`, export `<CA>-trusted.pem` with `-nokeys`.
5. Client → `openssl pkcs12 -export -in <c>.pem -inkey <c>.key -out ~/<c>.p12 -name <c> -CAfile ca.pem -passin pass:${PASS} -passout pass:${randpwd}`.
6. Prints verify command `openssl pkcs12 -info -in <c>.p12`.
Source: https://mytecknet.com/random-client-certificate-passwords/

## installPEM.sh (third-party, shared in the external-CA guide)
Splits a multi-cert PEM and imports each into a JKS truststore with keytool. See 06.

## installTAK
Universal installer — see 04. https://github.com/myTeckNet/installTAK

## Other downloads on the site
- Data package templates: Soft-Cert.zip, Auto-Enrollment.zip, iTAK.zip, OpenMapSources.zip (creating-tak-data-packages-for-enrollment).
- ATAK Preferences Key 4.8 (.xlsx).
- `channels.zip` (archived channels method).
- TAK Visio stencils (`TAK-Visio-Stencils.vssx`) and icons (`TAK-Visio-Icons.pptx`) v1.1 incl. Federation Hub — https://mytecknet.com/tak-visio-stencils/
