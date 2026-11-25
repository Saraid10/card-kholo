"""Normalize card events and publish scan-specific calendars for ten minutes."""

import re
from datetime import UTC, datetime, timedelta
from threading import Lock
from time import monotonic
from urllib.parse import urlencode

TTL_SECONDS = 600


def _parse(value: str, formats: tuple[str, ...]) -> datetime | None:
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _period(event: dict) -> tuple[str, str]:
    day = datetime.fromisoformat(event["date"])
    if event["time"]:
        start = datetime.fromisoformat(f'{event["date"]}T{event["time"]}')
        return start.strftime("%Y%m%dT%H%M%S"), (start + timedelta(hours=3)).strftime("%Y%m%dT%H%M%S")
    return day.strftime("%Y%m%d"), (day + timedelta(days=1)).strftime("%Y%m%d")


def _location(event: dict) -> str:
    return ", ".join(event[key] for key in ("venue_name", "venue_address", "city") if event[key])


def directions_url(location: str) -> str:
    return "https://www.google.com/maps/dir/?" + urlencode({"api": 1, "destination": location})


def _title(event: dict, couple: str) -> str:
    return " - ".join(part for part in (event["name"] or event["name_original"], couple) if part)


def normalize(raw: dict) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("functions"), list):
        raise ValueError("Expected a card with an event list")
    couple = raw.get("couple", "")
    couple = couple.strip() if isinstance(couple, str) else ""
    events = []
    for item in raw["functions"]:
        if not isinstance(item, dict):
            continue
        event = {k: item[k].strip() if isinstance(item.get(k), str) else ""
                 for k in ("name", "name_original", "date", "time", "venue_name", "venue_address", "city")}
        day = _parse(event["date"].replace(",", ""), (
            "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
        ))
        if not day:
            continue
        clock_text = re.sub(r"(?<=\d)\.(?=\d{2}\b|\d{2}[ap])", ":", event["time"], flags=re.I)
        clock = _parse(clock_text.replace(".", "").replace(" ", "").upper(),
                       ("%H:%M", "%H:%M:%S", "%I:%M%p", "%I%p"))
        event["date"] = day.date().isoformat()
        event["time"] = clock.strftime("%H:%M") if clock else ""
        try:
            start, end = _period(event)
        except OverflowError:
            continue
        location = _location(event)
        event["gcal_url"] = "https://calendar.google.com/calendar/render?" + urlencode({
            "action": "TEMPLATE", "text": _title(event, couple), "dates": f"{start}/{end}",
            "ctz": "Asia/Kolkata", "location": location, "details": "Added with Card Kholo",
        })
        event["maps_url"] = directions_url(location)
        events.append(event)
    events.sort(key=lambda event: (event["date"], not event["time"], event["time"]))
    return {"couple": couple, "functions": events}


def _escape(value: str) -> str:
    return (value.replace("\\", "\\\\").replace("\r\n", "\n").replace("\r", "\n")
            .replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;"))


def _fold(line: str) -> str:
    parts = []
    size = 0
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > 75:
            parts.append("\r\n ")
            size = 1
        parts.append(char)
        size += width
    return "".join(parts)


def render_ics(scan_id: str, card: dict, stamp: str) -> str:
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Card Kholo//Wedding Invite//EN",
        "BEGIN:VTIMEZONE", "TZID:Asia/Kolkata", "BEGIN:STANDARD", "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0530", "TZOFFSETTO:+0530", "TZNAME:IST", "END:STANDARD", "END:VTIMEZONE",
    ]
    for index, event in enumerate(card["functions"]):
        start, end = _period(event)
        param = "TZID=Asia/Kolkata" if event["time"] else "VALUE=DATE"
        lines.extend([
            "BEGIN:VEVENT", f"UID:{scan_id}-{index}@cardkholo", f"DTSTAMP:{stamp}",
            f"DTSTART;{param}:{start}", f"DTEND;{param}:{end}",
            "SUMMARY:" + _escape(_title(event, card["couple"])),
            "LOCATION:" + _escape(_location(event)),
            "BEGIN:VALARM", "ACTION:DISPLAY",
            "DESCRIPTION:" + _escape((event["name"] or event["name_original"] or "Event") + " in 1 hour"),
            "TRIGGER:-PT60M", "END:VALARM", "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


_calendars = {}
_lock = Lock()


def _purge(now: float) -> None:
    # Entries are inserted in expiry order, one per new scan ID.
    while _calendars:
        oldest = next(iter(_calendars))
        if _calendars[oldest][0] > now:
            break
        del _calendars[oldest]


def remember(scan_id: str, card: dict) -> None:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    with _lock:
        now = monotonic()
        _purge(now)
        _calendars[scan_id] = (now + TTL_SECONDS, card, stamp)


def lookup(scan_id: str) -> str | None:
    with _lock:
        _purge(monotonic())
        entry = _calendars.get(scan_id)
    return render_ics(scan_id, entry[1], entry[2]) if entry else None


def forget(scan_id: str) -> None:
    with _lock:
        _calendars.pop(scan_id, None)
