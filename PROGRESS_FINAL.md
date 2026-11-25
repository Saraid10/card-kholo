# Card Kholo: final integration progress

## Current phase
Phases 0-9 done offline (user asked to do everything except env/provider steps).
Next: user fills `.env` / `CardKholo/.env.local`, deploys, then runs the live checks below.

## Layout
- Backend = repo root (`app/`, `tests/`, `scripts/`, `demo/`, root `.env`). Prompt's `backend/` = repo root.
- Frontend = `CardKholo/` (`CardKholo/.env.local`). `web/` empty, `__MACOSX/` junk (gitignored).
- Git: branch `master`, no commits yet.

## Done
- P1 env: names match spec; `.env` via `uvicorn --env-file .env` (python-dotenv); fail-fast without
  SARVAM_API_KEY / FLAGSMITH_ENV_KEY; one warning per missing optional service; no hardcoded secrets.
- P2 `scripts/check_integrations.py` (`--base-url`, `--nudgebee`). TTS language param = `language_code` (SDK 0.1.49).
- P3 backend: one bad `scam_signatures` rule is skipped, not the whole list; Doc AI + vision share a 28 s budget
  (fits the 35 s scan timeout); Hindi/Kannada warning audio in native script.
- P4: experiment built (`warning_style` from Flagsmith with a hash fallback, `POST /api/events` 400/404,
  `experiment` in `/api/status`, dedup per scan+event). Plan B: DELETE and PATCH each attempted.
  Feed: "NudgeBee rollback" if open incident / rolled back < 2 min / changed_by contains "nudgebee".
  Times in /api/status are ISO UTC with Z. Raw webhook body no longer logged. Rollback accepts numeric incident_id.
  `/api/status` caches environment packs 5 s. `/health` accepts HEAD.
- P5 `scripts/simulate_incident.py`; `demo/make_test_apk.py` verified (text manifest + empty dex).
- P6 frontend: "Waking up the server" banner + /health ping on load; one audio player at a time;
  `warning_played` only when audio really starts; `opened_anyway` sent; pairing poll retries non-404 errors;
  control room: 5 s highlight, canary tag, red pack at >= 3, "Leading" only with >= 5 shown each,
  family alerts render backend fields; host wedding sends every Function field; "real" sample = demo PDF.
- P7 local e2e (dummy keys, DEMO_CACHE=on): identify, link QR, fake APK STOP, first hour, events,
  real sample OK with 2 functions, calendar, directions, /status, 390 px no overflow. 51 tests pass, build OK.
- P8 requirements pinned, `.python-version` 3.12, Dockerfile uses `$PORT`, README deploy section.
- P9 README: frontend, scripts, experiment, deploy, reset checklist, privacy, AI disclosure updated.

## Open issues (not fixed)
- P1: calendar ICS lives 10 min in memory (`/api/ics`); "Remind me" 404s later or after a Render restart.
- P1: frontend `/i/:id` page uses demo data (no `GET /api/invites/{id}`); real links use backend `/i/{token}`.
- P1: Render free tier loses SQLite on restart (pairings, incidents, feed).
- P2: language pills 30 px and logo 32 px tap targets (< 48 px).
- P2: Calendar Today/Tomorrow uses device time zone, not forced Asia/Kolkata.
- P2: pre-existing oxlint warnings (Calendar purity, Check set-state-in-effect, useVoice refs).

## Decisions
- Don't rename folders. Env loaded by `--env-file`, not at import (tests never see real keys).
- Contract unchanged; `warning_style` and `experiment` were already optional fields in it.
- Name the Flagsmith Admin API key used by NudgeBee "NudgeBee" so the feed can label its changes.

## User must do
1. Fill `.env` and `CardKholo/.env.local` (never paste keys in chat). 2. Deploy Render + Vercel (README "Deploy").
3. Run `check_integrations.py --base-url <render>`, register the Flagsmith webhook, then `--nudgebee`.
4. Keep-warm ping on `/health` every 10 min. 5. Rehearse (README reset checklist).

## Provisioning + deploy prep (third prompt) - status 2026-11-25
- Phase 0: no Chrome. All keys in `.env`; Telegram bot @cardkholo_alert_bot (getMe PASS). NudgeBee workflow done by user.
- Flagsmith (env Development 119652, versioning v2): all items correct EXCEPT `warning_style` variant
  (variant value is now the text "50%" with 0% weighting -> 20/20 test users get calm). Needs value `urgent`, weighting 50.
- IDs in `.env`: features pack_core 302765, pack_wedding_2026 302766, pack_broad_test 302767; canary_20 1203642.
- check_integrations (local, real keys): 10 PASS, Telegram SKIP. TTS language param = `language_code`.
- Local e2e (real Sarvam): real card PDF OK 4 functions in ~10 s, PNG OK, ICS 4 alarms, APK DANGEROUS + Hindi
  audio, bit.ly SUSPICIOUS, opened/events/status/pairing OK.
- FIX P0: Doc AI took ~23 s, vision ~16 s, so sequential reading missed the 35 s scan timeout (0 functions).
  `read_card` now runs both in parallel and takes the first card with functions (budget 28 s).
- Demo files: `demo/make_real_card.py` -> Priya_Arjun_Wedding_Card.pdf/.png + invitation_card_1..3.pdf.
  `simulate_incident.py` uses them.
- Deploy prep: `render.yaml` (root, free, /health, env names sync:false), requirements verified in a fresh venv,
  `.gitignore` extended (.env*, *.db, demo/*.apk), secret scan clean (only dummy "test" keys in tests),
  `deploy/DEPLOY_STEPS.md`, `deploy/DEMO_CHECKLIST.md`. gh logged in as Saraid10, no remote yet.
- Waiting on user: Telegram bot, warning_style fix, NudgeBee workflow check, commit/push, deploy choices.
- Deploy: warning_style fixed (12/20 urgent). Repo github.com/Saraid10/card-kholo (private, main).
  Vercel prod https://card-kholo.vercel.app (project card-kholo, VITE_ env set, points at card-kholo-api.onrender.com).
  Render https://card-kholo-api.onrender.com live (Blueprint, env from gitignored deploy/render.env).
- Production: check_integrations 12/12 PASS (Telegram webhook set by app, CORS for Vercel origin);
  e2e API run PASS (real card 4 functions in 5 s, ICS, APK + audio, bit.ly, events, status, pairing).
  Flagsmith env webhook created (id 5481) -> /hooks/flagsmith.
- Left: simulate_incident + NudgeBee approval (needs user OK), two-phone Telegram test, cron-job.org keep-warm.
