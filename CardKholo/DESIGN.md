# Card Kholo: frontend brainstorm and design brief

Sources: `Card Kholo team spec and roadmap.pdf` (product + API contract), `Card Kholo UI designs.html`
(13 boards: landing, control room, 11 mobile screens), and five visual references (Kin onboarding,
Recto editorial site, maroon/gold wedding stationery, device-tier mockups).

## 1. What the product has to do (from the spec)

| Story | Screen(s) |
|---|---|
| Guest uploads an invite, gets every function as a calendar entry + Maps | Check a card → SAFE result → Your functions → Directions |
| Parent uploads a fake card, hears a warning in their language, sees a big red screen | STOP result (auto-plays voice) |
| Child gets a Telegram alert when that happens | Link family (QR / WhatsApp / copy link) |
| Parent already tapped it: first-hour steps, spoken | First hour |
| Child marks "this was a real invite" (false alarm) | STOP / CHECK result feedback button |
| Operator sees packs, false alarms, rollback | Control room (projector) |
| Stretch / roadmap: host speaks an invite, guests get a verified link | Host setup → Speak invite → Preview & send → Verified invite page |

Golden rule carried into the UI: **rules decide, AI only reads and explains.** The UI never says
"AI thinks this is safe". SAFE screens say what was checked.

## 2. Design direction: "wedding stationery that protects you"

The supplied HTML is dark + neon lime. The references point somewhere warmer and more editorial, which
fits the audience (parents 55–70, tier 2/3 towns) and the object (a wedding card) much better:

- **Kin**: warm paper background, big serif headline with one coloured word, small pill CTA.
- **Recto**: editorial serif, one *italic* accent word in red, hairline rules, breadcrumb line.
- **Stationery**: deep maroon and wine, gold foil, blush/terracotta, ornamental frames.
- **Device tiers**: Mobile = primary experience, Tablet = comfortable adaptation, Desktop = demo and
  operator experience.

We keep the boards' **information architecture and copy** and re-skin with that language.

### Palette (tokens in `src/index.css`)

Muted on purpose: dusty maroon, sand and brick instead of saturated red, marigold and green, so the
app feels like printed stationery rather than an alert system.

| Token | Hex | Use |
|---|---|---|
| paper | `#F7F1E7` | app background (ivory card stock) |
| paper-2 | `#EFE6D6` | sunken panels |
| card | `#FFFCF6` | raised cards |
| ink | `#22181A` | text |
| ink-2 | `#5E5052` | secondary text |
| line | `#E2D5C3` | hairlines |
| maroon | `#5B2A33` | brand, hero sections, host |
| wine | `#7A4049` | italic accents, links |
| gold | `#B39A6B` | foil, primary CTA on dark, seal |
| sand | `#D4BC93` | primary CTA on dark (Kin pill) |
| blush | `#E6D6CC` | soft highlights |
| safe | `#55705D` | SAFE stamp |
| check | `#8C6C45` | CHECK stamp |
| stop | `#8F4038` | STOP stamp + danger screen |

Contrast: body text ink on paper is ~14:1; gold is never used for small text on paper.

### Type

- Display: **Fraunces** (soft serif, optical sizes, real italic) for headlines, one italic accent word.
- Body/UI: **Mukta** (Latin + Devanagari in one family, already chosen in the HTML boards).
- Kannada: **Noto Sans Kannada**; Hindi/Kannada display: **Tiro Devanagari Hindi** / **Tiro Kannada**.
- Minimum body size 17px on mobile (elders), buttons 18px, tap targets ≥ 52px.

### Signature details

1. **Verdict stamps**: SAFE / CHECK / STOP set as a rubber stamp (double border, slight rotation,
   condensed serif caps) pressed onto the "exhibit" card. One glance tells the story.
2. **Exhibit card**: the scanned file shown as a paper tag with filename in mono, like evidence.
3. **Gold hairline frame + seal**: the logo is a small wax seal "ck"; ornamental double rules divide
   sections, echoing the printed invites.
4. **Maroon full-bleed** sections for the hero, host flow and verified invite (stationery feel);
   the STOP screen goes full-bleed red so it can't be mistaken for anything else.

## 3. Information architecture (routes)

```
/                       Landing (responsive, desktop is the demo surface)
/start                  1 Welcome: name, language, role   (?role=parent|child|host)
/link                   2 Link family: QR of pair_link, WhatsApp, copy
/check                  3 Check a card: upload / paste, "checked today"
/result/:scanId         4 / 7 SAFE, CHECK or STOP result
/functions/:scanId      5 Your functions (day strip + timeline)
/directions/:scanId/:i  6 Directions (open in Google Maps by travel mode)
/first-hour/:scanId     8 First hour steps (spoken)
/host                   Host: wedding details
/host/speak             9 Speak invite (mic, or type)
/host/preview           10 Preview and send (WhatsApp, verified link)
/i/:inviteId            11 Verified invite page (guest)
/status                 Control room (projector, polls /api/status)
```

## 4. Responsive strategy

- **Mobile (<768)**: single column, sticky bottom action bar, thumb-reach CTAs.
- **Tablet (768–1023)**: same flow in a centred 560px sheet with more breathing room; results show
  the exhibit and the list side by side where it fits.
- **Desktop (≥1024)**: app screens become a split: left editorial panel (step headline, tagline,
  QR "open this on your phone"), right the flow column. Landing and control room are designed at 1440.

## 5. Architecture

Vite + React 19 + TypeScript, Tailwind v4 (tokens via `@theme`), React Router 7, `qrcode.react`.
API layer mirrors the contract; mocks run automatically when no `VITE_API_BASE_URL` is set, so the
whole demo works offline. Audio: `audio_b64` WAV when the backend sends it, browser speech synthesis
as a fallback so mocks still talk. Scan results are cached in session storage so result, functions,
directions and first-hour screens survive a refresh.

## 6. Build phases

1. Scaffold, tokens, fonts, shell, shared components, API + mocks, i18n.
2. Landing, Welcome, Link family.
3. Check a card, results (SAFE/CHECK/STOP), functions, directions, first hour, feedback.
4. Host flow and verified invite page.
5. Control room.
6. Build, lint, responsive check at 390 / 820 / 1440.

## 7. Contract gaps found (tell backend)

- No endpoint to fetch a verified invite by id for `/i/:id`; frontend calls `GET /api/invites/:id`
  and falls back to mock data. Please add or tell us the real shape.
- No endpoint to know whether the child has finished pairing; Link family shows "waiting" without polling.
- No endpoint to change language after `/api/identify`.
