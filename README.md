# Card Kholo

Card Kholo helps families check wedding invitations that arrive over chat. A guest can scan a file or a pasted message, see why it was flagged, and alert a paired family member. A wedding host can dictate a personal invite and share a link that guests can check against the saved invitation.

## How the backend works

| Service | Role |
|---|---|
| Sarvam | Document AI and a vision fallback extract functions from eligible cards after an OK scan. Bulbul voices warnings and invitations. Saaras transcribes the host's note, and sarvam-105b selects the invited functions and writes the message. |
| Flagsmith | Identity flags select scanning rules, strict mode and host features. The dashboard controls rule packs, canary rollouts and kill switches. |
| NudgeBee | Three distinct false alarms for one pack within five minutes open an incident. The backend sends it to a workflow where a human can approve rollback. After the callback, the backend refreshes flags and queues notices for paired children. |

The scanner determines verdicts from file markers, links, enabled signatures and saved invite records. It can return an OK, SUSPICIOUS or DANGEROUS verdict with provider credentials unset.

## Run locally

From the repository root, use PowerShell and Python 3.12. The demo cache lets you try the sample PDF immediately.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:DEMO_CACHE="on"
.\.venv\Scripts\python -m uvicorn app.main:app --reload --env-file .env
```

With this workspace's environment already installed, run just the last two lines. In Swagger UI, execute `POST /api/identify` and copy the returned UUID into `POST /api/scan`. With local defaults, a child scanning `{"user_id":"<UUID>","text":"https://bit.ly/invite"}` gets `SUSPICIOUS`. A parent gets `DANGEROUS` through strict mode. A plain message such as `Dinner at six` gives `OK`. [Swagger UI](http://127.0.0.1:8000/docs)

The demo APK is harmless. It is a ZIP containing a plain-text note named `AndroidManifest.xml` and an empty `classes.dex`. Upload `demo/Shaadi_Card_Priya.pdf.apk` with the same user ID to see the scanner detect the archive markers and filename. [Demo fixtures](demo/README.md)

For Docker, run `docker build -t card-kholo .` followed by `docker run --rm -p 8000:8000 -v card-kholo-data:/data card-kholo`. Reuse the named volume on the next start to keep users, pairing codes and scans. Outside Docker, `CARD_KHOLO_DB` can select a database file in an existing directory.

Use one Uvicorn worker so scan calendars and recent alerts remain available across requests. To run all offline tests, execute `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` from the repository root.

## Environment variables

Copy `.env.example` to `.env` in the repository root and fill it in. Locally, start Uvicorn with `--env-file .env`; on Render, set the same names in the dashboard. Startup stops with a clear error without `SARVAM_API_KEY` or `FLAGSMITH_ENV_KEY`, and prints one warning per optional service (Telegram, NudgeBee, Flagsmith Admin API) that is not configured. The frontend reads `VITE_API_BASE_URL`, `VITE_USE_MOCKS` and `VITE_TELEGRAM_BOT_USERNAME` from `CardKholo/.env.local`. [Environment template](.env.example)

| Variables | Purpose |
|---|---|
| `APP_BASE_URL`, `ALLOWED_ORIGINS` | Public backend URL for invites and callbacks (default `http://127.0.0.1:8000`), and comma-separated frontend origins (default `*`). Use public HTTPS for Telegram. |
| `CARD_KHOLO_DB`, `DEMO_CACHE` | SQLite file path and sample-card cache switch. Defaults are `card_kholo.sqlite3` at the project root and cache off. |
| `SARVAM_API_KEY` | Enables live card extraction, voice invites and speech synthesis. |
| `BULBUL_SPEAKER_HI`, `BULBUL_SPEAKER_KN`, `BULBUL_SPEAKER_EN` | Optional Bulbul voices. The default speaker is `shubh`. |
| `FLAGSMITH_ENV_KEY` | SDK environment key for evaluating identities and fetching remote rules. |
| `FLAGSMITH_FEATURE_IDS`, `FLAGSMITH_SEGMENT_IDS` | JSON maps of pack names and segment names to their numeric IDs. The rollback uses the pack's feature ID and the `canary_20` segment ID. |
| `FLAGSMITH_PROJECT_ID` | Optional project identifier. The current rollback endpoints use the environment, feature and segment identifiers. |
| `FLAGSMITH_ADMIN_API_KEY`, `FLAGSMITH_ADMIN_ENV_KEY` | Admin credentials for the backend fallback rollback. |
| `NUDGEBEE_WEBHOOK_URL`, `HOOK_SECRET` | Incoming NudgeBee workflow URL and shared secret for the rollback routes and Flagsmith webhook. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_SECRET` | Bot API access, pairing-link username and incoming webhook authentication. |

## Test identity and flags

In Swagger UI, execute `POST /api/identify` with `{"name":"Asha","lang":"hi","role":"parent"}`. Expect a UUID and a Telegram URL ending in a unique start code. Repeat with `"role":"child"` or `"role":"host"` to get a new UUID and a null link. Set `TELEGRAM_BOT_USERNAME` to your bot's username before sharing live pairing links.

With `FLAGSMITH_ENV_KEY` set before startup, check the returned UUID in the Flagsmith dashboard for the language, role and beta traits. Add `"beta":true` to the identify request to enter the canary deterministically. Omitting it sends the trait string `"false"`. Without a key, the API uses local defaults.

## Test the card reader

Set `$env:DEMO_CACHE="on"` before starting Uvicorn. With local flags, identify a user and upload `demo/sample-invite.pdf` to `POST /api/scan`. Functions are sorted by date and time, with untimed functions last on their day. Open the Sangeet's `maps_url` for directions and its `gcal_url` for Google Calendar. Download `ics_url` within ten minutes. Both the timed Sangeet and the all-day wedding have a one-hour display reminder.

For live extraction, set `SARVAM_API_KEY` and `DEMO_CACHE=off` before startup. The backend sends eligible PDF, JPEG and PNG files to Sarvam after an `OK` verdict. If extraction and vision both fail, the response keeps its verdict and includes the manual-entry reason. With the demo cache enabled, `demo/cache.json` supplies curated fixtures at startup. Other successful reads are cached in memory for ten minutes. Multipart requests are limited to 20 MiB including form overhead, JSON scans to 256 KiB. Oversized requests return HTTP 413.

## Test voice warnings

Set `SARVAM_API_KEY` in the environment before starting Uvicorn. The default Bulbul v3 speaker is `shubh`. You can override it per language with `BULBUL_SPEAKER_HI`, `BULBUL_SPEAKER_KN` and `BULBUL_SPEAKER_EN`.

In Swagger UI, identify a user, scan `demo/Shaadi_Card_Priya.pdf.apk`, then submit the returned scan ID to `POST /api/opened`. With `spoken_summary` enabled and Bulbul available, both responses include base64 WAV audio. To listen in PowerShell, copy an `audio_b64` value without the JSON quotes, run `[IO.File]::WriteAllBytes("$env:TEMP\card-kholo.wav", [Convert]::FromBase64String((Get-Clipboard).Trim()))`, then open the WAV file.

Without a key or when speech is disabled, expect `audio_b64: null`. The scan verdict and five localized steps still work. The complaint draft uses the scan date in India and includes the filename for uploads. Hindi and Kannada audio use native-script scripts. Startup prepares six clips and retries missing ones in the background twice.

## Test host voice invites

Open `/i/demo` on the running server to preview the guest page without credentials. For the complete flow, set `SARVAM_API_KEY` and `DEMO_CACHE=on` before starting Uvicorn.

1. In `/docs`, call `POST /api/identify` with `{"name":"Anu","lang":"en","role":"host"}`. With local defaults, this identity has `host_invites` enabled.
2. Scan `demo/sample-invite.pdf` with the host ID. Copy the returned `functions` into `POST /api/invites/wedding` with the same `user_id`, `"couple":"Priya and Arjun"` and `"host_family":"Gupta"`. Expect a wedding ID.
3. In `POST /api/invites/voice`, submit the same host ID and an audio recording up to 30 seconds, such as “Invite Riya to the Sangeet in English.” The voice route uses that host's most recently saved wedding. Open the returned `invite_url` to check the event, Directions, Calendar and optional guest audio. The `wa_url` opens a prefilled WhatsApp message.
4. Paste the returned invite URL or full invitation text into `POST /api/scan`. With default rules, expect `OK`, `verified_from: "Gupta"` and the reason “Verified invite from the Gupta family”. Download the guest page's calendar to check that it contains only the guest's functions and a one-hour reminder for each.

## Test Telegram pairing and feedback

Set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_SECRET` and a public HTTPS `APP_BASE_URL` before starting Uvicorn. Startup registers `/hooks/telegram`. Telegram allows letters, digits, underscores and hyphens in its webhook secret. [Bot API webhook documentation](https://core.telegram.org/bots/api#setwebhook)

1. Use `POST /api/identify` in Swagger UI to create a parent. Poll `GET /api/pairing/{user_id}` every four seconds while displaying the QR code. New parents and unknown IDs return `{"linked":false,"child_name":null}`. Open the returned `pair_link` in the child's private Telegram chat and press **Start**. After the “Linked!” reply, the next poll returns `linked: true` and the child's stored name.
2. Use that parent's UUID in a multipart `POST /api/scan` with `demo/Shaadi_Card_Priya.pdf.apk`. Expect `DANGEROUS`, `alert_sent: true` once Telegram accepts the message, and a family alert with one button. Telegram failures leave `alert_sent: false`; the verdict is still returned.
3. Tap **This was a real invite**, then post `{"scan_id":"<same scan ID>","real_invite":true}` to `/api/feedback`. With the default packs and a fresh database, expect `pack_false_alarms` to contain `pack_wedding_2026: 1`. The button and HTTP route count a given scan once per pack. Check `GET /api/status` for the latest accepted family alerts, up to 20.

To check this phase offline, run `.\.venv\Scripts\python.exe -m unittest tests.test_telegram`. The tests simulate Telegram registration, pairing, message acceptance, feedback and timeouts.

## How we use Flagsmith

- Each identity carries its language, role and a string-valued beta trait.
- The `parents` segment enables strict scanning, `hosts` targets the host invite flag, and `canary_20` targets early rule-pack recipients.
- Edit the `scam_signatures` JSON in the dashboard. Once the webhook arrives, the next scan fetches the updated rules.
- Each pack has a kill switch evaluated for the scanning identity.
- New packs can default OFF and turn ON for `canary_20`, a 20% identifier split or an exact `beta = "true"` match.
- After human approval, NudgeBee uses the Admin API to remove the canary override and disable the environment default.
- The authenticated Flagsmith webhook records changes in SQLite. Status shows the latest 15, newest first.

## Reproduce a canary incident

Run the offline suite from the repository root with `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. For a live demo, use the Flagsmith test environment with the broad filename signature, the canary override ON and the environment default OFF.

1. Set `FLAGSMITH_ENV_KEY`, `FLAGSMITH_FEATURE_IDS` (e.g. `{"pack_broad_test":123456}`), `FLAGSMITH_SEGMENT_IDS` (e.g. `{"canary_20":98765}`), `FLAGSMITH_PROJECT_ID`, `NUDGEBEE_WEBHOOK_URL`, public `APP_BASE_URL` and `HOOK_SECRET`. Substitute your actual IDs. Register `{APP_BASE_URL}/hooks/flagsmith?token={HOOK_SECRET}` in Flagsmith.
2. In Swagger UI, identify a child with `"beta":true`. Upload `demo/sample-invite.pdf` three times as that user and confirm each scan's `pack_hits` includes `pack_broad_test`. Within five minutes post `{"scan_id":"<id>","real_invite":true}` to `/api/feedback` once for each distinct ID. Status should show one open incident. Its pack listing shows the environment default, so the pack can read OFF during the canary.
3. Configure NudgeBee to deduplicate by `incident_id`. After approval, use the payload's feature and segment IDs with the Flagsmith Admin API. On the environment feature resource (`/api/__future__/environments/{admin_env_key}/features/{feature_id}/`), first DELETE `segment-overrides/{segment_id}/` (404 counts as already removed), then PATCH the feature with `{"environment_default":{"enabled":false}}`. Both requests use `Authorization: Api-Key <admin key>`. After success, POST to `app_callback` with `X-Hook-Secret` and `{"incident_id":"<id>","pack":"<pack>","approver":"<reviewer>"}`.
4. Refresh `GET /api/status` and repeat the scan with the same beta identity. Expect a closed `rolled_back` incident and no broad-pack hit. The `flag_changes` feed labels a change “NudgeBee rollback” when that feature has an open incident or one rolled back in the last two minutes, or when `changed_by` contains “NudgeBee” (name the Admin API key NudgeBee uses “NudgeBee”). Other changes are labelled “Dashboard or API”.
5. To exercise the backup on an open incident, set `FLAGSMITH_ADMIN_API_KEY` and `FLAGSMITH_ADMIN_ENV_KEY` before startup and call `POST /api/admin/fallback-rollback/{incident_id}` with `X-Hook-Secret`. It performs the same DELETE then PATCH, each attempted even if the other fails. Any upstream failure returns 502 and keeps the incident open for retry. A confirmed rollback clears cached flags and queues notifications for affected paired children.

## Frontend

```powershell
cd CardKholo; npm ci; npm run dev
```

`CardKholo/.env.local` needs `VITE_API_BASE_URL=http://127.0.0.1:8000`, `VITE_USE_MOCKS=false` and `VITE_TELEGRAM_BOT_USERNAME`. With no API URL, the app runs on mocks. `/status` is the projector control room.

## Integration checks and incident script

- `.\.venv\Scripts\python scripts\check_integrations.py [--base-url https://<render-app>] [--nudgebee]` prints PASS / FAIL per integration (Sarvam TTS, Flagsmith identities and `scam_signatures`, Admin API IDs and the canary override, Telegram webhook, backend health and CORS, and optionally a NudgeBee test run that you must reject). It prints the correct `FLAGSMITH_FEATURE_IDS` / `FLAGSMITH_SEGMENT_IDS` JSON and never prints a secret.
- `.\.venv\Scripts\python scripts\simulate_incident.py https://<render-app>` identifies a beta parent, uploads three generated one-page PDFs named `invitation_card_1.pdf` to `_3.pdf`, marks each as a real invite and prints packs and incidents. It talks only to the backend.

## Warning-style experiment

`warning_style` (multivariate `calm` / `urgent`) is evaluated per identity and returned on every non-OK scan. The frontend posts `warning_shown`, `warning_played`, `warning_completed` and `opened_anyway` to `POST /api/events`, stored once per scan and event with that scan's style. `GET /api/status` returns `completion_rate = completed / shown` per variant.

## Deploy

- **Render (backend):** Web Service from this repo, runtime Python (or Docker), build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check path `/health`. Set every backend env name; `APP_BASE_URL` is the Render URL and `ALLOWED_ORIGINS` the exact Vercel URL. Free instances sleep after 15 minutes and may lose SQLite data; ping `/health` every 10 minutes (GET or HEAD).
- **Vercel (frontend):** root directory `CardKholo`, framework Vite, build `npm run build`, output `dist`. Set `VITE_API_BASE_URL` (Render URL, no trailing slash), `VITE_USE_MOCKS=false`, `VITE_TELEGRAM_BOT_USERNAME`, then redeploy after any `VITE_` change.
- After deploying, register `{APP_BASE_URL}/hooks/flagsmith?token={HOOK_SECRET}` as a Flagsmith environment webhook and run the integration check against the Render URL.

## Reset between demo runs

1. In Flagsmith, set `pack_broad_test` back to environment default OFF with the `canary_20` override ON, and remove any demo `domain` rule from `scam_signatures`.
2. Reject or close any leftover NudgeBee runs.
3. Wait 5 minutes after the last "This was a real invite" tap so old false alarms leave the window.
4. On each phone, clear the site data (or open `/start` again) so a fresh user and pair code are created; the child taps Start on the new QR.
5. Open `{APP_BASE_URL}/health` a minute before going on stage so Render is awake.

## Privacy

- The backend processes uploaded files, pasted scan text and host recordings in memory. A scan row keeps the user ID, time, verdict, matching packs and, for files, the filename and SHA-256 hash. Extracted scan calendars expire after ten minutes.
- With live integrations enabled, Sarvam receives eligible cards and voice notes for processing. Flagsmith receives the identity UUID and its language, role and beta traits. Telegram receives pairing replies and family alerts. NudgeBee receives incident and rule-pack details.
- SQLite keeps user and pairing records, including the linked Telegram chat ID and child name. It also keeps saved weddings, guest names, selected functions, invite text and optional generated narration. Anyone with a guest link can open that invitation. The dictated contact number is used for the WhatsApp share link, and the voice note and transcript are not saved in the invite row.
- Feedback, incidents, flag-change summaries and warning-experiment events (scan ID, event, style) persist in SQLite. The Flagsmith webhook logs only the event type and feature name.
- Uploaded files are never written to disk; only their SHA-256 and the outcome are stored.

## AI assistance

The project used AI coding assistants: OpenAI Codex implemented the backend, tests and first documentation, another assistant built the frontend, and Claude Code (Anthropic) integrated both sides, added the warning-style experiment and the integration scripts, and reviewed the code for the demo. The offline suite exercises provider integrations with simulated responses. The live walkthroughs above use your configured provider accounts.
