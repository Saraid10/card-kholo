# Card Kholo: web frontend

The safe way to open a wedding card. Real cards go to your calendar. Fake ones are stopped, explained out loud in
Hindi, Kannada or English, and your family is told on Telegram.

Design rationale, palette, routes and contract gaps: see [DESIGN.md](DESIGN.md).

## Run

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # type-check + production build into dist/
```

With no `VITE_API_BASE_URL` set, the app runs on built-in mocks, so the whole demo works offline
(including the false-alarm → NudgeBee → rollback loop on `/status`).

## Environment (`.env.local`)

| Variable | Meaning |
|---|---|
| `VITE_API_BASE_URL` | FastAPI backend, e.g. `https://cardkholo.onrender.com` |
| `VITE_USE_MOCKS` | `true` forces mocks, `false` forces the real API |
| `VITE_TELEGRAM_BOT_USERNAME` | Bot used for the pairing link fallback |

## Screens

| Route | Screen |
|---|---|
| `/` | Landing (desktop demo surface) |
| `/start` | Welcome: name, language, role (`?role=parent\|child\|host`, `?beta=1`) |
| `/link` | Link family: QR / WhatsApp / copy pair link |
| `/check` | Check a card: upload, paste, sample files |
| `/result/:scanId` | SAFE, CHECK or STOP result |
| `/functions/:scanId` | Your functions timeline |
| `/directions/:scanId/:i` | Directions (opens Google Maps) |
| `/first-hour/:scanId` | First-hour steps |
| `/host`, `/host/speak`, `/host/preview` | Host: wedding details, speak invite, preview and send |
| `/i/:inviteId` | Verified invite page for guests |
| `/status` | Control room (projector) |

## Demo tips

- On `/check`, "Try a sample" builds harmless demo files in the browser. The fake one is a few bytes of text named
  `Shaadi_Card_Priya.pdf.apk`; there is no real malware anywhere.
- Incident demo with mocks: check the "Invitation PDF" sample and tap "This was a real invite" three times (within
  5 minutes). `/status` shows the incident open, then rolled back about 6 seconds later.
- Audio: the backend's `audio_b64` (Bulbul WAV) is played when present; otherwise the browser's speech synthesis
  speaks the same text, so mocks still talk.

## AI assistance

This frontend was built with help from Claude Code (AI coding assistant), as the event rules require us to disclose.
