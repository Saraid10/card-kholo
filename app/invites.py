"""Create personalized invitations from a host's saved wedding and voice note."""

import logging
import re
import secrets
from urllib.parse import urlencode

from fastapi import HTTPException

from . import calendar_links, config, db, flags, models, sarvam_client

log = logging.getLogger(__name__)
INVITATIONS = {
    "en": "{guest}, please join us to celebrate {couple}!",
    "hi": "{guest}, {couple} की शादी में आपका स्वागत है!",
    "kn": "{guest}, {couple} ಅವರ ಮದುವೆಗೆ ಆತ್ಮೀಯ ಆಹ್ವಾನ!",
    "ta": "{guest}, {couple} திருமணத்திற்கு அன்புடன் அழைக்கிறோம்!",
    "te": "{guest}, {couple} వివాహానికి సాదర ఆహ్వానం!",
    "mr": "{guest}, {couple} यांच्या लग्नाला आपले हार्दिक स्वागत!",
    "gu": "{guest}, {couple} ના લગ્નમાં આપનું હાર્દિક સ્વાગત છે!",
    "bn": "{guest}, {couple} এর বিয়েতে আপনাকে সাদর আমন্ত্রণ!",
    "ml": "{guest}, {couple} വിവാഹത്തിലേക്ക് സ്നേഹപൂർവം ക്ഷണിക്കുന്നു!",
    "pa": "{guest}, {couple} ਦੇ ਵਿਆਹ ਲਈ ਤੁਹਾਨੂੰ ਪਿਆਰ ਭਰਿਆ ਸੱਦਾ!",
}


def require_host_flag(user_id: str) -> dict:
    user = db.get_user(user_id)
    if user is None:
        raise HTTPException(404, "Unknown user_id")
    if not flags.for_user(user).enabled.get("host_invites"):
        raise HTTPException(403, "Host invites are disabled for this user")
    return user


def save_wedding(body: models.Wedding) -> dict:
    require_host_flag(body.user_id)
    card = calendar_links.normalize(body.model_dump())
    functions = card["functions"]
    if not card["couple"] or not body.host_family.strip():
        raise HTTPException(422, "Supply the couple and host family names")
    if (not functions or len(functions) != len(body.functions)
            or any(not (event["name"] or event["name_original"]) for event in functions)):
        raise HTTPException(422, "Each wedding needs at least one function with a name and valid date")
    return {"wedding_id": db.save_wedding(body.user_id, card["couple"], body.host_family.strip(), functions)}


def _select_functions(events: list[dict], names: list[str]) -> list[dict]:
    requested = {name.strip().casefold() for name in names if name.strip()}
    selected = []
    matched = set()
    for event in events:
        aliases = {event["name"].casefold(), event["name_original"].casefold()}
        if aliases & requested:
            selected.append(event)
            matched.update(aliases & requested)
    if not selected or requested != matched:
        raise HTTPException(422, "Record another note naming the functions from this wedding")
    return selected


def _digits(phone: str) -> str:
    number = re.sub("[^0-9]", "", phone)
    if len(number) == 11 and number.startswith("0"):
        number = number[1:]
    if len(number) == 10:
        return "91" + number
    return number if 11 <= len(number) <= 15 and not number.startswith("0") else ""


def create(user_id: str, filename: str, audio: bytes, mime: str) -> dict:
    user = require_host_flag(user_id)
    wedding = db.latest_wedding(user_id)
    if wedding is None:
        raise HTTPException(409, "Save a wedding before creating a voice invite")
    if not audio:
        raise HTTPException(422, "Supply a nonempty voice note")
    if not config.SARVAM_API_KEY:
        raise HTTPException(503, "Set SARVAM_API_KEY to transcribe voice invites")
    try:
        transcript = sarvam_client.transcribe_invite(filename, audio, mime, user["lang"])
        names = [event["name"] or event["name_original"] for event in wedding["functions"]]
        parsed = models.ParsedInvite.model_validate(sarvam_client.parse_invite(transcript, names))
    except Exception as exc:
        log.warning("Voice invite transcription or parsing failed (%s)", type(exc).__name__)
        raise HTTPException(502, "Could not read the voice note. Try a short recording naming the guest and functions.") from exc
    guest = parsed.guest_name.strip()
    if not guest or parsed.guest_lang not in INVITATIONS:
        raise HTTPException(422, "Supply a guest name and a supported guest language")
    functions = _select_functions(wedding["functions"], parsed.function_names)
    token = secrets.token_urlsafe(12)
    url = f"{config.APP_BASE_URL}/i/{token}"
    number = _digits(parsed.phone)
    # Keep the dictated number out of the guest page, saved message and narration.
    phone_digits = number[-10:] if number else ""
    if phone_digits and phone_digits in re.sub(r"\D", "", guest):
        raise HTTPException(422, "Provide a guest name separately from their phone number")
    try:
        tone = parsed.tone
        if phone_digits and phone_digits in re.sub(r"\D", "", tone):
            tone = "warm"
        message = sarvam_client.write_invite(guest, parsed.guest_lang, tone, wedding["couple"], functions, url)
        if phone_digits and phone_digits in re.sub(r"\D", "", message.removesuffix(url)):
            raise ValueError("Contact number in invitation text")
    except Exception as exc:
        log.warning("Using invitation template (%s)", type(exc).__name__)
        intro = INVITATIONS[parsed.guest_lang].format(guest=guest, couple=wedding["couple"])
        details = [" · ".join(filter(None, (event["name_original"] or event["name"], event["date"],
                   event["time"], event["venue_name"] or event["venue_address"] or event["city"]))) for event in functions]
        message = "\n".join([intro, *details, url])
        if len(message) >= 400:
            raise HTTPException(422, "These function details exceed the invite length. Select fewer functions or shorten the names.")
    try:
        speech = sarvam_client.synthesize(message.removesuffix(url).strip(), parsed.guest_lang)
    except Exception as exc:
        log.warning("Invite audio unavailable (%s)", type(exc).__name__)
        speech = None
    db.save_invite({"token": token, "host_user_id": user_id, "host_family": wedding["host_family"],
                    "couple": wedding["couple"], "guest_name": guest, "guest_lang": parsed.guest_lang,
                    "functions": functions, "message": message, "audio_b64": speech})
    return {"transcript": transcript, "parsed": parsed, "invite_text": message, "invite_url": url,
            "wa_url": f"https://wa.me/{number}?" + urlencode({"text": message}), "audio_b64": speech}
