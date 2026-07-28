"""Poll the TAK Server Marti API for the authoritative connected-client list.

Unlike the passive CoT stream (which only sees clients whose SA is relayed to
our subscription's group), `/Marti/api/clientEndPoints` reports every client
the server knows about and its true Connected/Disconnected status. We reconcile
that into the device registry so presence matches the server exactly.
"""
from __future__ import annotations

import asyncio
import json
import logging
import urllib.request

from django.conf import settings

from .registry import registry
from .tak_client import build_ssl_context

log = logging.getLogger("monitor.marti")


def fetch_client_endpoints(ssl_ctx) -> list[dict]:
    """GET /Marti/api/clientEndPoints -> list of client dicts."""
    url = settings.TAK_MARTI_URL.rstrip("/") + "/Marti/api/clientEndPoints"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8", "replace"))
    data = payload.get("data") if isinstance(payload, dict) else payload
    return data or []


async def run_marti_poller() -> None:
    """Refresh the authoritative client list on an interval."""
    if not settings.TAK_MARTI_URL:
        return
    try:
        ssl_ctx = build_ssl_context()
    except Exception as exc:
        log.warning("Marti poller: cannot load client cert: %s", exc)
        registry.set_marti_state("error", str(exc))
        return

    interval = max(5, settings.TAK_MARTI_POLL_SECONDS)
    while True:
        try:
            endpoints = await asyncio.to_thread(fetch_client_endpoints, ssl_ctx)
            registry.merge_marti(endpoints)
            registry.set_marti_state("ok")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("Marti poll error: %s", exc)
            registry.set_marti_state("error", str(exc))
        await asyncio.sleep(interval)
