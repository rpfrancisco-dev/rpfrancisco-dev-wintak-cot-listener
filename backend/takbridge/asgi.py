import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "takbridge.settings")

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from monitor.routing import websocket_urlpatterns  # noqa: E402
from monitor.runtime import ensure_background_tasks  # noqa: E402


class StartupWrapper:
    """Kick off the TAK stream + stale sweeper on the first ASGI event."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        ensure_background_tasks()
        await self.inner(scope, receive, send)


application = StartupWrapper(
    ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": URLRouter(websocket_urlpatterns),
        }
    )
)
