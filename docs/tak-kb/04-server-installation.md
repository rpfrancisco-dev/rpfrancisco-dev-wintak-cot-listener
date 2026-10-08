# 04 — TAK Server Installation

Based on the TAK Server **5.0** guide (Dec 2023 release, updated Oct 2024), plus notes from the archived 4.8 guide. Complements, not replaces, the official TAK Server Configuration Guide.

## Requirements
- Min **4 cores, 8 GB RAM, 40 GB storage** (fits on a Raspberry Pi 4 8GB w/ 32 GB card).
- **Java OpenJDK**: 11 for TAK Server ≤4.9; **17 for 4.10+** (must be installed *before* the RPM on 4.10+).
- **PostgreSQL**: 10 for ≤4.7; **15 for 4.8+** (with PostGIS).
- OS: Rocky Linux 8 (*preferred*), RHEL 8, Ubuntu 22, Raspberry Pi OS 64-bit. CentOS 7 / RHEL 7 EOL June 2024 (not covered). Archived guide also used Fedora Server 35+.
- Deployment options: `.rpm`, `.deb`, or Docker (`docker.zip`) from tak.gov.

## Single-server install

### 1. Raise file-handle limits (Java threads)
```shell
echo -e "*      soft      nofile      32768\n*      hard      nofile      32768\n" | sudo tee --append /etc/security/limits.conf
sudo tail -n 15 /etc/security/limits.conf
```
(Default is 1024.)

### 2. EPEL
```shell
# Rocky 8
sudo dnf config-manager --set-enabled powertools
sudo dnf install epel-release -y
# RHEL 8
sudo subscription-manager repos --enable codeready-builder-for-rhel-8-$(arch)-rpms
sudo rpm --import https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-8
sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm -y
```

### 3. PostgreSQL/PostGIS repo
```shell
# Rocky/RHEL 8 (GPG keys rotated 03 Jan 2024)
sudo rpm --import https://download.postgresql.org/pub/repos/yum/keys/PGDG-RPM-GPG-KEY-RHEL
sudo dnf install https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm -y
sudo dnf -qy module disable postgresql

# Ubuntu / Raspberry Pi OS
sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget -O- https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/postgresql.org.gpg > /dev/null
# (legacy apt-key method for Debian 11 / Ubuntu 22.04 and older)
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt install gnupg -y     # if gpg missing on minimal installs
```
Then `sudo dnf update -y` or `sudo apt update -y`.

### 4. Java 17
```shell
sudo dnf install java-17-openjdk-devel -y      # Rocky/RHEL
java --version; sudo apt install openjdk-17-jre # Ubuntu/RPi
```

### 5. Copy installer & install
```shell
scp takserver-5.*.rpm <user>@<takserver>:~/        # macOS zsh: escape the wildcard  takserver-5.\*.rpm
sudo dnf install takserver-5.*.rpm -y               # Rocky/RHEL
sudo apt install ./takserver_5.0-RELEASE29_all.deb -y   # Ubuntu/RPi
```

### 6. SELinux (Rocky/RHEL)
```shell
getenforce
sudo dnf install checkpolicy          # Rocky
cd /opt/tak && sudo ./apply-selinux.sh
```
(Archived 4.8 note: had to remove `sudo` from line 12 of `apply-selinux.sh`.)

### 7. PKI, CoreConfig, start → see 05-pki-certificates.md, then:
```shell
sudo systemctl enable takserver.service
sudo systemctl start takserver.service
ls -l /opt/tak/logs/
tail -f /opt/tak/logs/takserver-messaging.log
```

## Two-server install
**Database server:** EPEL + PostgreSQL repo + Java, then
```shell
sudo dnf install takserver-database-5.0-RELEASE29.noarch.rpm --setopt=clean_requirements_on_remove=false -y
sudo apt install ./takserver-database_5.0-RELEASE29_all.deb -y
```
Open 5432/tcp (restrict to the core IP). Get the generated DB password:
```shell
grep -Eo ".+password=\".+/>" /opt/tak/CoreConfig.example.xml
```
**Core server:** limits.conf + Java, then
```shell
sudo dnf install takserver-core-5.0-RELEASE29.noarch.rpm -y
sudo apt install ./takserver-core_5.0-RELEASE29_all.deb -y
sudo su tak
grep -Eo ".+password=\".+/>" /opt/tak/CoreConfig.example.xml | sed -i 's/127.0.0.1/<dbIPAddress>/g' /opt/tak/CoreConfig.example.xml
grep -Eo ".+password=\".+/>" /opt/tak/CoreConfig.example.xml | sed -i 's/""/"<dbPassword>"/g' /opt/tak/CoreConfig.example.xml
```

## Updating
```shell
sudo dnf install takserver-5.0-RELEASE*.noarch.rpm --setopt=clean_requirements_on_remove=false -y
sudo apt install ./takserver-5.0-RELEASEx_all.deb
sudo systemctl daemon-reload
sudo systemctl restart takserver
sudo tail -f /opt/tak/logs/takserver-messaging.log
```

## Archived (4.8) notes still worth knowing
- Add your admin user to the `tak` group: `sudo usermod -aG tak <username>`.
- Pre-4.10 required `sudo /opt/tak/db-utils/takserver-setup-db.sh` (now done by the RPM).
- **FIPS + Java on Fedora/RHEL 8+** can cause `keytool error: java.io.IOException: keystore password was incorrect`. Fix: in `/usr/lib/jvm/<java-openJDK>/conf/security/java.security` set `security.useSystemPropertiesFile=false` before installing.
- Older install: `sudo rpm --import takserver-public-gpg.key` then `sudo yum install takserver-4.8-RELEASE31.noarch.rpm`.

## installTAK (universal installer)
- GitHub: https://github.com/myTeckNet/installTAK — one script for rpm, deb, and docker.zip deployments; text-UI setup wizard; includes Let's Encrypt support. Meant for a fresh OS or docker environment.
- Steps: install git and clone the repo → download the TAK Server binary/ZIP from tak.gov into the repo directory → run `./installTAK` (no args prints usage).
- Walk-through video: https://www.youtube.com/watch?v=-mjqOsbfu9c

## Key paths
| Path | Contents |
|---|---|
| `/opt/tak` | install root; `CoreConfig.xml`, `CoreConfig.example.xml`, `validateConfig.sh`, `apply-selinux.sh`, `UserAuthenticationFile.xml` |
| `/opt/tak/certs` | `cert-metadata.sh`, `makeRootCa.sh`, `makeCert.sh`, `revokeCert.sh` |
| `/opt/tak/certs/files` | generated keys, certs, keystores, truststores, CRLs |
| `/opt/tak/utils/UserManager.jar` | user/group/cert management CLI |
| `/opt/tak/logs` | `takserver-messaging.log`, `takserver-api.log` |
| `/opt/tak/db-utils` | DB setup scripts |

## Sources
- https://mytecknet.com/lets-build-a-tak-server/
- https://mytecknet.com/lets-build-a-tak-server_archived/
- https://mytecknet.com/installtak/
