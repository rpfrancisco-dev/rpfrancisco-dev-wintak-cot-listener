# 08 — AD/LDAP Integration

## Key constraints (at time of writing)
- AD/LDAP auth is **username/password** for ATAK/iTAK/WinTAK. CAC/token auth only works in **WebTAK**.
- Once linked, users/groups can't be managed via UserManager or Manage Users.
- Needs a read-only **service account** with interactive logon denied.
- Optional: have the domain CA sign the TAK Server (06); optional: AD CS (CES/CEP) for certificate enrollment.
- TAK Server can still be the CA for clients while using LDAP for auth.

## Recommended AD layout
OU `TAK` → sub-OUs `Users` and `Groups`. In SmartCardLogon-enforced domains, put TAK users in a group like `denyTAK_DomainAuth` with a GPO denying interactive logon (can be automated with a PowerShell scheduled task).

## CoreConfig examples
**AD:**
```xml
<auth default="ldap" x509groups="true" x509addAnonymous="false">
  <ldap url="ldap://mytecknet.labs/DC=mytecknet,DC=labs" style="AD"
        userstring="mytecknet\{username}" updateinterval="60"
        serviceAccountDN="CN=TAK [ServiceACCT],OU=ServiceACCTs,DC=mytecknet,DC=labs"
        serviceAccountCredential="<password>" groupBaseRDN="CN=Groups,OU=TAK"/>
</auth>
```
**LDAP (DS):**
```xml
<auth default="ldap" x509groups="true" x509addAnonymous="false">
  <ldap url="ldap://mytecknet.labs/" userstring="uid{username},ou=Users,ou=TAK,dc=mytecknet,dc=labs" updateinterval="60" style="DS"/>
</auth>
```
**LDAPS:** add `ldaps://` URL plus `ldapsTruststore="JKS" ldapsTruststoreFile="certs/files/ldaps-keystore.jks" ldapsTruststorePass="<pw>"`.

Notes:
- `default="ldap"` on `<auth>` is required or authentication errors occur.
- `groupBaseRDN` takes **OU paths only**, not a full DN.
- Userstring formats: `DOMAIN\{username}` or `{username}@FQDN`; URL `ldap://{DC|FQDN}/DC=domain,DC=com`.
- Web UI (*Configuration → Security and Authentication → Edit Configuration*, then *Test Service Account*) exists, but the author saw groups not populate correctly — prefer CoreConfig.

### Group prefix and IN/OUT groups
```xml
<ldap ... groupprefix="CN=tak_" groupNameExtractorRegex="CN=(.*?)(?:,|$)" .../>
```
- `groupprefix="CN=tak_"` → only groups starting `tak_` are used (`tak_GroupA` yes, `GroupC` no).
- IN/OUT via group naming: `tak_GroupA_WRITE` = **IN** group, `tak_GroupA_READ` = **OUT** group. Users in no group fall back to `__ANON__`.

## Testing with ldapsearch
```shell
sudo yum whatprovides ldapsearch
sudo yum install openldap-clients -y
ldapsearch -LLL -H ldap://mytecknet.labs:389 -b 'dc=mytecknet,dc=labs' -x -D 'mytecknet\tak.service' -W '(sAMAccountName=ghost)'
```
Portal test: `https://<server>:8446/` (open 8446/tcp), log in with bare username (no `DOMAIN\`).

## Microsoft CA auto-enrollment
Needs AD CS with CES/CEP using username/password auth. Import the AD CA into the TAK truststore if TAK is still the CA:
```shell
keytool -noprompt -import -trustcacerts -alias <alias> -keystore <TAKTruststoreJKS> -storepass <JKSPassword>
```
Configure `certificateSigning CA="MicrosoftCA"` in CoreConfig (the UI doesn't pass `svcUrl`) — XML in 03.

## Client connection with AD/LDAP
- Soft cert + LDAP: give `caCert.p12`, `clientCert.p12`, AD credentials; tick *Use Authentication*. Cert CN must match the user.
- Enrollment + LDAP: give `caCert.p12` + credentials; tick *Enroll for Client Certificate* + *Use Authentication*. iTAK didn't support this at the time.
- WebTAK: `https://<server>:8446`, bare username.

## Custom AD attributes → ATAK callsign/role/color
Only with an AD/LDAP backend and **ATAK only** (WinTAK lacks the Device Profile API used to push prefs at enrollment). Applies to new enrollments; existing devices must delete and re-add the connection.

1. Schema admin: `regsvr32 schmmgmt.dll` (elevated), MMC → *Active Directory Schema* snap-in.
2. Generate an OID per attribute (PowerShell script builds one from prefix `1.2.840.113556.1.8000.2554` + a GUID split into 7 hex parts); large orgs should get an official OID from their ISO NRA (ANSI in the US).
3. Create attributes (Unicode String): `tak_callsign`/LDAP `takCallsign`, `takRole`, `takColor`.
4. Add them as **Optional** attributes on the `user` class.
5. Set values:
   ```powershell
   Set-ADUser ghost -Add @{takCallsign = "Ghost"; takRole = "Team Lead"; takColor = "Cyan"}
   Get-ADUser ghost -Properties sAMAccountName, takCallsign, takRole, takColor
   # bulk
   Get-ADUser -Filter * -SearchBase "OU=Users,OU=TAK,DC=mytecknet,DC=labs" | ForEach-Object {Set-ADUser $_.sAMAccountName -Add @{takCallsign = "$($_.sAMAccountName)"; takRole = "Team Member"; takColor = "Cyan"}}
   ```
6. CoreConfig (`callsignAttribute`, `colorAttribute`, `roleAttribute` must equal the LDAP display names):
   ```xml
   <auth default="ldap" x509groups="true" x509addAnonymous="false">
     <ldap url="ldap://mytecknet.labs/DC=mytecknet,DC=labs" userstring="mytecknet\{username}" updateinterval="60"
           groupprefix="CN=tak_" groupNameExtractorRegex="CN=(.*?)(?:,|$)" style="AD"
           serviceAccountDN="CN=TAK [ServiceACCT],OU=ServiceAccounts,DC=mytecknet,DC=labs" serviceAccountCredential="PASSWORD"
           groupBaseRDN="OU=Groups,OU=TAK" userBaseRDN="OU=Users,OU=TAK"
           callsignAttribute="takCallsign" colorAttribute="takColor" roleAttribute="takRole"/>
     <File/>
   </auth>
   ```
Valid roles: Team Member, Team Lead, HQ, Sniper, Medic, Forward Observer, K9, RTO.
Valid colors: Black, Blue, Brown, Cyan, Dark Blue, Dark Green, Green, Magenta, Maroon, Orange, Purple, Red, Teal, White, Yellow.

(The bulk script as published is missing a closing `)` after `sAMAccountName` inside `$(...)`; corrected above.)

## Sources
- https://mytecknet.com/managing-users-and-groups/
- https://mytecknet.com/creating-custom-ad-ldap-attributes-for-atak/
- https://mytecknet.com/implementing-channels-in-tak/
