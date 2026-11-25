"""False alarm incidents, approved rollbacks and queued external notifications."""

import asyncio
import json
import logging
from threading import Lock
from urllib.parse import quote
from uuid import uuid4

from fastapi import HTTPException
from httpx import Client, HTTPError, InvalidURL

from . import alerts, config, db, flag_changes, flags

log = logging.getLogger(__name__)
admin_log = logging.getLogger("uvicorn.error.flagsmith")
_rollback_lock = Lock()
WINDOW = "created_at >= datetime('now','-5 minutes')"


def record_feedback(scan_id: str, real_invite: bool, child_chat_id: int | None = None) -> dict | None:
    opened = []
    with db.connection() as conn:
        # Serialize duplicate button deliveries and concurrent feedback from the frontend.
        conn.execute("BEGIN IMMEDIATE")
        scan = conn.execute(
            "SELECT s.pack_hits, p.child_chat_id FROM scans s "
            "LEFT JOIN pairings p ON p.parent_id = s.user_id WHERE s.id = ?", (scan_id,),
        ).fetchone()
        if scan is None or (child_chat_id is not None and child_chat_id != scan["child_chat_id"]):
            return None
        counts = {}
        if real_invite:
            for pack in json.loads(scan["pack_hits"]):
                inserted = conn.execute(
                    "INSERT INTO false_alarms (scan_id, pack) SELECT ?, ? WHERE NOT EXISTS "
                    "(SELECT 1 FROM false_alarms WHERE scan_id = ? AND pack = ?)",
                    (scan_id, pack, scan_id, pack),
                )
                counts[pack] = conn.execute(
                    f"SELECT COUNT(*) FROM false_alarms WHERE pack = ? AND {WINDOW}",
                    (pack,),
                ).fetchone()[0]
                if inserted.rowcount and counts[pack] >= 3:
                    incident_id = f"inc_{uuid4().hex}"
                    created = conn.execute(
                        "INSERT INTO incidents (id, pack, count, status) VALUES (?, ?, ?, 'open') "
                        "ON CONFLICT(pack) WHERE status = 'open' DO NOTHING",
                        (incident_id, pack, counts[pack]),
                    )
                    if created.rowcount:
                        conn.execute("INSERT INTO incident_notifications (incident_id) VALUES (?)", (incident_id,))
                        opened.append(incident_id)
    for incident_id in opened:
        deliver_pending(incident_id)
    return {"ok": True, "pack_false_alarms": counts}


def _notify_workflow(job) -> bool:
    pack = job["pack"]
    count = job["count"]
    feature_id = config.FLAGSMITH_FEATURE_IDS.get(pack)
    segment_id = config.FLAGSMITH_SEGMENT_IDS.get("canary_20")
    if not (config.NUDGEBEE_WEBHOOK_URL and feature_id and segment_id):
        log.warning("Incident %s awaiting NudgeBee URL, feature ID or canary segment ID for %s", job["incident_id"], pack)
        return False
    payload = {
        "type": "false_alarm_spike", "pack": pack, "false_alarms": count, "window_minutes": 5,
        "flagsmith_feature_id": feature_id, "incident_id": job["incident_id"],
        "flagsmith_segment_id": segment_id, "rollout": "canary_20",
        "app_callback": f"{config.APP_BASE_URL}/hooks/rolled-back",
        "summary": f"Pack {pack} flagged {count} real invites as scams in 5 minutes",
    }
    try:
        with Client(timeout=10) as client:
            response = client.post(config.NUDGEBEE_WEBHOOK_URL, json=payload,
                                   headers={"Idempotency-Key": job["incident_id"]})
            response.raise_for_status()
        return True
    except (HTTPError, InvalidURL, ValueError) as exc:
        log.warning("NudgeBee delivery failed for %s (%s)", job["incident_id"], type(exc).__name__)
        return False


def deliver_pending(incident_id: str | None = None) -> None:
    query = ("SELECT n.id, n.incident_id, n.child_chat_id, i.pack, i.count "
             "FROM incident_notifications n JOIN incidents i ON i.id=n.incident_id "
             "WHERE n.next_attempt_at <= CURRENT_TIMESTAMP")
    with db.connection() as conn:
        if incident_id is None:
            jobs = conn.execute(query + " ORDER BY n.next_attempt_at, n.id LIMIT 50").fetchall()
        else:
            jobs = conn.execute(query + " AND i.id=? ORDER BY n.id", (incident_id,)).fetchall()
    for job in jobs:
        # Commit a short lease before the HTTP call. A stopped worker's delivery becomes eligible again.
        with db.connection() as conn:
            claim = conn.execute(
                "UPDATE incident_notifications SET next_attempt_at=datetime('now','+60 seconds') "
                "WHERE id=? AND next_attempt_at <= CURRENT_TIMESTAMP", (job["id"],),
            )
        if not claim.rowcount:
            continue
        if job["child_chat_id"] is None:
            delivered = _notify_workflow(job)
        else:
            delivered = alerts.notify_rollback(job["child_chat_id"], job["pack"])
        if delivered:
            with db.connection() as conn:
                conn.execute("DELETE FROM incident_notifications WHERE id=?", (job["id"],))


async def retry_notifications() -> None:
    while True:
        try:
            await asyncio.to_thread(deliver_pending)
        except Exception:
            log.exception("Could not process queued incident notifications")
        await asyncio.sleep(30)


def _disable_pack(pack: str) -> None:
    feature_id = config.FLAGSMITH_FEATURE_IDS.get(pack)
    segment_id = config.FLAGSMITH_SEGMENT_IDS.get("canary_20")
    if not (feature_id and segment_id and config.FLAGSMITH_ADMIN_API_KEY and config.FLAGSMITH_ADMIN_ENV_KEY):
        raise HTTPException(503, "Configure the Flagsmith Admin credentials, feature ID and canary_20 segment ID")
    env = quote(config.FLAGSMITH_ADMIN_ENV_KEY, safe="")
    url = f"https://api.flagsmith.com/api/__future__/environments/{env}/features/{feature_id}/"
    failed = []
    with Client(timeout=10, headers={"Authorization": f"Api-Key {config.FLAGSMITH_ADMIN_API_KEY}"}) as client:
        # Each call gets its own try so a failed DELETE still lets the PATCH turn the pack off.
        try:
            response = client.delete(f"{url}segment-overrides/{segment_id}/")
            admin_log.info("Flagsmith DELETE override for %s returned %s", pack, response.status_code)
            if response.status_code != 404:  # 404 means the override is already gone.
                response.raise_for_status()
        except (HTTPError, InvalidURL, ValueError) as exc:
            log.warning("Flagsmith override removal failed for %s (%s)", pack, type(exc).__name__)
            failed.append("removal of the canary override")
        try:
            response = client.patch(url, json={"environment_default": {"enabled": False}})
            admin_log.info("Flagsmith PATCH environment default for %s returned %s", pack, response.status_code)
            response.raise_for_status()
        except (HTTPError, InvalidURL, ValueError) as exc:
            log.warning("Flagsmith default update failed for %s (%s)", pack, type(exc).__name__)
            failed.append("disabling the environment default")
    flags.clear_cache()
    if failed:
        raise HTTPException(502, "Flagsmith did not confirm " + " and ".join(failed))


def rollback(incident_id: str, *, confirmed_pack: str | None = None) -> dict:
    # A callback confirms an external change. Only the admin fallback calls Flagsmith.
    with _rollback_lock:
        with db.connection() as conn:
            row = conn.execute("SELECT pack, status FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Unknown incident")
        pack = row["pack"]
        if confirmed_pack is not None and confirmed_pack != pack:
            raise HTTPException(409, "Callback pack does not match the incident")
        if row["status"] == "rejected":
            raise HTTPException(409, "Incident was rejected")
        if row["status"] == "open":
            if confirmed_pack is None:
                _disable_pack(pack)
            with db.connection() as conn:
                closed = conn.execute("UPDATE incidents SET status='rolled_back', closed_at=CURRENT_TIMESTAMP "
                                      "WHERE id=? AND status='open'", (incident_id,))
                if closed.rowcount:
                    conn.execute("DELETE FROM incident_notifications WHERE incident_id=? AND child_chat_id IS NULL",
                                 (incident_id,))
                    conn.execute("INSERT INTO incident_notifications (incident_id, child_chat_id) "
                                 "SELECT DISTINCT ?, child_chat_id FROM pairings WHERE child_chat_id IS NOT NULL",
                                 (incident_id,))
        flags.clear_cache()
    deliver_pending(incident_id)
    return {"ok": True}


def status() -> dict:
    enabled = flags.environment_packs()
    with db.connection() as conn:
        counts = dict(conn.execute(f"SELECT pack, COUNT(*) FROM false_alarms WHERE {WINDOW} GROUP BY pack"))
        rows = conn.execute("SELECT id, pack, count, status, opened_at, closed_at FROM incidents "
                            "ORDER BY opened_at DESC, rowid DESC").fetchall()
    packs = [{"name": name, "enabled": enabled.get(name, False), "false_alarms_5m": counts.get(name, 0)}
             for name in sorted(enabled.keys() | counts.keys())]
    incidents = [{**dict(row), "opened_at": db.iso(row["opened_at"]), "closed_at": db.iso(row["closed_at"])}
                 for row in rows]
    return {"packs": packs, "incidents": incidents, "last_alerts": alerts.recent_alerts(),
            "flag_changes": flag_changes.latest(), "experiment": db.experiment()}
