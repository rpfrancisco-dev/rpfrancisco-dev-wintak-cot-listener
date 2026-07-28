from django.http import JsonResponse
from django.shortcuts import render

from .registry import object_registry, registry


def index(request):
    return render(request, "index.html")


def devices_json(request):
    """One-shot snapshot, handy for curl/urllib smoke tests."""
    return JsonResponse(registry.snapshot())


def objects_json(request):
    """Plotted objects as a GeoJSON FeatureCollection (Method 2)."""
    return JsonResponse(object_registry.to_featurecollection())
