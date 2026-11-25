"""Build the Card Kholo demo video: slides + live screenshots, Sarvam Bulbul voiceover, burned-in captions, SRT.

Usage: python demo/video/make_video.py        (needs .env with SARVAM_API_KEY and ffmpeg on PATH)
Inputs: demo/video/shots/*.png (from capture.py). Output: demo/video/CardKholo_demo.mp4 + .srt (--short, under 2 min) or CardKholo_demo_extended.mp4 (full walkthrough)
"""

import base64
import hashlib
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import httpx
from dotenv import dotenv_values
from PIL import Image, ImageDraw, ImageFont
from sarvamai import SarvamAI

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHOTS, BUILD = HERE / "shots", HERE / "build"
ENV = dotenv_values(ROOT / ".env")
W, H, BAND = 1920, 1080, 150
MAROON, DEEP, PAPER, GOLD, INK, SAGE, RED = "#5a1f29", "#2a1418", "#f6efe3", "#d4a64f", "#2a1e1a", "#7f9c83", "#c0574b"

# Spoken text -> caption text.
CAPTION_FIX = [("Shaadi Card Priya dot pdf dot apk", "Shaadi_Card_Priya.pdf.apk"), ("dot pdf dot apk", ".pdf.apk"), ("Android Manifest", "AndroidManifest.xml"), ("classes dot dex", "classes.dex"),
               ("nineteen thirty", "1930"), ("S H A 256", "SHA-256"), ("O T Ps", "OTPs"), ("cybercrime dot gov dot in", "cybercrime.gov.in"),
               ("card kholo dot vercel dot app", "card-kholo.vercel.app"), ("A slash B", "A/B")]


def font(size, bold=False, serif=False):
    names = (["georgiab.ttf"] if bold else ["georgia.ttf"]) if serif else (["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"])
    for n in names + ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]:
        for d in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", ""):
            try:
                return ImageFont.truetype(str(Path(d) / n) if d else n, size)
            except OSError:
                pass
    return ImageFont.load_default(size=size)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


# ---------------------------------------------------------------- slides
def base(title, kicker=None):
    img = Image.new("RGB", (W, H - BAND), DEEP)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=GOLD)
    if kicker:
        d.text((110, 70), kicker.upper(), font=font(30, bold=True), fill=GOLD)
    d.text((110, 112), title, font=font(70, serif=True), fill=PAPER)
    return img, d


def box(d, xy, title, body, fill=MAROON, title_fill=GOLD):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle(xy, radius=22, fill=fill, outline="#7a3a44", width=2)
    d.text((x0 + 24, y0 + 18), title, font=font(30, bold=True), fill=title_fill)
    y = y0 + 64
    for line in wrap(d, body, font(25), x1 - x0 - 48):
        d.text((x0 + 24, y), line, font=font(25), fill=PAPER)
        y += 34


def arrow(d, a, b):
    d.line([a, b], fill=GOLD, width=5)
    import math
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (2.6, -2.6):
        d.line([b, (b[0] + 22 * math.cos(ang + s), b[1] + 22 * math.sin(ang + s))], fill=GOLD, width=5)


def slide_title():
    img = Image.new("RGB", (W, H - BAND), MAROON)
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, W - 60, H - BAND - 60], outline=GOLD, width=4)
    d.text((W // 2, 300), "Card Kholo", font=font(150, bold=True, serif=True), fill=PAPER, anchor="mm")
    d.text((W // 2, 430), "The safe way to open, and send, a wedding card", font=font(46, serif=True), fill=GOLD, anchor="mm")
    d.text((W // 2, 560), "Sarvam AI  ·  Flagsmith  ·  NudgeBee  ·  Telegram", font=font(36), fill=PAPER, anchor="mm")
    d.text((W // 2, 640), "card-kholo.vercel.app", font=font(32, bold=True), fill=GOLD, anchor="mm")
    return img


def slide_problem():
    img, d = base("A wedding card that steals OTPs", "The problem")
    items = [("1", "The invite", "A forwarded WhatsApp file named like Shaadi_Card_Priya.pdf.apk, looks like a PDF card."),
             ("2", "The tap", "It is really an Android app. One tap installs it on a parent's phone."),
             ("3", "The theft", "The app reads SMS and bank OTPs, and money leaves the account."),
             ("4", "The silence", "Scams count on families not talking. Nobody else knows until it is too late.")]
    for i, (n, t, b) in enumerate(items):
        x = 110 + i * 430
        box(d, (x, 300, x + 400, 700), f"{n}. {t}", b)
    return img


def slide_workflow():
    img, d = base("The complete workflow", "How it works")
    box(d, (60, 300, 400, 520), "1. Forward", "Parent uploads the card (photo, PDF, any file) or pastes the message.")
    box(d, (470, 300, 850, 520), "2. Check", "Deterministic rules + Flagsmith rule packs decide the verdict. AI never marks safe.")
    box(d, (940, 200, 1380, 420), "3a. Real card: SAFE", "Sarvam reads every function: calendar, Maps, reminders.", fill="#3d5a45", title_fill=PAPER)
    box(d, (940, 470, 1380, 720), "3b. Fake card: STOP", "Full-screen stop, Bulbul voice warning, Telegram alert to the son or daughter.", fill="#7a2a2a", title_fill=PAPER)
    box(d, (1460, 470, 1860, 720), "4. Safety loop", "False alarms -> NudgeBee incident -> human approves -> Flagsmith rollback.")
    arrow(d, (400, 410), (470, 410))
    arrow(d, (850, 380), (940, 310))
    arrow(d, (850, 450), (940, 590))
    arrow(d, (1380, 595), (1460, 595))
    d.text((110, 790), "Three people use it: the parent checks cards, the son or daughter gets alerts, the host sends verified invites.",
           font=font(28), fill=GOLD)
    return img


def slide_telegram():
    img, d = base("Instant alert to the family", "Telegram  ·  @cardkholo_alert_bot")
    d.rounded_rectangle((560, 260, 1360, 860), radius=40, fill="#17212b")
    d.text((600, 285), "Card Kholo", font=font(32, bold=True), fill=PAPER)
    d.text((600, 325), "bot", font=font(24), fill="#7d8b99")
    msg = ("Card Kholo alert: Sunita Agarwal received the file 'Shaadi_Card_Priya.pdf.apk'. Card Kholo flagged it as "
           "dangerous. An Android app may be able to read SMS. Ask them to leave it unopened and call them now.")
    d.rounded_rectangle((600, 390, 1320, 700), radius=24, fill="#2b5278")
    y = 410
    for line in wrap(d, msg, font(29), 670):
        d.text((625, y), line, font=font(29), fill="white")
        y += 40
    d.rounded_rectangle((600, 720, 1320, 790), radius=18, fill="#3a4a5c")
    d.text((960, 755), "This was a real invite", font=font(29, bold=True), fill="white", anchor="mm")
    d.text((110, 880 - 30), "The exact message format the backend sends; the button feeds the false-alarm loop.", font=font(26), fill=GOLD)
    return img


def slide_sarvam():
    img, d = base("Sarvam AI: everything families read and hear", "Sponsor 1")
    rows = [("Document AI + vision", "Reads the card: every function with date, time and venue. Document AI and a vision model run in parallel; the first good answer wins (about 5-10 s)."),
            ("Bulbul TTS", "Speaks the STOP warning and the first-hour steps in Hindi, Kannada and English. Clips are cached at startup so they play instantly."),
            ("Saaras STT (codemix)", "Turns a host's spoken note (Hinglish is fine) into text."),
            ("sarvam-105b", "Picks the invited functions and writes a warm personal invite in the guest's language."),
            ("Rule of the house", "AI only reads and speaks. It never decides that something is safe.")]
    y = 270
    for t, b in rows:
        d.text((110, y), t, font=font(34, bold=True), fill=GOLD)
        for line in wrap(d, b, font(29), 1180):
            d.text((620, y + 2), line, font=font(29), fill=PAPER)
            y += 40
        y += 34
    return img


def slide_flagsmith():
    img, d = base("Flagsmith: the live brain of the scam rules", "Sponsor 2")
    feats, segs = flagsmith_snapshot()
    d.text((110, 250), "Live config (Development environment, read from the Admin API)", font=font(26, bold=True), fill=GOLD)
    y = 300
    for name, info in feats:
        d.text((110, y), name, font=font(28, bold=True), fill=PAPER)
        d.text((480, y), info, font=font(26), fill="#e8dcc8")
        y += 44
    y += 10
    for name, rule in segs:
        d.text((110, y), f"segment {name}", font=font(28, bold=True), fill=GOLD)
        d.text((480, y), rule, font=font(26), fill="#e8dcc8")
        y += 44
    points = ["Each rule pack is a flag + JSON remote config", "Remote evaluation per identity (lang, role, beta)",
              "parents -> strict mode, hosts -> host invites", "canary_20: risky packs reach 20% / beta first",
              "New scam domain in the dashboard = blocked in seconds", "Webhook streams every change to /status",
              "Multivariate A/B test of the warning itself"]
    yy = 300
    for p in points:
        for line in wrap(d, "• " + p, font(28), 560):
            d.text((1250, yy), line, font=font(28), fill=PAPER)
            yy += 38
        yy += 12
    return img


def slide_nudgebee():
    img, d = base("NudgeBee: human-approved rollback", "Sponsor 3")
    steps = [("Families", "tap 'This was a real invite' (app or Telegram)"), ("Backend", "3 false alarms for one pack in 5 min -> incident"),
             ("NudgeBee", "webhook starts the 'Card Kholo pack rollback' workflow"), ("Human", "approves in NudgeBee (approve / reject)"),
             ("NudgeBee", "Flagsmith Admin API: delete canary override, turn pack off"), ("Callback", "/hooks/rolled-back closes the incident, alerts children")]
    for i, (t, b) in enumerate(steps):
        col = i if i < 3 else 5 - i  # second row runs right to left, so the flow snakes
        x, y = 70 + col * 610, 280 + (i // 3) * 280
        box(d, (x, y, x + 560, y + 220), f"{i + 1}. {t}", b)
        if i < 2:
            arrow(d, (x + 560, y + 110), (x + 610, y + 110))
        elif 3 <= i < 5:
            arrow(d, (x, y + 110), (x - 50, y + 110))
    arrow(d, (1690, 500), (1690, 560))
    d.text((110, 860), "Plan B: a protected backend route performs the same rollback if NudgeBee is down.", font=font(28), fill=GOLD)
    return img


def slide_stack():
    img, d = base("Built for trust", "Architecture and privacy")
    rows = [("Frontend", "React + Vite + TypeScript + Tailwind on Vercel. Works in any phone browser, no install."),
            ("Backend", "FastAPI + SQLite on Render. Telegram bot for pairing and alerts."),
            ("Verdicts", "Only deterministic rules (APK markers, extensions, magic bytes, risky links) + Flagsmith packs."),
            ("Privacy", "Files are processed in memory and never stored: only the SHA-256 fingerprint and the verdict."),
            ("Demo safety", "The demo APK is harmless: a text file named AndroidManifest.xml and an empty classes.dex.")]
    y = 280
    for t, b in rows:
        d.text((110, y), t, font=font(34, bold=True), fill=GOLD)
        for line in wrap(d, b, font(30), 1300):
            d.text((480, y + 2), line, font=font(30), fill=PAPER)
            y += 42
        y += 36
    return img


def slide_end():
    img = Image.new("RGB", (W, H - BAND), MAROON)
    d = ImageDraw.Draw(img)
    d.text((W // 2, 330), "Check the card before you tap.", font=font(84, serif=True), fill=PAPER, anchor="mm")
    d.text((W // 2, 470), "card-kholo.vercel.app", font=font(48, bold=True), fill=GOLD, anchor="mm")
    d.text((W // 2, 560), "Card Kholo  ·  Sarvam AI  ·  Flagsmith  ·  NudgeBee", font=font(34), fill=PAPER, anchor="mm")
    return img


def flagsmith_snapshot():
    h = {"Authorization": "Api-Key " + ENV["FLAGSMITH_ADMIN_API_KEY"]}
    b, pid, key = "https://api.flagsmith.com/api/v1", ENV["FLAGSMITH_PROJECT_ID"], ENV["FLAGSMITH_ADMIN_ENV_KEY"]
    feats = httpx.get(f"{b}/projects/{pid}/features/?page_size=100", headers=h, timeout=30).json()["results"]
    states = httpx.get(f"{b}/environments/{key}/featurestates/?page_size=200", headers=h, timeout=30).json()["results"]
    on = {s["feature"]: s["enabled"] for s in states if s.get("feature_segment") is None}
    order = ["pack_core", "pack_wedding_2026", "pack_broad_test", "scam_signatures", "strict_mode", "host_invites", "spoken_summary", "warning_style"]
    out = []
    for f in sorted(feats, key=lambda f: order.index(f["name"]) if f["name"] in order else 99):
        info = "ON" if on.get(f["id"]) else "OFF by default"
        if f["name"] == "scam_signatures":
            info = "ON, JSON rule list (filename / text / domain)"
        if f["name"] == "warning_style":
            info = "multivariate: calm / urgent 50%"
        if f["name"] in ("strict_mode", "host_invites", "pack_broad_test"):
            info += {"strict_mode": " + ON for parents", "host_invites": " + ON for hosts", "pack_broad_test": " + canary_20 override"}[f["name"]]
        out.append((f["name"], info))
    segs = [("parents", "role = parent"), ("hosts", "role = host"), ("canary_20", "20% split OR beta = true")]
    return out, segs


def screenshot(name):
    shot = Image.open(SHOTS / f"{name}.png").convert("RGB")
    scale = (H - BAND) / shot.height
    shot = shot.resize((int(shot.width * scale), H - BAND), Image.LANCZOS)
    img = Image.new("RGB", (W, H - BAND), "#120a0c")
    img.paste(shot, ((W - shot.width) // 2, 0))
    return img


# ---------------------------------------------------------------- script
SCENES = [
    (slide_title, "Namaste. This is Card Kholo, the safe way to open, and send, a wedding card. In wedding season, families forward hundreds of invites on WhatsApp. Card Kholo checks every one of them before anyone taps."),
    (slide_problem, "Scammers now send fake wedding invitations as Android apps, with names like Shaadi Card Priya dot pdf dot apk. One tap installs an app that reads SMS and bank O T Ps. The people most likely to tap are our parents. And scams count on families not talking to each other."),
    (slide_workflow, "Here is the complete workflow. A parent forwards any card: a photo, a PDF, a file, or a message. Deterministic rules and Flagsmith rule packs decide the verdict. AI never marks anything as safe. A real card goes to Sarvam, which reads every function into a calendar. A fake card triggers a full screen stop, a spoken warning from Sarvam Bulbul, and an instant Telegram alert to the son or daughter. And if a rule ever flags real invites, NudgeBee runs a human approved rollback in Flagsmith."),
    ("01_landing", "This is the live product, a web app on Vercel with a FastAPI backend on Render. There is nothing to install. It opens in any phone browser, and the home page explains the idea in one line: every scam says don't tell your family. We tell them."),
    ("02_start", "Setup takes two questions. First the language for warnings and voice: Hindi, Kannada or English. Then the role: a parent who checks wedding cards, a son or daughter who gets alerts, or a host who sends invites. Language, role and beta become Flagsmith identity traits."),
    ("03_link", "Next, the parent links a son or daughter. The child scans this QR code with their phone. It opens our Telegram bot with a one time pairing code, they tap Start, and within seconds this screen shows that they are linked."),
    ("04_check", "Now the everyday use. When a card arrives on WhatsApp, the parent opens Card Kholo and uploads the file exactly as it came, or pastes the message or link. The file is processed in memory and never stored. We keep only its S H A 256 fingerprint and the verdict."),
    ("05_result_ok", "This is a real wedding card. The rules find no hidden app, no fake file type, and no scam link, so the verdict is safe. Then Sarvam Document AI reads the card, with a Sarvam vision model running in parallel, and the first good answer wins. Every function comes out: Mehendi, Sangeet, Phere and Reception, with date, time and venue."),
    ("06_calendar", "With one tap the whole wedding lands in the calendar. A week strip, the next function, and a leave around time, forty five minutes before it starts. Each function has a Google Calendar link, and one download adds all of them, with a reminder an hour before each."),
    ("07_directions", "Directions opens the venue on Google Maps, with car, bike or metro, a start button, and a WhatsApp share, so the whole family reaches on time."),
    ("08_stop", "Now the fake card: Shaadi Card Priya dot pdf dot apk. The rules see a zip with Android Manifest and classes dot dex inside, an Android app extension, and a double extension. The verdict is dangerous. A full screen stop appears, and the warning plays out loud, generated by Sarvam Bulbul."),
    (slide_telegram, "At the same moment, the linked son or daughter gets this Telegram alert, so they can call right away. If it was actually a real invite, one button says so, and that feedback flows into our rule safety loop."),
    ("11_stop_hindi", "Every parent sees and hears the warning in their own language. Here is the same stop screen in Hindi. Kannada and English work the same way."),
    ("09_first_hour", "And if they already opened it, Card Kholo shows the first hour steps: call nineteen thirty, the national cybercrime helpline. Turn on airplane mode. Call the bank to block cards and UPI. And report on cybercrime dot gov dot in, with a complaint draft ready to copy, and a button to tell the family on WhatsApp."),
    ("10_check_link", "Pasted messages are checked too. URL shorteners, plain HTTP, links to bare IP addresses and look alike punycode domains are suspicious. For parents, a Flagsmith segment turns on strict mode, so anything suspicious becomes a full stop."),
    ("12_checked_today", "Every check is listed under Checked today on the phone, so the family can see at a glance what came in and what was stopped."),
    ("14_host", "Card Kholo also helps the people sending invites. A host adds the wedding functions once, then simply speaks: invite Riya to the Sangeet, in Hindi. Sarvam Saaras transcribes the voice note, Sarvam's 105 billion parameter model writes a personal invite in the guest's language, and the guest gets a verified link and a WhatsApp message instead of a file. When that link is checked, Card Kholo marks it as a verified invite from that family."),
    (slide_sarvam, "Sponsor one, Sarvam AI, powers everything a family reads and hears. Document AI and a vision model read the card. Bulbul speaks the warning and the first hour steps in Hindi, Kannada and English, cached at startup so they play instantly. Saaras turns a host's voice note into text, and the 105B model writes the invitation. Even the voice you are hearing in this video is Sarvam Bulbul."),
    (slide_flagsmith, "Sponsor two, Flagsmith, is the live brain of the scam rules. Every rule pack is a feature flag, with its JSON rules as remote config, evaluated remotely for each identity using language, role and beta traits. Segments give parents strict mode and hosts the invite feature. New risky packs roll out to a canary segment first: twenty percent of users, or anyone in beta. When a new scam site appears, we add one domain rule in the dashboard and every phone blocks it within seconds, with no app update. A webhook streams every flag change to our control room. And a multivariate flag runs an A slash B test on the warning itself, calm versus urgent, measured by how many people listen to the end."),
    (slide_nudgebee, "Sponsor three, NudgeBee, closes the loop. When families mark three real invites from one pack as false alarms within five minutes, the backend opens an incident and sends it to a NudgeBee workflow. A human approves it in NudgeBee. NudgeBee then calls the Flagsmith Admin API to remove the canary override and switch the pack off, and calls our backend back to close the incident and tell the linked children. If NudgeBee is ever down, a protected Plan B route performs the same rollback from our side."),
    ("13_status", "This is the control room, live from production, built for the projector. The broad canary pack flagged three real invites. NudgeBee rolled it back after a human approval, the incident is closed, and the live flag feed shows both changes labelled NudgeBee rollback. The packs, family alerts and the warning experiment all update every three seconds."),
    (slide_stack, "Under the hood: React on Vercel, FastAPI on Render, and Telegram for family alerts. Verdicts come only from deterministic rules and Flagsmith packs. Files never touch the disk. And the demo app file is completely harmless, just a text file with an Android name."),
    (slide_end, "Card Kholo. Check the card before you tap. Thank you."),
]


SHORT_SCENES = [
    (slide_title, "Card Kholo. The safe way to open, and send, a wedding card."),
    (slide_workflow, "Scammers send fake wedding cards as Android apps that steal bank O T Ps from parents. Card Kholo checks every invite before anyone taps. Rules and Flagsmith decide the verdict, never AI."),
    ("02_start", "A parent picks a language, Hindi, Kannada or English, and a role."),
    ("03_link", "Their son or daughter scans this QR code to link on Telegram."),
    ("04_check", "When a card arrives, the parent uploads it as is, or pastes the message. Files are never stored."),
    ("05_result_ok", "A real card is safe. Sarvam Document AI and a vision model read every function, with date, time and venue."),
    ("06_calendar", "One tap adds the whole wedding to the calendar, with reminders and a leave by time."),
    ("07_directions", "Directions open in Google Maps, by car, bike or metro, with a WhatsApp share."),
    ("08_stop", "A fake card, Shaadi Card Priya dot pdf dot apk, is caught by its Android files. A full screen stop plays a warning in the parent's language, voiced by Sarvam Bulbul."),
    (slide_telegram, "And the son or daughter gets a Telegram alert instantly."),
    ("11_stop_hindi", "Every warning is shown and spoken in Hindi, Kannada or English."),
    ("09_first_hour", "Already opened it? First hour steps: call nineteen thirty, airplane mode, block the bank."),
    ("10_check_link", "Pasted links are checked too: shorteners, plain HTTP and look alike domains. For parents, strict mode turns them into a stop."),
    ("14_host", "Hosts just speak an invite. Sarvam Saaras transcribes it, Sarvam 105B writes it, and guests get a verified link."),
    (slide_sarvam, "Sarvam powers it all: Document AI reads cards, Bulbul speaks warnings, Saaras and the 105B model write invites. Even this voice is Bulbul."),
    (slide_flagsmith, "Flagsmith runs the rules. Each scam pack is a flag with JSON rules. Parents get strict mode. Risky packs reach a twenty percent canary first. A new scam domain blocks every phone in seconds. And a multivariate flag tests the warning itself."),
    (slide_nudgebee, "If a pack flags real invites, three false alarms open an incident in NudgeBee. A human approves, and NudgeBee removes the canary and turns the pack off in Flagsmith."),
    ("13_status", "Our live control room shows it: incident closed, changes labelled NudgeBee rollback."),
    (slide_end, "Card Kholo. Check the card before you tap."),
]
PACE = 1.0
GAP = 0.6


# ---------------------------------------------------------------- audio + render
def tts(text, idx):
    BUILD.mkdir(parents=True, exist_ok=True)
    path = BUILD / f"voice_{idx:02d}_{hashlib.sha1(f'{PACE}|{text}'.encode()).hexdigest()[:8]}.wav"
    if not path.exists():
        with httpx.Client(timeout=90) as http:
            client = SarvamAI(api_subscription_key=ENV["SARVAM_API_KEY"], httpx_client=http)
            r = client.text_to_speech.convert(text=text, language_code="en-IN", model="bulbul:v3",
                                              speaker=ENV.get("BULBUL_SPEAKER_EN") or "shubh", output_audio_codec="wav", pace=PACE,
                                              request_options={"timeout_in_seconds": 90, "max_retries": 2})
        path.write_bytes(b"".join(base64.b64decode(a) for a in r.audios[:1]))
    with wave.open(str(path)) as w:
        return path, w.getnframes() / w.getframerate()


def caption_chunks(text):
    for spoken, shown in CAPTION_FIX:
        text = text.replace(spoken, shown)
    sentences = re.split(r"(?<=[.!?:])\s+", text)
    chunks = []
    for s in sentences:
        words = s.split()
        while words:
            n = len(words) if len(words) <= 14 else min(12, len(words) - 4)
            chunks.append(" ".join(words[:n]))
            words = words[n:]
    return chunks


def frame(picture, caption):
    img = Image.new("RGB", (W, H), "#0d0709")
    img.paste(picture, (0, 0))
    d = ImageDraw.Draw(img)
    f = font(40, bold=True)
    lines = wrap(d, caption, f, W - 240)[:2]
    y = H - BAND + (BAND - 52 * len(lines)) // 2
    for line in lines:
        d.text((W // 2, y + 24), line, font=f, fill="white", anchor="mm")
        y += 52
    return img


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    global PACE, GAP
    short = "--short" in sys.argv
    scenes, name = (SHORT_SCENES, "CardKholo_demo") if short else (SCENES, "CardKholo_demo_extended")
    if short:
        PACE, GAP = 1.1, 0.25
    BUILD.mkdir(parents=True, exist_ok=True)
    segments, srt, clock, n = [], [], 0.0, 1
    for i, (visual, text) in enumerate(scenes):
        picture = visual() if callable(visual) else screenshot(visual)
        voice, dur = tts(text, i)
        total = dur + GAP
        chunks = caption_chunks(text)
        weights = [len(c) for c in chunks]
        lines, t = [], 0.0
        for j, c in enumerate(chunks):
            seg = total * weights[j] / sum(weights)
            p = BUILD / f"f_{i:02d}_{j:02d}.png"
            frame(picture, c).save(p)
            lines.append(f"file '{p.name}'\nduration {seg:.3f}")
            srt.append(f"{n}\n{srt_time(clock + t)} --> {srt_time(clock + t + seg)}\n{c}\n")
            n += 1
            t += seg
        lines.append(f"file '{p.name}'")
        (BUILD / f"list_{i:02d}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        out = BUILD / f"seg_{i:02d}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"list_{i:02d}.txt",
                        "-i", voice.name, "-af", f"apad=pad_dur={GAP}", "-t", f"{total:.3f}", "-r", "30",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", out.name], cwd=BUILD, check=True)
        segments.append(out.name)
        clock += total
        print(f"scene {i + 1:02d}/{len(scenes)} {total:5.1f}s")
    (BUILD / "segments.txt").write_text("".join(f"file '{s}'\n" for s in segments), encoding="utf-8")
    final = HERE / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "segments.txt",
                    "-c", "copy", "-movflags", "+faststart", str(final)], cwd=BUILD, check=True)
    (HERE / f"{name}.srt").write_text("\n".join(srt), encoding="utf-8")
    print(f"done: {final} ({clock / 60:.1f} min)")


if __name__ == "__main__":
    main()
