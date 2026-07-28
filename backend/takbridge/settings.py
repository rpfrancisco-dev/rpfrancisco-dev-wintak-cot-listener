"""Django settings for the TAK device monitor bridge."""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent      # backend/
REPO_DIR = BASE_DIR.parent                             # repo root
FRONTEND_DIR = REPO_DIR / "frontend"


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader — real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(REPO_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-for-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "daphne",
    "channels",
    "monitor",
]

MIDDLEWARE = []

ROOT_URLCONF = "takbridge.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIR],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": []},
    },
]

ASGI_APPLICATION = "takbridge.asgi.application"

CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

DATABASES = {}

USE_TZ = True

# --- TAK Server connection -------------------------------------------------
# The streaming endpoint. TAK Server >= 4.x exposes a WebSocket API that
# emits TAK protocol v1 protobuf frames at /takproto/1 on the SSL port.
TAK_WS_URL = os.environ.get("TAK_WS_URL", "wss://10.4.1.42:8443/takproto/1")

# Client certificate (PKCS#12) used for mutual TLS, and its password.
TAK_CLIENT_P12 = os.environ.get(
    "TAK_CLIENT_P12",
    r"C:\Users\Ryan Francisco\AppData\Roaming\WinTAK\SslCerts\client_39b0d9ef.p12",
)
TAK_P12_PASSWORD = os.environ.get("TAK_P12_PASSWORD", "atakatak")

# TAK servers ship self-signed certs; verification is off unless a CA bundle
# is supplied via TAK_CA_FILE and TAK_VERIFY_SSL=true.
TAK_VERIFY_SSL = os.environ.get("TAK_VERIFY_SSL", "false").lower() == "true"
TAK_CA_FILE = os.environ.get("TAK_CA_FILE", "")

# Optional extra CoT source: a UDP listener, run alongside the stream above.
# udp://host:port — a multicast host (224-239.x) joins that group; a host that
# isn't a local interface falls back to binding all interfaces on the port
# (so datagrams sent to any local IP on that port are still received).
# Set empty to disable.
TAK_UDP_URL = os.environ.get("TAK_UDP_URL", "udp://10.4.1.42:6969")

# Presence rules: past its CoT stale time a device shows as "stale"; after
# this many extra seconds without an update it is marked offline.
TAK_OFFLINE_GRACE_SECONDS = int(os.environ.get("TAK_OFFLINE_GRACE_SECONDS", "60"))

# Plotted objects: WinTAK persists every map object as CoT in this SQLite
# store. Polling it (read-only) gives the complete current set, seeding
# objects created before the backend started; the live stream then keeps
# them fresh. Set empty to rely on the stream alone.
TAK_STATESAVER_PATH = os.environ.get(
    "TAK_STATESAVER_PATH",
    os.path.join(
        os.environ.get("APPDATA", ""), "WinTAK", "Databases", "statesaver.sqlite"
    ),
)
TAK_STATESAVER_POLL_SECONDS = int(os.environ.get("TAK_STATESAVER_POLL_SECONDS", "10"))

# TAK Server's Marti API — the authoritative list of connected clients
# (/Marti/api/clientEndPoints), polled with the same client cert. This shows a
# client's true Connected/Disconnected state even when its SA isn't relayed to
# our CoT subscription (e.g. a different group). Defaults to the TAK_WS_URL
# host on https. Set empty to disable.
def _default_marti_url() -> str:
    from urllib.parse import urlparse

    u = urlparse(TAK_WS_URL)
    if u.hostname:
        return f"https://{u.hostname}:{u.port or 8443}"
    return ""


TAK_MARTI_URL = os.environ.get("TAK_MARTI_URL") or _default_marti_url()
TAK_MARTI_POLL_SECONDS = int(os.environ.get("TAK_MARTI_POLL_SECONDS", "8"))

# Routine plotted-object check: every interval, re-verify each object against
# the sources that still vouch for it (statesaver presence, recent CoT stream
# traffic, CoT stale time) and prune objects that stay missing for this many
# consecutive checks. 0 disables the check.
TAK_OBJECT_CHECK_SECONDS = int(os.environ.get("TAK_OBJECT_CHECK_SECONDS", "30"))
TAK_OBJECT_CHECK_MISSES = int(os.environ.get("TAK_OBJECT_CHECK_MISSES", "3"))
