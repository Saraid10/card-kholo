"""Prepared warning audio and localized first-hour guidance."""

import asyncio
import logging

from . import config, sarvam_client

log = logging.getLogger(__name__)
SCRIPTS = {
    "en": {
        "warning": "Stop. This wedding invitation may be a scam. Don't open it or install anything. Call your family for help.",
        "first_hour": "Turn on airplane mode now. Call 1930. Call your bank and block cards and UPI.",
    },
    "hi": {
        "warning": "रुकिए! यह शादी का निमंत्रण धोखा हो सकता है। इसे मत खोलिए। कोई ऐप इंस्टॉल मत कीजिए। अपने परिवार को फ़ोन कीजिए।",
        "first_hour": "अभी फ़ोन को एयरप्लेन मोड में डालिए। 1930 पर कॉल कीजिए। अपने बैंक को कॉल करके कार्ड और UPI बंद करवाइए।",
    },
    "kn": {
        "warning": "ನಿಲ್ಲಿ! ಈ ಮದುವೆಯ ಆಹ್ವಾನ ವಂಚನೆ ಆಗಿರಬಹುದು. ಇದನ್ನು ತೆರೆಯಬೇಡಿ. ಯಾವುದೇ ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಬೇಡಿ. ನಿಮ್ಮ ಮನೆಯವರಿಗೆ ಕರೆ ಮಾಡಿ.",
        "first_hour": "ಈಗಲೇ ಫೋನ್ ಅನ್ನು ಏರ್‌ಪ್ಲೇನ್ ಮೋಡ್‌ಗೆ ಹಾಕಿ. 1930ಕ್ಕೆ ಕರೆ ಮಾಡಿ. ನಿಮ್ಮ ಬ್ಯಾಂಕಿಗೆ ಕರೆ ಮಾಡಿ ಕಾರ್ಡ್ ಮತ್ತು UPI ಬ್ಲಾಕ್ ಮಾಡಿಸಿ.",
    },
}
CLIPS: dict[tuple[str, str], str] = {}


async def warm_clips() -> None:
    if not config.SARVAM_API_KEY:
        return

    async def generate(lang, kind, text):
        try:
            async with asyncio.timeout(sarvam_client.TTS_SECONDS):
                CLIPS[lang, kind] = await asyncio.to_thread(sarvam_client.synthesize, text, lang)
        except Exception as exc:
            log.warning("Bulbul clip unavailable for %s/%s (%s)", lang, kind, type(exc).__name__)
    await asyncio.gather(*(generate(lang, kind, text) for lang, scripts in SCRIPTS.items()
                           for kind, text in scripts.items() if (lang, kind) not in CLIPS))


async def retry_missing() -> None:
    for delay in (30, 120):
        if not config.SARVAM_API_KEY or all((lang, kind) in CLIPS for lang, scripts in SCRIPTS.items() for kind in scripts):
            return
        await asyncio.sleep(delay)
        await warm_clips()


def first_hour_steps(context: dict) -> list[str]:
    lang = context["lang"]
    date = context["scan_date"]
    filename = context["filename"]
    if lang == "hi":
        item = filename or "एक शादी के निमंत्रण का लिंक या संदेश"
        return [
            "अभी फ़ोन का एयरप्लेन मोड चालू करें।",
            "दूसरे फ़ोन से राष्ट्रीय साइबर अपराध हेल्पलाइन 1930 पर कॉल करें।",
            f"cybercrime.gov.in पर शिकायत दर्ज करें। शिकायत का मसौदा — {date} की स्कैन रिपोर्ट: मैंने शादी के निमंत्रण में {item} खोला। मुझे धोखाधड़ी का संदेह है।",
            "अपने बैंक को कॉल करके कार्ड और UPI ब्लॉक करवाएँ।",
            "अगर आपने कोई ऐप इंस्टॉल किया है तो उसे हटाएँ या परिवार से मदद लें।",
        ]
    if lang == "kn":
        item = filename or "ಮದುವೆಯ ಆಹ್ವಾನದ ಲಿಂಕ್ ಅಥವಾ ಸಂದೇಶ"
        return [
            "ಈಗಲೇ ಫೋನ್ ಅನ್ನು ಏರ್‌ಪ್ಲೇನ್ ಮೋಡ್‌ಗೆ ಹಾಕಿ.",
            "ಬೇರೆ ಫೋನಿನಿಂದ ರಾಷ್ಟ್ರೀಯ ಸೈಬರ್ ಅಪರಾಧ ಸಹಾಯವಾಣಿ 1930ಕ್ಕೆ ಕರೆ ಮಾಡಿ.",
            f"cybercrime.gov.in ನಲ್ಲಿ ದೂರು ನೀಡಿ. ದೂರಿನ ಕರಡು — {date}ರ ಸ್ಕ್ಯಾನ್ ವರದಿ: ಮದುವೆಯ ಆಹ್ವಾನದಲ್ಲಿ ಬಂದ {item} ತೆರೆದೆ. ಇದು ವಂಚನೆ ಎಂದು ಶಂಕಿಸುತ್ತೇನೆ.",
            "ನಿಮ್ಮ ಬ್ಯಾಂಕಿಗೆ ಕರೆ ಮಾಡಿ ಕಾರ್ಡ್‌ಗಳು ಮತ್ತು UPI ಅನ್ನು ಬ್ಲಾಕ್ ಮಾಡಿಸಿ.",
            "ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಿದ್ದರೆ ಅದನ್ನು ತೆಗೆದುಹಾಕಿ ಅಥವಾ ಮನೆಯವರ ಸಹಾಯ ಕೇಳಿ.",
        ]
    item = filename or "a link or message"
    return [
        "Turn on airplane mode now.",
        "From another phone, call 1930, the national cybercrime helpline.",
        f"File a complaint at cybercrime.gov.in. Complaint draft — Scan date {date}. I opened {item} from a wedding invitation. I suspect fraud.",
        "Call your bank and block cards and UPI.",
        "If you installed an app, uninstall it or ask your family for help.",
    ]
