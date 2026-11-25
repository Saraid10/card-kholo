# Demo checklist

`API` = `https://<service>.onrender.com`, `WEB` = `https://<project>.vercel.app`.

## Before going on stage (15 min before)
1. Wake the backend: open `API/health` → `{"ok":true}`. Then `check_integrations.py --base-url API` (all PASS).
2. Flagsmith (Development): `pack_core`, `pack_wedding_2026`, `spoken_summary` ON; `pack_broad_test` OFF with the
   `canary_20` override ON; `warning_style` = calm / urgent 50%; no leftover demo `domain` rule in `scam_signatures`.
3. Parent phone: open `WEB/start`, name + Hindi + Parent > QR screen. Child phone: scan the QR, tap **Start**
   in Telegram, wait for "Linked!". The parent screen shows "<name> is linked".
4. Projector: `WEB/status` (fullscreen).
5. On the parent phone (WhatsApp "saved messages" or Files): `Priya_Arjun_Wedding_Card.pdf`,
   `Shaadi_Card_Priya.pdf.apk` (harmless test file), and `demo/invitation_card_1..3.pdf` on the laptop.

## Demo order (one sentence each)
1. **Real card** - upload `Priya_Arjun_Wedding_Card.pdf`: "A real card: Sarvam reads every function, and Mummy gets
   them on her calendar." Tap **Add all to calendar** > `/calendar` > Directions on the next function.
2. **Fake card** - upload `Shaadi_Card_Priya.pdf.apk`: "This one is an app pretending to be a card; it stops her,
   speaks the warning in Hindi, and her son's phone buzzes on Telegram right now." Show the child phone.
3. **I already opened it** - "If she already tapped it, she gets the first-hour steps: airplane mode, 1930, the bank."
4. **Live rule** - in Flagsmith add a `domain` rule (e.g. `{"id":"live-01","pack":"pack_core","type":"domain",
   "pattern":"shaadi-card.in","severity":"DANGEROUS","label":"Known scam site"}`) to `scam_signatures`, save; paste
   `Your card: https://shaadi-card.in/priya` in the app: "A new scam site was reported; one flag change in
   Flagsmith and every phone blocks it within seconds, no app update." The `/status` feed lights up.
5. **Canary** - "New risky rules ship to 20% first, via a Flagsmith segment." (`WEB/start?beta=1` user gets `pack_broad_test`.)
6. **Incident** - run `.\.venv\Scripts\python scripts\simulate_incident.py API`: "The canary rule flagged three real
   invites; NudgeBee opens an incident and asks a human." Approve in NudgeBee: "On approval NudgeBee removes the canary
   and turns the pack off in Flagsmith." `/status` shows **Rolled back** and "NudgeBee rollback" in the feed.
7. **Experiment** - point at the warning_style panel: "We A/B test the warning itself: calm vs urgent, measured by
   who listens to the end."

## Reset between runs
1. Flagsmith: re-add the `canary_20` override ON on `pack_broad_test` (environment default stays OFF);
   remove the live `domain` rule.
2. Reject or finish any open NudgeBee run. Wait 5 minutes after the last "real invite" feedback.
3. Phones: reopen `WEB/start` for a fresh user (re-link the child if the backend restarted).

## Plan B (NudgeBee down) - roll back from our side
```powershell
curl.exe -X POST "API/api/admin/fallback-rollback/<incident_id>" -H "X-Hook-Secret: <HOOK_SECRET>"
```
`<incident_id>` is on `/status` (Incidents) or from `API/api/status`. It removes the canary override (404 = already
gone) and turns `pack_broad_test` off, then marks the incident rolled back.
