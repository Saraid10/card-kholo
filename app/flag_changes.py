"""Flagsmith change feed, with a durable history and a small dashboard cache."""

import json
import logging
from collections import deque
from threading import Lock

from . import config, db, flags

log = logging.getLogger("uvicorn.error.flagsmith")
_recent = deque(maxlen=30)
_lock = Lock()


def redact_hook_query(record: logging.LogRecord) -> bool:
    # Uvicorn includes the query string as the third access-log argument.
    args = record.args
    if isinstance(args, tuple) and len(args) == 5 and isinstance(args[2], str):
        path = args[2].partition("?")[0]
        if path.rstrip("/").endswith("/hooks/flagsmith"):
            record.args = (*args[:2], path, *args[3:])
    return True


def initialize() -> None:
    logging.getLogger("uvicorn.access").addFilter(redact_hook_query)
    with _lock, db.connection() as conn:
        rows = conn.execute("SELECT received_at AS time, feature, summary, source FROM flag_changes "
                            "ORDER BY id DESC LIMIT 30")
        _recent.clear()
        _recent.extend({**dict(row), "time": db.iso(row["time"])} for row in rows)


def latest() -> list[dict]:
    with _lock:
        return list(_recent)[:15]


def _object(value) -> dict:
    return value if isinstance(value, dict) else {}


def _label(value) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("username") or value.get("id")
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return str(value)[:180].strip().encode("utf-8", "replace").decode("utf-8")
    return ""


def _enabled(state: dict) -> bool | None:
    value = state.get("enabled")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return {"true": True, "false": False}.get(value.lower())
    return None


def record(raw: bytes) -> None:
    flags.clear_cache()
    try:
        event = _object(json.loads(raw))
    except (ValueError, UnicodeError, RecursionError):
        event = {}
    data = _object(event.get("data", event))
    new = _object(data.get("new_state", data))
    old = _object(data.get("previous_state", data.get("old_state")))
    feature = (_label(new.get("feature")) or _label(old.get("feature")) or _label(data.get("feature"))
               or _label(data.get("feature_name")))
    kind = _label(event.get("event_type") or data.get("event_type") or event.get("type"))
    author = _label(data.get("changed_by") or event.get("changed_by") or new.get("changed_by"))
    segment_info = new.get("feature_segment") or old.get("feature_segment") or data.get("feature_segment")
    segment = _label(_object(segment_info).get("segment")) or _label(segment_info)
    if segment.isdigit() and segment == str(config.FLAGSMITH_SEGMENT_IDS.get("canary_20")):
        segment = "canary_20"
    log.info("Flagsmith webhook: %s %s", kind or "event", feature or "unknown")

    before, after = _enabled(old), _enabled(new)
    missing = object()
    old_value = old.get("feature_state_value", old.get("value", missing))
    new_value = new.get("feature_state_value", new.get("value", missing))
    if not feature:
        feature, summary = "unknown", "Flag changed"
    elif after is not None and after != before:
        summary = f"{feature} turned {'ON' if after else 'OFF'}"
    elif new_value is not missing and new_value != old_value:
        summary = f"{feature} value updated"
    elif "delet" in kind.lower() or "remov" in kind.lower():
        summary = f"{feature} {'override removed' if segment else 'removed'}"
    else:
        summary = f"{feature} changed"
    if segment and feature != "unknown":
        summary += f" (segment {segment})"

    with _lock:
        with db.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            # NudgeBee edits Flagsmith before it calls back, so an open incident also counts.
            recent_rollback = conn.execute(
                "SELECT 1 FROM incidents WHERE pack=? AND (status='open' OR (status='rolled_back' "
                "AND closed_at BETWEEN datetime('now','-120 seconds') AND CURRENT_TIMESTAMP)) LIMIT 1", (feature,),
            ).fetchone()
            by_nudgebee = "nudgebee" in author.lower()  # Name the Admin API key "NudgeBee" in Flagsmith.
            source = "NudgeBee rollback" if recent_rollback or by_nudgebee else "Dashboard or API"
            row = conn.execute(
                "INSERT INTO flag_changes(feature,summary,enabled_before,enabled_after,source) VALUES (?,?,?,?,?) "
                "RETURNING received_at AS time, feature, summary, source", (feature, summary, before, after, source),
            ).fetchone()
        _recent.appendleft({**dict(row), "time": db.iso(row["time"])})
