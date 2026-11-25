import json
import os
import secrets
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

from .models import Identify

DB_PATH = Path(os.getenv("CARD_KHOLO_DB") or Path(__file__).resolve().parent.parent / "card_kholo.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    lang TEXT NOT NULL CHECK (lang IN ('hi','kn','en')),
    role TEXT NOT NULL CHECK (role IN ('parent','child','host')),
    beta INTEGER NOT NULL DEFAULT 0 CHECK (beta IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pairings (
    parent_id TEXT PRIMARY KEY NOT NULL REFERENCES users(id),
    child_chat_id INTEGER,
    child_name TEXT,
    pair_code TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id),
    verdict TEXT NOT NULL CHECK (verdict IN ('DANGEROUS','SUSPICIOUS','OK')),
    pack_hits TEXT NOT NULL DEFAULT '[]',
    file_sha256 TEXT,
    filename TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS false_alarms (
    id INTEGER PRIMARY KEY,
    scan_id TEXT NOT NULL REFERENCES scans(id),
    pack TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS false_alarms_window ON false_alarms(pack, created_at);
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY NOT NULL,
    pack TEXT NOT NULL,
    count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','rolled_back','rejected')),
    opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_incident ON incidents(pack) WHERE status = 'open';
CREATE TABLE IF NOT EXISTS flag_changes (
    id INTEGER PRIMARY KEY,
    feature TEXT NOT NULL,
    summary TEXT NOT NULL,
    enabled_before INTEGER,
    enabled_after INTEGER,
    source TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS incident_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    -- NULL targets NudgeBee; a chat ID targets the paired child's rollback notice.
    child_chat_id INTEGER,
    next_attempt_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS due_incident_notifications ON incident_notifications(next_attempt_at);
CREATE TABLE IF NOT EXISTS invites (
    token TEXT PRIMARY KEY NOT NULL,
    host_user_id TEXT NOT NULL REFERENCES users(id),
    host_family TEXT NOT NULL,
    couple TEXT NOT NULL,
    guest_name TEXT NOT NULL,
    guest_lang TEXT NOT NULL,
    functions TEXT NOT NULL,
    message TEXT NOT NULL,
    audio_b64 TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS experiment_events (
    scan_id TEXT NOT NULL REFERENCES scans(id),
    event TEXT NOT NULL,
    warning_style TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scan_id, event)
);
CREATE TABLE IF NOT EXISTS weddings (
    id TEXT PRIMARY KEY NOT NULL,
    host_user_id TEXT NOT NULL REFERENCES users(id),
    couple TEXT NOT NULL,
    host_family TEXT NOT NULL,
    functions TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def iso(timestamp: str | None) -> str | None:
    """SQLite CURRENT_TIMESTAMP is UTC without a zone; mark it so browsers do not read it as local time."""
    return timestamp.replace(" ", "T") + "Z" if timestamp and " " in timestamp else timestamp


@contextmanager
def connection():
    with closing(sqlite3.connect(DB_PATH, timeout=5)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            yield conn


def initialize() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        if "beta" not in {row["name"] for row in conn.execute("PRAGMA table_info(users)")}:
            conn.execute("ALTER TABLE users ADD COLUMN beta INTEGER NOT NULL DEFAULT 0 CHECK (beta IN (0,1))")
        if "warning_style" not in {row["name"] for row in conn.execute("PRAGMA table_info(scans)")}:
            conn.execute("ALTER TABLE scans ADD COLUMN warning_style TEXT")


def create_user(body: Identify) -> tuple[dict, str | None]:
    user = {"id": str(uuid4()), **body.model_dump()}
    pair_code = None
    with connection() as conn:
        conn.execute("INSERT INTO users (id, name, lang, role, beta) VALUES (:id, :name, :lang, :role, :beta)", user)
        if body.role == "parent":
            while True:
                pair_code = secrets.token_urlsafe(9)
                added = conn.execute(
                    "INSERT INTO pairings (parent_id, pair_code) VALUES (?, ?) "
                    "ON CONFLICT(pair_code) DO NOTHING", (user["id"], pair_code),
                )
                if added.rowcount:
                    break
    return user, pair_code


def get_user(user_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row is not None else None


def pair_child(code: str, chat_id: int, child_name: str) -> str | None:
    with connection() as conn:
        claimed = conn.execute(
            "UPDATE pairings SET child_chat_id = ?, child_name = ? WHERE pair_code = ? "
            "AND (child_chat_id IS NULL OR child_chat_id = ?)", (chat_id, child_name, code, chat_id),
        )
        if not claimed.rowcount:
            return None
        return conn.execute("SELECT u.name FROM users u JOIN pairings p ON p.parent_id = u.id "
                            "WHERE p.pair_code = ?", (code,)).fetchone()["name"]


def pairing_status(parent_id: str) -> dict:
    with connection() as conn:
        row = conn.execute(
            "SELECT child_name FROM pairings WHERE parent_id = ? AND child_chat_id IS NOT NULL", (parent_id,),
        ).fetchone()
    return {"linked": row is not None, "child_name": row["child_name"] if row is not None else None}


def paired_chat(parent_id: str) -> int | None:
    with connection() as conn:
        row = conn.execute("SELECT child_chat_id FROM pairings WHERE parent_id = ?", (parent_id,)).fetchone()
        return row["child_chat_id"] if row else None


def scan_context(scan_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT u.id, u.role, u.lang, u.beta, s.filename, date(s.created_at, '+330 minutes') AS scan_date "
            "FROM scans AS s JOIN users AS u ON u.id = s.user_id WHERE s.id = ?", (scan_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def save_scan(user_id: str, verdict: str, pack_hits: list[str], file_sha256: str | None,
              filename: str | None, warning_style: str | None = None) -> str:
    scan_id = str(uuid4())
    with connection() as conn:
        conn.execute(
            "INSERT INTO scans (id, user_id, verdict, pack_hits, file_sha256, filename, warning_style) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (scan_id, user_id, verdict, json.dumps(pack_hits), file_sha256, filename, warning_style),
        )
    return scan_id


EVENTS = ("warning_shown", "warning_played", "warning_completed", "opened_anyway")


def record_event(scan_id: str, event: str) -> bool:
    """Store one event per scan and kind, tagged with the scan's warning style. False for an unknown scan."""
    with connection() as conn:
        row = conn.execute("SELECT warning_style FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if row is None:
            return False
        conn.execute("INSERT OR IGNORE INTO experiment_events (scan_id, event, warning_style) VALUES (?, ?, ?)",
                     (scan_id, event, row["warning_style"] or "calm"))
    return True


def experiment() -> dict:
    with connection() as conn:
        rows = conn.execute("SELECT warning_style, event, COUNT(*) FROM experiment_events "
                            "GROUP BY warning_style, event").fetchall()
    counts = {(style, event): n for style, event, n in rows}
    variants = []
    for style in ("calm", "urgent"):
        stats = {event.removeprefix("warning_"): counts.get((style, event), 0) for event in EVENTS}
        stats["completion_rate"] = round(stats["completed"] / stats["shown"], 2) if stats["shown"] else 0
        variants.append({"name": style, **stats})
    return {"flag": "warning_style", "variants": variants}


def save_wedding(host_id: str, couple: str, family: str, functions: list[dict]) -> str:
    wedding_id = str(uuid4())
    with connection() as conn:
        conn.execute("INSERT INTO weddings(id,host_user_id,couple,host_family,functions) VALUES (?,?,?,?,?)",
                     (wedding_id, host_id, couple, family, json.dumps(functions, ensure_ascii=False)))
    return wedding_id


def latest_wedding(host_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM weddings WHERE host_user_id=? ORDER BY rowid DESC LIMIT 1",
                           (host_id,)).fetchone()
    return {**dict(row), "functions": json.loads(row["functions"])} if row else None


def save_invite(invite: dict) -> None:
    with connection() as conn:
        conn.execute("INSERT INTO invites(token,host_user_id,host_family,couple,guest_name,guest_lang,"
                     "functions,message,audio_b64) VALUES (:token,:host_user_id,:host_family,:couple,"
                     ":guest_name,:guest_lang,:functions,:message,:audio_b64)",
                     {**invite, "functions": json.dumps(invite["functions"], ensure_ascii=False)})


def get_invite(token: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM invites WHERE token=?", (token,)).fetchone()
    return {**dict(row), "functions": json.loads(row["functions"])} if row else None


def invite_family(token: str) -> str | None:
    with connection() as conn:
        row = conn.execute("SELECT host_family FROM invites WHERE token=?", (token,)).fetchone()
    return row["host_family"] if row else None
