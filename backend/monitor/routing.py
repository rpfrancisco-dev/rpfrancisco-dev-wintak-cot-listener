from django.urls import path

from .consumers import DevicesConsumer

websocket_urlpatterns = [
    path("ws/devices", DevicesConsumer.as_asgi()),
]
