# Festive Hacks submission answers (copy-paste)

## Demo video
<YouTube unlisted link to demo/video/CardKholo_demo.mp4 (under 2 min). Upload it, set Visibility = Unlisted, paste the link.>

## Live demo or deployment
https://card-kholo.vercel.app

## What did you build and how does it work?
Card Kholo is "the safe way to open, and send, a wedding card", built for Indian families in wedding season.

The festive problem: in wedding season, families forward hundreds of invites on WhatsApp, and scammers have started sending fake wedding cards as Android apps with names like "Shaadi_Card_Priya.pdf.apk". One tap installs an app that reads SMS and bank OTPs, and the people most likely to tap are our parents. Scams also count on families not talking to each other.

How it works (live at card-kholo.vercel.app, FastAPI backend on Render):
1. Setup in two questions: language for warnings and voice (Hindi, Kannada, English) and role (parent, son/daughter, or host). The parent shows a QR code; the son or daughter scans it and taps Start in our Telegram bot (@cardkholo_alert_bot), and the two are linked.
2. When a card arrives, the parent uploads it exactly as received (photo, PDF, any file) or pastes the message/link.
3. The verdict (SAFE / CHECK / STOP) comes only from deterministic rules plus Flagsmith rule packs, never from AI: Android archives (a zip containing AndroidManifest.xml and classes.dex), .apk/.xapk/.apks/.apkm and double extensions, file headers that don't match the claimed type (PDF/JPG/PNG magic bytes), URL shorteners, plain HTTP, IP-address hosts and punycode domains, plus the JSON scam signatures from Flagsmith. Parents get strict mode, which turns any suspicious result into a full stop.
4. Real card: Sarvam Document AI and a Sarvam vision model read the card in parallel and the first good answer wins (about 5-10 s). Every function (Mehendi, Sangeet, Phere, Reception) comes out with date, time and venue, with Google Calendar links, one ICS download with a reminder an hour before each, a calendar view with a "leave around" time and a directions screen (Google Maps, car/bike/metro, WhatsApp share).
5. Fake card: a full-screen STOP, a spoken warning in the parent's language (Sarvam Bulbul), and at the same moment a Telegram alert to the linked son or daughter. "I already opened it" shows the first-hour steps: call 1930, airplane mode, call the bank to block cards and UPI, report on cybercrime.gov.in with a ready complaint draft.
6. Hosts can send invites the safe way: they speak "invite Riya to the Sangeet, in Hindi"; Sarvam Saaras transcribes, sarvam-105b writes a personal invite, and the guest gets a verified link instead of a file. Scanning that link returns "Verified invite from the <family> family".
7. Safety loop: if a rule pack flags real invites ("This was a real invite" in the app or on Telegram), 3 false alarms in 5 minutes open an incident that goes to a NudgeBee workflow. A human approves, NudgeBee rolls the pack back in Flagsmith, and calls our backend to close the incident. A projector control room (/status) shows packs, incidents, the live Flagsmith change feed, family alerts and an A/B experiment on the warning itself.

Privacy: uploaded files are processed in memory and never stored, only their SHA-256 and the verdict. The demo APK is harmless (a text file named AndroidManifest.xml and an empty classes.dex).
Stack: React + Vite + TypeScript + Tailwind on Vercel, FastAPI + SQLite on Render, Telegram Bot API.

## How have you used Flagsmith and what problem does it solve?
Flagsmith is the live brain of our scam rules, so we can react to new scams in seconds without shipping an app update.
- Every rule pack (pack_core, pack_wedding_2026, pack_broad_test) is a feature flag, and `scam_signatures` is a JSON remote-config list of rules (filename_regex, text_regex, domain). The backend evaluates flags remotely per identity with the Python SDK, cached for 5 s at most, using the traits lang, role and beta (strings). Only packs that are ON for that identity apply, and every scan returns which packs fired.
- Segments: `parents` (role = parent) gets `strict_mode` (suspicious becomes STOP); `hosts` (role = host) gets `host_invites`.
- Canary rollouts: risky new packs ship with the environment default OFF and a `canary_20` segment override ON, where canary_20 = 20% identifier split OR beta = "true", in one rule. That lets us test a broad pack on a slice of users first.
- Live rules: when a new scam site appears we add one `domain` rule to `scam_signatures` in the dashboard and every phone blocks it within seconds.
- A multivariate flag `warning_style` (calm / urgent, 50/50) runs an A/B test on the STOP warning itself; the app records shown / played / completed / opened-anyway events and the control room shows the completion rate per variant.
- An environment webhook streams every flag change to our backend, which refreshes the flag cache and shows a live "flag changes" feed on the control room, labelled "NudgeBee rollback" or "Dashboard or API".
- The Flagsmith Admin API is what NudgeBee calls to roll a pack back (delete the canary override, switch the pack off), and our protected Plan B route can do the same if NudgeBee is down.

## How have you used Nudgebee and what problem does it solve?
NudgeBee gives our rule system a human-approved, auditable rollback loop, so a bad rule can't keep scaring families.
- Families can say "This was a real invite" on a STOP result, in the app or with a button on the Telegram alert. Each one adds a false alarm for every pack that fired on that scan.
- When one pack gets 3 false alarms within 5 minutes (and has no open incident), the backend saves an incident and POSTs it to our NudgeBee workflow webhook with type, pack, false_alarms, window_minutes, flagsmith_feature_id, flagsmith_segment_id, rollout, incident_id, app_callback and summary.
- The NudgeBee automation "Card Kholo pack rollback" runs a core.approval task (approve / reject). On approve, three HTTP tasks run: DELETE the canary_20 segment override on that feature via the Flagsmith Admin API, PATCH the feature's environment default to OFF, then POST back to our /hooks/rolled-back with a shared secret header.
- Our backend marks the incident rolled back, clears the flag cache and notifies linked children on Telegram; the control room shows the incident closed and both Flagsmith changes labelled "NudgeBee rollback". We tested this end to end on production.
- The backend never changes Flagsmith itself while NudgeBee is configured; a secret-protected fallback route exists only as Plan B.

## How have you used Sarvam and what problem does it solve?
Sarvam is everything a family reads and hears, in their own language.
- Document AI (doc_ai.extract with a JSON schema, polling the job) reads a wedding card into structured functions: name, original-language name, date, time, venue, address, city. A vision model (chat completions with the card as an image; PDFs rendered to an image first) runs in parallel and the first good answer wins, so a card is read in about 5-10 seconds. AI only reads: it never decides a card is safe.
- Bulbul (bulbul:v3) speaks the STOP warning and the first-hour steps in Hindi, Kannada and English. Clips are generated at startup and cached, so the warning plays instantly. Elderly parents who don't read small text still hear what to do. Our demo video's narration is also Bulbul.
- Saaras (speech to text, codemix mode) transcribes a host's spoken note, including Hinglish.
- sarvam-105b parses which guest, language and functions the host meant, and writes a warm personal invitation in the guest's language, with a verified link.

## What did you like about Flagsmith, and what would you improve?
Liked: segments with traits made per-identity behaviour trivial (strict mode for parents, canary for beta users), JSON remote config let us ship rule changes with no deploy, the environment webhook made a real-time change feed easy, and the Admin API made automated rollback possible.
Improve: with feature versioning v2, writing segment overrides through the API is not obvious, and the simpler `__future__` endpoints are marked experimental. In the multivariate editor it is easy to type the weight into the variation value field (we did). The webhook payload under v2 made it hard to build a human summary like "override removed" vs "turned off".

## What did you like about Nudgebee, and what would you improve?
Liked: the webhook trigger exposing the body as Inputs.webhook_json, the built-in approval task, and the clear per-task execution view with input/output made a human-in-the-loop rollback quick to build.
Improve: numbers from the webhook JSON render in exponent form inside templates (our 7-digit segment ID 1203642 became 1.203642e+06 in a URL, which caused a 404 until we sent IDs as strings). An integer formatting filter or a warning would help, and so would a "test run with sample payload" button and a non-HTML error summary for failed HTTP tasks.

## What did you like about Sarvam, and what would you improve?
Liked: Bulbul voices sound natural in Hindi and Kannada, Document AI with a JSON schema returns clean structured data from real Indian wedding cards, and Saaras handles code-mixed speech well.
Improve: Document AI took about 20-23 s per card in our tests, so we had to race it against the vision model to fit a mobile timeout; a faster mode would help. The Python SDK's doc_ai.extract has no language parameter (we passed it as an extra body field), and clearer docs on TTS text limits and timeouts would help.

## Social post links
<Your LinkedIn / X post URL. Tag Flagsmith, NudgeBee, Sarvam AI and WeMakeDevs.>
