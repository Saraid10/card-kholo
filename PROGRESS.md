# Card Kholo progress

## Current phase
9 complete. All planned backend phases and the UI contract additions are implemented.

## Done
- 1 — Mock contract, upload formats, media and CORS in `app/main.py`, `app/models.py`, `app/examples.py` and `app/config.py`. Setup in `.env.example`, `requirements.txt`, `Dockerfile` and `README.md`.
- 2 — SQLite schema and identities in `app/db.py` and `app/main.py`; remote flags, cache and local signatures in `app/flags.py`; checks in `tests/test_phase2.py`.
- 3 — R1–R6, strict mode and scan persistence in `app/scan_rules.py`, `app/main.py`, `app/flags.py` and `app/db.py`. Harmless fixture in `demo/`; rule checks in `tests/test_scan_rules.py`.
- 4 — Document AI and vision in `app/sarvam_client.py` and `app/card_schema.json`; scan integration and ICS in `app/main.py` and `app/calendar_links.py`; demo card/cache in `demo/`, checks in `tests/test_card_reader.py`.
- 5 — Cached Bulbul warnings and first-hour audio, localized guidance and complaint drafts in `app/voice.py`, `app/sarvam_client.py`, `app/db.py`, `app/main.py` and `app/config.py`; checks in `tests/test_voice.py`. Three-agent review recorded in `AUDIT.md`.
- 6 — Telegram registration, private pairing, alerts, last 20 deliveries and shared feedback in `app/alerts.py`, `app/db.py`, `app/main.py` and `app/incidents.py`; offline checks in `tests/test_telegram.py`.
- 7 — Incident threshold, NudgeBee delivery, protected rollbacks, child notifications and live status in `app/incidents.py`, `app/flags.py`, `app/alerts.py`, `app/db.py` and `app/main.py`. Verified in `tests/test_incidents.py`; demo steps in `README.md`.
- 7b adds optional beta identities, migrates existing rows, includes canary metadata in incidents, and removes the segment override before disabling the environment default. The authenticated Flagsmith webhook refreshes cached rules and persists the status feed. Coverage in `tests/test_canary.py` and `tests/test_incidents.py`.
- The shared API serves pairing status with one indexed lookup. Scans order functions by date and time with untimed entries last on their day. Scan and mock invite links open directions. Each ICS event has a one-hour display reminder.
- 8 — Host weddings, voice invites and optional narration in `app/invites.py`, `app/sarvam_client.py`, `app/db.py` and `app/main.py`. The guest page in `app/guest_page.py` includes event directions, Google Calendar and guest-specific ICS. R7 in `app/scan_rules.py` verifies links to saved invitations.
- 9 — `README.md` covers the problem, sponsor integrations, four-command setup, environment variables, incident demo, privacy, harmless APK fixture and AI assistance.

## Next
- Run the documented live demos with provider credentials and a public HTTPS callback URL.
- The warning_style A/B test, event tracking and experiment status require “do the experiment”.

## Decisions
- The existing repository is the project root. Swagger UI serves as the phase 1 test page.
- The parent pairing link uses a demo bot name until configured.
- SQLite uses `card_kholo.sqlite3` in the project root. Each identify call creates a fresh UUID.
- The installed SDK sends Document AI language via an extra multipart field. The fictional sample card has a seeded demo cache entry. Only usable event results are cached.
- The warning asks the user to call family because phase 5 cannot confirm delivery or identify every danger as an installed app. Kannada audio uses the requested English placeholder.
- The audit added streaming caps of 20 MiB per multipart request and 256 KiB per JSON scan. Live extracts stay in memory for ten minutes. Docker uses a named SQLite volume.
- The first private chat claims a pairing code. Feedback is shared and deduplicated per scan/pack. Public alert history omits personal details. Telegram text describes the actual input.
- External notifications retry from a SQLite queue, keyed by incident for NudgeBee. A failed fallback leaves the incident open. Both successful rollback paths clear cached flags.
- The voice route uses the host's most recently saved wedding because its contract takes only user ID and audio. A writing failure uses a localized template and a speech failure leaves audio null. The demo page remains a labelled preview.

## Known issues
- All 50 tests passed locally and inside the Linux Docker image. HTTP checks covered both demo scans, ICS reminders, guest preview, QR and SQLite persistence after container replacement. The guest page fit 320, 390 and 480 px viewports.
- Live Sarvam, Flagsmith, Telegram and NudgeBee checks remain pending because provider credentials were unavailable.

## Last reviewed commit

