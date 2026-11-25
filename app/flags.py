import json
import logging
import re
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from flagsmith import Flagsmith
from urllib3.util.retry import Retry

from . import config

log = logging.getLogger(__name__)
CACHE_SECONDS = 5
PACK_DEFAULTS = {"pack_core": True, "pack_wedding_2026": True, "pack_broad_test": False}
DEFAULT_RULES = [
    {"id": "core-01", "pack": "pack_core", "type": "text_regex", "pattern": r"(?i)\.apk\b",
     "severity": "DANGEROUS", "label": "Mentions an APK file"},
    {"id": "wed-01", "pack": "pack_wedding_2026", "type": "filename_regex",
     "pattern": r"(?i)(shaadi|wedding|marriage|invitation|nimantran|card).*\.(apk|xapk|apks)$",
     "severity": "DANGEROUS", "label": "Wedding card that is really an app"},
    {"id": "wed-02", "pack": "pack_wedding_2026", "type": "text_regex",
     "pattern": r"(?i)(download|install).{0,20}(app|apk).{0,30}(card|invitation)",
     "severity": "SUSPICIOUS", "label": "Asks you to install something to see a card"},
    {"id": "broad-01", "pack": "pack_broad_test", "type": "filename_regex",
     "pattern": r"(?i)(invitation|invite|card)", "severity": "DANGEROUS",
     "label": "Too broad: flags real invites"},
]


@dataclass
class UserFlags:
    enabled: dict[str, bool]
    rules: list[dict]
    warning_style: str = "calm"

    def active_rules(self) -> list[dict]:
        return [rule for rule in self.rules if self.enabled.get(rule["pack"], False)]


def _rule_ok(rule) -> bool:
    if not isinstance(rule, dict) or not all(
        isinstance(rule.get(k), str) and rule[k] for k in ("id", "pack", "type", "pattern", "severity", "label")
    ):
        return False
    if rule["severity"] not in ("OK", "SUSPICIOUS", "DANGEROUS"):
        return False
    if rule["type"] in ("filename_regex", "text_regex"):
        try:
            re.compile(rule["pattern"])
        except re.error:
            return False
        return True
    return rule["type"] == "domain"


def _rules(value: str) -> list[dict]:
    rules = json.loads(value)
    if not isinstance(rules, list):
        raise ValueError("Expected a signature list")
    valid = [rule for rule in rules if _rule_ok(rule)]
    if len(valid) != len(rules):
        # One bad rule edited live in Flagsmith must not throw away the others.
        log.warning("Skipped %d invalid scam signature(s)", len(rules) - len(valid))
    return valid


def _client():
    if not config.FLAGSMITH_ENV_KEY:
        raise ValueError("Missing environment key")
    return Flagsmith(environment_key=config.FLAGSMITH_ENV_KEY, request_timeout_seconds=3,
                     enable_local_evaluation=False, retries=Retry(total=0))


_env_cache: list = [0.0, None]  # [expires_at, packs]; /status polls every 3 s


def environment_packs() -> dict[str, bool]:
    with _lock:
        if _env_cache[1] is not None and monotonic() < _env_cache[0]:
            return dict(_env_cache[1])
    packs = {**dict.fromkeys(config.FLAGSMITH_FEATURE_IDS, False), **PACK_DEFAULTS}
    try:
        client = _client()
        with client.session:
            remote = client.get_environment_flags()
        for flag in remote.all_flags():
            if flag.feature_name.startswith("pack_") or flag.feature_name in packs:
                packs[flag.feature_name] = flag.enabled
    except Exception as exc:
        log.warning("Using default environment pack states (%s)", type(exc).__name__)
    with _lock:
        _env_cache[:] = [monotonic() + CACHE_SECONDS, packs]
    return dict(packs)


STYLES = ("calm", "urgent")


def _default_style(user_id: str) -> str:
    return STYLES[sum(user_id.encode()) % 2]


def _evaluate(user: dict) -> UserFlags:
    style = _default_style(user["id"])
    defaults = {
        "strict_mode": user["role"] == "parent", "host_invites": user["role"] == "host",
        "spoken_summary": True, **PACK_DEFAULTS,
    }
    try:
        client = _client()
        with client.session:
            remote = client.get_identity_flags(identifier=user["id"], traits={
                "lang": user["lang"], "role": user["role"],
                "beta": "true" if user.get("beta") else "false",
            })
        try:
            rules = _rules(remote.get_feature_value("scam_signatures"))
        except Exception as exc:
            log.warning("Using built-in scam signatures (%s)", type(exc).__name__)
            rules = DEFAULT_RULES
        enabled = {}
        for name in defaults.keys() | {rule["pack"] for rule in rules}:
            try:
                enabled[name] = remote.is_feature_enabled(name)
            except Exception as exc:
                log.warning("Using default for feature %s (%s)", name, type(exc).__name__)
                enabled[name] = defaults.get(name, False)
        try:
            value = str(remote.get_feature_value("warning_style") or "").strip().lower()
            style = value if value in STYLES else style
        except Exception as exc:
            log.warning("Using default warning_style (%s)", type(exc).__name__)
        return UserFlags(enabled, rules, style)
    except Exception as exc:
        log.warning("Flagsmith unavailable; using local defaults (%s)", type(exc).__name__)
        return UserFlags(defaults, DEFAULT_RULES, style)


_lock = Lock()
_cache: dict[tuple[str, str, str, bool], tuple[float, UserFlags]] = {}


def clear_cache() -> None:
    global _cache
    with _lock:
        # In-flight evaluations finish against the old dictionary after a rollback.
        _cache = {}
        _env_cache[:] = [0.0, None]


def for_user(user: dict) -> UserFlags:
    key = (user["id"], user["lang"], user["role"], bool(user.get("beta")))
    with _lock:
        cache = _cache
        now = monotonic()
        entry = cache.get(key)
        if entry and now < entry[0]:
            return entry[1]

    result = _evaluate(user)
    with _lock:
        if len(cache) >= 512 and key not in cache:
            del cache[next(iter(cache))]
        if key not in cache or cache[key][0] <= now + CACHE_SECONDS:
            cache[key] = (now + CACHE_SECONDS, result)
    return result


def signatures(user: dict) -> list[dict]:
    return for_user(user).active_rules()
