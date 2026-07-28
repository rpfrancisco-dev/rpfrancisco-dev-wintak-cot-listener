"""Poll WinTAK's statesaver.sqlite for the full set of plotted objects.

WinTAK persists every map object (markers, drawings, routes) as a CoT event
in the `cotevents` table. Reading it read-only gives the complete current set
— including objects created before this backend started, which the live
stream alone would miss. The DB is opened `mode=ro` because WinTAK holds a
WAL lock while running.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path

from django.conf import settings

from . import cot
from .registry import object_registry

log = logging.getLogger("monitor.statesaver")


def read_features() -> list[dict]:
    """Return GeoJSON features for every visible persisted plotted object."""
    path = settings.TAK_STATESAVER_PATH
    if not path or not Path(path).exists():
        return []
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    try:
        rows = con.execute(
            "select event from cotevents where visible=1 and event is not null"
        ).fetchall()
    finally:
        con.close()

    features = []
    for (xml,) in rows:
        result = cot.parse_frame(xml)
        # Keep only rows that classify as plotted objects (skip self/devices).
        if result and result[0] == "object" and result[1]:
            features.append(result[1])
    return features


async def run_statesaver_poller() -> None:
    """Refresh plotted objects from statesaver.sqlite on an interval."""
    if not settings.TAK_STATESAVER_PATH:
        return
    interval = max(2, settings.TAK_STATESAVER_POLL_SECONDS)
    logged_missing = False
    while True:
        try:
            features = await asyncio.to_thread(read_features)
            for feature in features:
                object_registry.upsert(feature, source="statesaver")
            logged_missing = False
        except FileNotFoundError:
            pass
        except sqlite3.OperationalError as exc:
            # Locked/being-written — just try again next tick.
            log.debug("statesaver read skipped: %s", exc)
        except Exception as exc:  # pragma: no cover
            if not logged_missing:
                log.warning("statesaver poll error: %s", exc)
                logged_missing = True
        await asyncio.sleep(interval)
