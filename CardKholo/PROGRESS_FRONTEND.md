# Card Kholo frontend progress

## Current phase
Add-on parts 1–6 done.

## Done
- Base app: all screens, muted stationery design (see DESIGN.md, README.md).
- Add-on 1: localStorage keys (all reads/writes wrapped in try/catch via `src/lib/storage.ts`), helpers in `src/state/scans.ts`:
  - `cardkholo_wedding` `{scan_id, functions[], ics_url, saved_at, couple}`: saved by "Add all to calendar" / "See my functions"
    on the OK result (then go to `/calendar`), and also on a venue tap (so `/directions/:index` reads the right wedding).
  - `cardkholo_recent` `{scan_id, label (≤40 chars), verdict, time}`: after every scan, last 5. Replaces the old `cardkholo_history`.
  - `cardkholo_child` `{child_name}`: helpers ready (`getChild`, `saveChild`); written by pairing in part 4.
- Add-on 2: `/calendar` (`src/pages/Calendar.tsx`): empty state, sort by date then time (no time = last, "Time not printed"),
  7-day strip from the day before the first function with dots, tap a day to scroll to and highlight its function, "Next up" card
  (relative day, time, names, venue, map preview, "Leave around" = start − 45 min, Directions), list with directions icons,
  "Remind me an hour before each" link to `ics_url` (hidden when missing).
- Add-on 3: `/directions/:index` (`src/pages/Directions.tsx`): Google Maps embed, no API key (`src/components/MapEmbed.tsx`,
  6 s fallback placeholder), floating back button, bottom sheet with Starts / Leave around / Date tiles,
  Car / Bike / Metro → driving / two-wheeler / transit, "Start in Google Maps" (new tab) and WhatsApp Share.
- Add-on 4: optional `GET /api/pairing/{user_id}` → `{linked, child_name}` (`api.pairing`, type `PairingRes`). Mock: not linked for
  15 s after identify, then `{linked: true, child_name: "Rohan"}` (identify time in `cardkholo_mock_identified_at`).
  `/link` polls every 4 s: "Waiting for them" (gold dot) → "{child_name} is linked" (sage dot), saves `cardkholo_child`, stops.
  On 404/error it stops quietly and keeps the waiting text. `/check` shows the "{child_name} is linked" chip (header on tablet+,
  first line of the screen on phones where the header has no room); STOP says "{child_name} told on Telegram" when `alert_sent`.
- Add-on 5: "Checked today" on `/check` lists today's `cardkholo_recent` entries (label, time, verdict word in its colour).
  Rows reopen results kept in memory (`getMemoryScan`); after a reload the row stays but a tap does nothing.
- Add-on 6: mock OK scan has the 4 spec functions (Phere at Shagun Gardens with no address, Reception "स्वागत समारोह");
  mock APK scan returns the 3 spec reasons.
- Routes: `/calendar`, `/directions/:index`, `/scan` → `/check` alias, old `/functions/:scanId` → `/calendar`.
  Old `/directions/:scanId/:idx` and `src/pages/Functions.tsx` removed.

## Decisions
- Map filter is `saturate(0.6) sepia(0.12)` to match the light paper theme. The spec's dark-theme filter
  (`invert(90%) hue-rotate(180deg) saturate(0.6)`) is one line in `MapEmbed.tsx` (`MAP_FILTER`) if wanted.
- Mock OK scan's `ics_url` is now a `data:text/calendar` URL so the reminder link works offline; `resolveUrl` passes `data:`/`blob:` through.
- "Linked" dot uses the sage `safe` token instead of lime, to match the muted palette.
- The 3 fixed DANGEROUS reasons apply to the `.apk` mock only; the broad-pack and install-text mocks keep their own reasons,
  since "File ends in .apk" would be wrong for a PDF.
- `user.linked_name` is no longer used; the child name comes from `cardkholo_child`.
- Directions index = position in the saved `functions[]` (as stored), not the sorted order.

## Next
- Connect to the real backend (`VITE_API_BASE_URL`), confirm `/api/pairing/{user_id}` exists or leave it optional.

## Known issues
- No endpoint to update a user's language after `/api/identify`.
- `GET /api/invites/:id` is not in the contract (falls back to demo data).
