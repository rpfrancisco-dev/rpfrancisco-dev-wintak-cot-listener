from django.conf import settings
from django.urls import path, re_path
from django.views.static import serve

from monitor import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/devices", views.devices_json, name="devices-json"),
    path("api/objects", views.objects_json, name="objects-json"),
    re_path(
        r"^static/(?P<path>.*)$",
        serve,
        {"document_root": settings.FRONTEND_DIR},
    ),
]
