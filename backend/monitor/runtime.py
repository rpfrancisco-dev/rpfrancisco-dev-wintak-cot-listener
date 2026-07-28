"""Starts the TAK stream and sweeper once, on the daphne event loop."""
from __future__ import annotations

import asyncio
import logging

log = logging.getLogger("monitor.runtime")

_started = False


def ensure_background_tasks() -> None:
    global _started
    if _started:
        return
    _started = True
    from django.conf import settings

    from .marti import run_marti_poller
    from .object_check import run_object_checker
    from .registry import registry
    from .statesaver import run_statesaver_poller
    from .tak_client import run_tak_stream, run_udp_listener

    loop = asyncio.get_running_loop()
    loop.create_task(run_tak_stream(), name="tak-stream")
    loop.create_task(registry.run_sweeper(), name="stale-sweeper")
    if settings.TAK_UDP_URL:
        loop.create_task(run_udp_listener(), name="udp-listener")
    if settings.TAK_STATESAVER_PATH:
        loop.create_task(run_statesaver_poller(), name="statesaver-poller")
    if settings.TAK_MARTI_URL:
        loop.create_task(run_marti_poller(), name="marti-poller")
    if settings.TAK_OBJECT_CHECK_SECONDS:
        loop.create_task(run_object_checker(), name="object-checker")
    log.info("Background tasks started")
