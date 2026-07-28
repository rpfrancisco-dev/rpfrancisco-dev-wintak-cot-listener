"""Routine check: are the plotted objects still current?

This TAK Server (5.6, verified 2026-07-22) keeps no queryable copy of loose
markers — `/Marti/api/cot/xml/<uid>` 404s, a fresh subscription gets no
latest-SA replay for objects, and the missions list is empty. Markers are
relayed once to subscribers and otherwise live only in each client's local
store. So "still on the TAK server" is checked against the truths that do
exist:

- WinTAK's statesaver (the plotted set the map actually shows right now),
- recent CoT traffic for the object on the stream/UDP feeds,
- the object's own CoT stale time,
- explicit `t-x-d-d` deletes (handled live by the stream handler).

Every `TAK_OBJECT_CHECK_SECONDS` this task re-reads the statesaver's visible
uid set and asks the object registry to reconcile: objects still vouched for
are marked *verified*, ones past their stale time *expired*, ones the
statesaver dropped *missing*. Missing objects are pruned from the dashboard
immediately; expired ones after `TAK_OBJECT_CHECK_MISSES` consecutive
failed checks.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path

from django.conf import settings

from .registry import object_registry

log = logging.getLogger("monitor.objcheck")


def read_visible_uids() -> set[str]:
    """The uids WinTAK's statesaver currently shows on the map."""
    path = settings.TAK_STATESAVER_PATH
    if not path or not Path(path).exists():
        raise FileNotFoundError(path)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    try:
        rows = con.execute(
            "select uid from cotevents where visible=1 and uid is not null"
        ).fetchall()
    finally:
        con.close()
    return {uid for (uid,) in rows}


async def run_object_checker() -> None:
    """Re-verify every plotted object on an interval; prune confirmed leavers."""
    interval = max(5, settings.TAK_OBJECT_CHECK_SECONDS)
    # An object counts as stream-fresh if a CoT for it arrived within two
    # check periods — markers aren't rebroadcast, so this only shields
    # recently created/updated ones while the statesaver catches up.
    fresh_ms = 2 * interval * 1000
    max_misses = max(1, settings.TAK_OBJECT_CHECK_MISSES)
    use_saver = bool(settings.TAK_STATESAVER_PATH)

    while True:
        await asyncio.sleep(interval)
        uids: set[str] | None = None
        error: str | None = None
        if use_saver:
            try:
                uids = await asyncio.to_thread(read_visible_uids)
            except sqlite3.OperationalError as exc:
                # Locked/being-written — skip evidence this pass, retry next.
                log.debug("object check: statesaver busy: %s", exc)
            except FileNotFoundError:
                error = "statesaver not found"
            except Exception as exc:
                error = str(exc)
                log.warning("object check: statesaver read failed: %s", exc)
        removed = object_registry.reconcile(uids, fresh_ms, max_misses, error)
        if removed:
            log.info(
                "object check: pruned %d object(s) no longer present: %s",
                len(removed),
                ", ".join(removed),
            )
