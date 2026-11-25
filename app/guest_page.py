"""Render a guest's public invitation from a stored, normalized invite."""

from datetime import date, time
from html import escape
from urllib.parse import quote


_STYLES = """
:root {
  color-scheme: dark;
  --bg: #0E0F12;
  --ink: #F2F0EA;
  --muted: #A9ABB4;
  --panel: #17181D;
  --inner: #1F2128;
  --accent: #C6F432;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 400 16px/1.5 Archivo, Mukta, sans-serif;
  overflow-wrap: anywhere;
}
main { max-width: 480px; margin: auto; padding: 24px 16px 32px; }
header { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 24px; }
.brand, h1 { font-weight: 900; font-stretch: 125%; font-variation-settings: "wdth" 125; }
.brand { font-size: 23px; letter-spacing: -0.055em; line-height: 1.1; }
.badge { display: inline-flex; align-items: center; gap: 8px; padding: 7px 10px; border: 1px solid #2A2C34; border-radius: 999px; font-size: 12px; }
.verified::before { content: ""; width: 7px; height: 7px; background: var(--accent); border-radius: 50%; box-shadow: 0 0 8px #C6F43299; }
.hero { padding: 28px 24px 32px; border-radius: 32px; background: var(--accent); color: var(--bg); }
.intro { margin: 0 0 14px; max-width: 32ch; font-weight: 500; }
h1 { font-size: 40px; letter-spacing: -0.035em; line-height: 1.09; margin: 0; }
.listen {
  display: inline-flex; align-items: center; gap: 10px; margin-top: 24px;
  background: var(--bg); color: var(--ink); padding: 10px 17px; min-height: 44px;
  border: 0; border-radius: 999px; font: 600 14px Archivo, Mukta, sans-serif; cursor: pointer;
}
.listen::before { content: ""; border-left: 9px solid currentColor; border-top: 6px solid transparent; border-bottom: 6px solid transparent; }
.listen.playing::before { width: 4px; height: 12px; box-sizing: content-box; border: 0; border-inline: 3px solid currentColor; }
audio { display: block; margin-top: 16px; width: 100%; }
[hidden] { display: none; }
.schedule { margin-top: 14px; padding: 20px; border-radius: 24px; background: var(--panel); }
h2 { margin: 0 0 4px; font-size: 20px; letter-spacing: -0.025em; }
ul { margin: 0; padding: 0; list-style: none; }
.event { display: grid; grid-template-columns: 50px minmax(0, 1fr) 44px; gap: 12px; align-items: start; padding: 18px 0; }
.event + .event, .calendar { border-top: 1px solid #2A2C34; }
.date { display: grid; place-items: center; padding: 7px 3px; background: var(--inner); border-radius: 12px; line-height: 1.15; }
.month, .weekday { color: var(--muted); font-size: 11px; }
.month { text-transform: uppercase; letter-spacing: 0.07em; }
.day { margin: 2px 0; font-size: 24px; font-weight: 800; }
h3 { margin: 0; font-size: 18px; line-height: 1.3; }
.details { margin: 3px 0 0; color: var(--muted); font-size: 14px; }
.directions, .calendar a { font-size: 14px; text-underline-offset: 3px; }
.directions { display: inline-block; padding-block: 5px; color: var(--accent); }
.add { display: grid; place-items: center; width: 44px; height: 44px; align-self: center; border-radius: 50%; background: var(--ink); color: var(--bg); font-size: 25px; text-decoration: none; }
.calendar { margin: 0; padding-top: 12px; }
.calendar a { color: var(--muted); }
footer { margin: 22px 8px; color: var(--muted); font-size: 13px; text-align: center; }
a:focus-visible, button:focus-visible { outline: 3px solid currentColor; outline-offset: 3px; }
.listen:focus-visible, .add:focus-visible { outline-color: var(--ink); box-shadow: 0 0 0 3px var(--bg); }
@media (max-width: 350px) {
  .schedule { padding: 16px; }
  .event { column-gap: 8px; }
}
"""

_AUDIO_SCRIPT = """
<script>
const audio = document.getElementById("invite-audio");
const button = document.getElementById("listen");
button.hidden = false;
audio.hidden = true;
button.addEventListener("click", async () => {
  if (!audio.paused) {
    audio.pause();
    return;
  }
  try {
    await audio.play();
  } catch {
    audio.hidden = false;
    button.hidden = true;
  }
});
function updateButton() {
  button.textContent = audio.paused ? "Hear the invite" : "Pause the invite";
  button.classList.toggle("playing", !audio.paused);
}
audio.addEventListener("play", updateButton);
audio.addEventListener("pause", updateButton);
audio.addEventListener("ended", updateButton);
</script>
"""


def _event_row(event: dict) -> str:
    day = date.fromisoformat(event["date"])
    clock = time.fromisoformat(event["time"]) if event["time"] else None
    when = clock.strftime("%I:%M %p").lstrip("0") if clock else "All day"
    venue = event["venue_name"] or event["venue_address"] or event["city"]
    details = escape(" · ".join(filter(None, (when, venue))))
    name = escape(event["name"] or event["name_original"] or "Function")
    return f"""
    <li class="event">
      <time class="date" datetime="{day.isoformat()}" aria-label="{day:%B %d, %Y}">
        <span class="month">{day:%b}</span><span class="day">{day.day}</span><span class="weekday">{day:%a}</span>
      </time>
      <div><h3>{name}</h3><p class="details">{details}</p>
        <a class="directions" href="{escape(event["maps_url"])}">Directions</a>
      </div>
      <a class="add" href="{escape(event["gcal_url"])}" aria-label="Add {name} to Google Calendar">+</a>
    </li>"""


def render(invite: dict) -> str:
    guest, family, couple = (escape(invite[key]) for key in ("guest_name", "host_family", "couple"))
    badge = ('<span class="badge">Sample invitation</span>' if invite.get("preview") else
             '<span class="badge verified">Verified by Card Kholo</span>')
    audio = ""
    if invite.get("audio_b64"):
        audio = f"""
        <button type="button" id="listen" class="listen" aria-controls="invite-audio" hidden>Hear the invite</button>
        <audio id="invite-audio" controls preload="none" aria-label="Hear the invite"
               src="data:audio/wav;base64,{escape(invite["audio_b64"])}"></audio>"""

    schedule = ""
    if invite["functions"]:
        rows = "".join(_event_row(event) for event in invite["functions"])
        token = quote(invite["token"], safe="")
        schedule = f"""
        <section class="schedule" aria-labelledby="functions"><h2 id="functions">Functions</h2>
          <ul>{rows}</ul>
          <p class="calendar"><a href="/i/{token}/calendar.ics">Save all functions to calendar</a></p>
        </section>"""

    return f"""<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>{couple} | Card Kholo</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&amp;family=Mukta:wght@400;500&amp;display=swap">
  <style>{_STYLES}</style>
</head><body><main>
  <header><span class="brand">cardkholo</span>{badge}</header>
  <section class="hero" aria-labelledby="couple">
    <p class="intro">{guest}, the {family} family invites you to</p><h1 id="couple">{couple}</h1>{audio}
  </section>{schedule}
  <footer>Card Kholo never sends files. A card that asks you to install an app is fake.</footer>
</main>{_AUDIO_SCRIPT if audio else ""}</body></html>"""
