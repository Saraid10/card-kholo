import json
import os


def id_map(name: str) -> dict[str, int]:
    try:
        values = json.loads(os.getenv(name) or "{}")
    except ValueError:
        return {}
    if not isinstance(values, dict):
        return {}
    return {key: value for key, value in values.items() if type(value) is int and value > 0}


SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SPEAKERS = {lang: os.getenv(f"BULBUL_SPEAKER_{lang.upper()}") or "shubh" for lang in ("hi", "kn", "en")}
FLAGSMITH_ENV_KEY = os.getenv("FLAGSMITH_ENV_KEY", "")
FLAGSMITH_ADMIN_API_KEY = os.getenv("FLAGSMITH_ADMIN_API_KEY", "")
FLAGSMITH_ADMIN_ENV_KEY = os.getenv("FLAGSMITH_ADMIN_ENV_KEY", "")
FLAGSMITH_FEATURE_IDS = id_map("FLAGSMITH_FEATURE_IDS")
FLAGSMITH_SEGMENT_IDS = id_map("FLAGSMITH_SEGMENT_IDS")
FLAGSMITH_PROJECT_ID = os.getenv("FLAGSMITH_PROJECT_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = (os.getenv("TELEGRAM_BOT_USERNAME") or "CardKholoDemoBot").lstrip("@")
TELEGRAM_SECRET = os.getenv("TELEGRAM_SECRET", "")
NUDGEBEE_WEBHOOK_URL = os.getenv("NUDGEBEE_WEBHOOK_URL", "")
HOOK_SECRET = os.getenv("HOOK_SECRET", "")
APP_BASE_URL = (os.getenv("APP_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
ALLOWED_ORIGINS = [s.strip() for s in os.getenv("ALLOWED_ORIGINS", "").split(",") if s.strip()] or ["*"]
DEMO_CACHE = os.getenv("DEMO_CACHE", "").strip().lower() == "on"
REQUIRED = ("SARVAM_API_KEY", "FLAGSMITH_ENV_KEY")
OPTIONAL = {
    "Telegram": ("TELEGRAM_BOT_TOKEN", "TELEGRAM_SECRET"),
    "NudgeBee": ("NUDGEBEE_WEBHOOK_URL", "HOOK_SECRET"),
    "Flagsmith Admin API": ("FLAGSMITH_ADMIN_API_KEY", "FLAGSMITH_ADMIN_ENV_KEY", "FLAGSMITH_FEATURE_IDS", "FLAGSMITH_SEGMENT_IDS"),
}


def check_startup(log) -> None:
    """Fail fast without the core keys; one warning per optional service that is off."""
    missing = [name for name in REQUIRED if not globals()[name]]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}. "
                           "Set them in .env and start with: uvicorn app.main:app --env-file .env")
    for service, names in OPTIONAL.items():
        gaps = [name for name in names if not globals()[name]]
        if gaps:
            log.warning("%s disabled: missing %s", service, ", ".join(gaps))


MAX_FORM_BYTES = 20 * 1024 * 1024
MAX_TEXT_BYTES = 256 * 1024
