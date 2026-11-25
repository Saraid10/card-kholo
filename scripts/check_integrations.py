"""Check every live integration. Prints PASS / FAIL / SKIP per check and never prints a secret.

Usage (from the repo root):
  .venv\\Scripts\\python scripts\\check_integrations.py [--base-url https://x.onrender.com] [--nudgebee]
"""

import argparse
import base64
import inspect
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
TIMEOUT = 15
FLAGSMITH_API = "https://api.flagsmith.com/api/v1"
results = []


def env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def masked(value: str) -> str:
    return value[:4] + "…" if value else "(empty)"


def report(status: str, name: str, detail: str = "") -> None:
    results.append(status)
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""), flush=True)


def check(name: str):
    """Run fn with its own try/except and a hard 15 s timeout."""
    def wrap(fn):
        pool = ThreadPoolExecutor(1)
        try:
            outcome = pool.submit(fn).result(timeout=TIMEOUT)
            if outcome is not None:
                report(*outcome) if isinstance(outcome, tuple) and len(outcome) == 3 else report("PASS", name, str(outcome))
        except FutureTimeout:
            report("FAIL", name, f"timed out after {TIMEOUT} s")
        except Exception as exc:  # each check isolates its own failure
            message = str(exc)
            for secret in (env("TELEGRAM_BOT_TOKEN"), env("SARVAM_API_KEY"), env("FLAGSMITH_ADMIN_API_KEY")):
                if secret:
                    message = message.replace(secret, masked(secret))
            report("FAIL", name, f"{type(exc).__name__}: {message[:200]}")
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        return fn
    return wrap


def sarvam():
    @check("Sarvam Bulbul TTS (hi)")
    def _():
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=env("SARVAM_API_KEY") or "unset")
        params = inspect.signature(client.text_to_speech.convert).parameters
        lang_param = next((p for p in ("language_code", "target_language_code", "language") if p in params), None)
        print(f"       text_to_speech.convert language parameter: {lang_param} (app/sarvam_client.py uses language_code)")
        if lang_param != "language_code":
            return ("FAIL", "Sarvam Bulbul TTS (hi)", f"SDK expects {lang_param}; update app/sarvam_client.py")
        if not env("SARVAM_API_KEY"):
            return ("FAIL", "Sarvam Bulbul TTS (hi)", "SARVAM_API_KEY is empty")
        from app import sarvam_client
        audio = sarvam_client.synthesize("नमस्ते", "hi")
        return ("PASS", "Sarvam Bulbul TTS (hi)", f"{len(base64.b64decode(audio))} bytes of WAV")


def flagsmith_sdk():
    from flagsmith import Flagsmith
    key = env("FLAGSMITH_ENV_KEY")
    if not key:
        report("FAIL", "Flagsmith SDK", "FLAGSMITH_ENV_KEY is empty")
        return
    if not key.startswith("ser."):
        print("       note: FLAGSMITH_ENV_KEY is not a server-side key (ser.…); remote evaluation still works")
    identities = {
        "check-parent": ("parent", "false"),
        "check-beta": ("parent", "true"),
        "check-host": ("host", "false"),
    }
    seen = {}
    for identifier, (role, beta) in identities.items():
        @check(f"Flagsmith SDK identity {identifier}")
        def _(identifier=identifier, role=role, beta=beta):
            client = Flagsmith(environment_key=key, request_timeout_seconds=10)
            remote = client.get_identity_flags(identifier=identifier, traits={"lang": "hi", "role": role, "beta": beta})
            names = [f.feature_name for f in remote.all_flags()]
            packs = sorted(n for n in names if n.startswith("pack_") and remote.is_feature_enabled(n))
            info = {n: remote.is_feature_enabled(n) for n in ("strict_mode", "host_invites", "spoken_summary") if n in names}
            style = remote.get_feature_value("warning_style") if "warning_style" in names else None
            seen[identifier] = (packs, info, remote)
            problems = []
            if identifier == "check-beta" and "pack_broad_test" not in packs:
                problems.append("expected pack_broad_test ON (canary_20 via beta=true)")
            if identifier == "check-parent" and "pack_broad_test" in packs:
                problems.append("pack_broad_test ON for a non-beta user (fine only if it fell in the 20% split)")
            if role == "parent" and not info.get("strict_mode"):
                problems.append("expected strict_mode ON for parents")
            if role == "host" and not info.get("host_invites"):
                problems.append("expected host_invites ON for hosts")
            if style not in ("calm", "urgent"):
                problems.append(f"warning_style should be calm or urgent, got {style!r}")
            detail = f"packs ON={packs} {info} warning_style={style}"
            return ("FAIL" if problems else "PASS", f"Flagsmith SDK identity {identifier}",
                    detail + ("; " + "; ".join(problems) if problems else ""))

    @check("Flagsmith scam_signatures")
    def _():
        if "check-parent" not in seen:
            return ("SKIP", "Flagsmith scam_signatures", "identity check failed")
        rules = json.loads(seen["check-parent"][2].get_feature_value("scam_signatures"))
        from app import flags
        valid = [r for r in rules if flags._rule_ok(r)]
        types = sorted({r.get("type") for r in rules if isinstance(r, dict)})
        status = "PASS" if len(valid) == len(rules) and rules else "FAIL"
        return (status, "Flagsmith scam_signatures", f"{len(rules)} rules, {len(valid)} valid, types {types}")


def flagsmith_admin():
    api_key, project, env_key = env("FLAGSMITH_ADMIN_API_KEY"), env("FLAGSMITH_PROJECT_ID"), env("FLAGSMITH_ADMIN_ENV_KEY")
    if not (api_key and project):
        report("FAIL", "Flagsmith Admin API", "FLAGSMITH_ADMIN_API_KEY or FLAGSMITH_PROJECT_ID is empty")
        return
    http = httpx.Client(timeout=TIMEOUT, headers={"Authorization": f"Api-Key {api_key}"})
    state = {}

    def listing(path):
        response = http.get(f"{FLAGSMITH_API}{path}")
        response.raise_for_status()
        data = response.json()
        return data["results"] if isinstance(data, dict) else data

    def compare(label, var, actual):
        try:
            configured = json.loads(env(var) or "{}")
        except ValueError:
            configured = None
        wrong = ([f"{k}={v}" for k, v in configured.items() if actual.get(k) != v]
                 if isinstance(configured, dict) else ["not valid JSON"])
        print(f"       correct {var}={json.dumps(actual, separators=(',', ':'))}")
        if not configured:
            return ("FAIL", label, f"{var} is empty; paste the line above into .env / Render")
        return ("FAIL" if wrong else "PASS", label, f"mismatched entries: {wrong}" if wrong else "all entries match")

    @check("Flagsmith Admin features")
    def _():
        features = listing(f"/projects/{project}/features/?page_size=100")
        state["features"] = {f["name"]: f["id"] for f in features}
        return compare("Flagsmith Admin features", "FLAGSMITH_FEATURE_IDS", state["features"])

    @check("Flagsmith Admin segments")
    def _():
        segments = listing(f"/projects/{project}/segments/?page_size=100")
        state["segments"] = {s["name"]: s["id"] for s in segments}
        result = compare("Flagsmith Admin segments", "FLAGSMITH_SEGMENT_IDS", state["segments"])
        if "canary_20" not in state["segments"]:
            return ("FAIL", "Flagsmith Admin segments", "no segment named canary_20 in the project")
        return result

    @check("Flagsmith canary_20 override on pack_broad_test")
    def _():
        name = "Flagsmith canary_20 override on pack_broad_test"
        feature_id = state.get("features", {}).get("pack_broad_test")
        segment_id = state.get("segments", {}).get("canary_20")
        if not (env_key and feature_id and segment_id):
            return ("SKIP", name, "needs FLAGSMITH_ADMIN_ENV_KEY, pack_broad_test and canary_20")
        environment = http.get(f"{FLAGSMITH_API}/environments/{env_key}/")
        environment.raise_for_status()
        overrides = listing(f"/features/feature-segments/?environment={environment.json()['id']}&feature={feature_id}")
        present = any(o.get("segment") == segment_id for o in overrides)
        return ("PASS" if present else "FAIL", name,
                "override present" if present else "missing: add a canary_20 segment override (ON) to pack_broad_test")


def telegram(base_url: str):
    token = env("TELEGRAM_BOT_TOKEN")
    if not token:
        report("SKIP", "Telegram", "TELEGRAM_BOT_TOKEN is empty")
        return

    @check("Telegram getMe")
    def _():
        me = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=TIMEOUT).json()
        if not me.get("ok"):
            return ("FAIL", "Telegram getMe", me.get("description", "not ok"))
        username = me["result"]["username"]
        expected = env("TELEGRAM_BOT_USERNAME").lstrip("@")
        status = "PASS" if username == expected else "FAIL"
        return (status, "Telegram getMe", f"bot @{username}" + ("" if status == "PASS" else
                f"; TELEGRAM_BOT_USERNAME is {expected!r} (also set VITE_TELEGRAM_BOT_USERNAME)"))

    @check("Telegram getWebhookInfo")
    def _():
        if "localhost" in base_url or "127.0.0.1" in base_url:
            return ("SKIP", "Telegram getWebhookInfo", "APP_BASE_URL is local; Telegram needs the public HTTPS URL")
        info = httpx.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=TIMEOUT).json()["result"]
        expected = f"{base_url}/hooks/telegram"
        problems = []
        if info.get("url") != expected:
            problems.append(f"url is {info.get('url')!r}, expected {expected!r} (restart the backend to re-register)")
        if info.get("last_error_message"):
            problems.append(f"last error: {info['last_error_message']}")
        return ("FAIL" if problems else "PASS", "Telegram getWebhookInfo", "; ".join(problems) or expected)


def backend(base_url: str):
    @check("Backend /health")
    def _():
        response = httpx.get(f"{base_url}/health", timeout=TIMEOUT)
        ok = response.status_code == 200 and response.json() == {"ok": True}
        return ("PASS" if ok else "FAIL", "Backend /health", f"{response.status_code} {response.text[:80]}")

    @check("Backend CORS preflight")
    def _():
        origins = [o.strip() for o in env("ALLOWED_ORIGINS").split(",") if o.strip()]
        if not origins:
            return ("FAIL", "Backend CORS preflight", "ALLOWED_ORIGINS is empty (the backend then allows *)")
        response = httpx.options(f"{base_url}/api/scan", timeout=TIMEOUT, headers={
            "Origin": origins[0], "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"})
        allowed = response.headers.get("access-control-allow-origin")
        ok = response.status_code == 200 and allowed in (origins[0], "*")
        return ("PASS" if ok else "FAIL", "Backend CORS preflight",
                f"origin {origins[0]} -> {response.status_code}, allow-origin={allowed}")


def nudgebee(base_url: str):
    @check("NudgeBee webhook")
    def _():
        url = env("NUDGEBEE_WEBHOOK_URL")
        if not url:
            return ("FAIL", "NudgeBee webhook", "NUDGEBEE_WEBHOOK_URL is empty")
        features = json.loads(env("FLAGSMITH_FEATURE_IDS") or "{}")
        segments = json.loads(env("FLAGSMITH_SEGMENT_IDS") or "{}")
        body = {
            "type": "false_alarm_spike", "pack": "pack_broad_test", "false_alarms": 3, "window_minutes": 5,
            "flagsmith_feature_id": features.get("pack_broad_test"),
            "flagsmith_segment_id": segments.get("canary_20"), "rollout": "canary_20",
            "incident_id": "check-test", "app_callback": f"{base_url}/hooks/rolled-back",
            "summary": "Integration check, please reject",
        }
        response = httpx.post(url, json=body, timeout=TIMEOUT, headers={"Idempotency-Key": "check-test"})
        print("       Reminder: REJECT the 'check-test' run in NudgeBee (approving it turns pack_broad_test OFF).")
        return ("PASS" if response.is_success else "FAIL", "NudgeBee webhook", f"HTTP {response.status_code}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=env("APP_BASE_URL") or "http://127.0.0.1:8000")
    parser.add_argument("--nudgebee", action="store_true", help="also POST a test incident to NudgeBee")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    print(f"Card Kholo integration check against {base_url} ({time.strftime('%H:%M:%S')})")
    sarvam()
    flagsmith_sdk()
    flagsmith_admin()
    telegram(base_url)
    backend(base_url)
    if args.nudgebee:
        nudgebee(base_url)
    print(f"\n{results.count('PASS')} PASS, {results.count('FAIL')} FAIL, {results.count('SKIP')} SKIP")
    sys.exit(1 if "FAIL" in results else 0)


if __name__ == "__main__":
    main()
