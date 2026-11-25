"""Telegram pairing, family warnings and feedback buttons."""

import logging
from collections import deque
from datetime import UTC, datetime

from httpx import Client, HTTPError

from . import config, db
from .scan_rules import ANDROID_EXTENSIONS

log = logging.getLogger(__name__)
_recent = deque(maxlen=20)


def bot_call(method: str, **payload) -> bool:
    if not config.TELEGRAM_BOT_TOKEN:
        return False
    try:
        with Client(timeout=3) as client:
            response = client.post(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}", json=payload)
            response.raise_for_status()
            result = response.json()
            if isinstance(result, dict) and result.get("ok") is True:
                return True
        log.warning("Telegram declined %s", method)
    except (HTTPError, ValueError) as exc:
        # Exception messages may contain the bot token in the request URL.
        log.warning("Telegram %s failed (%s)", method, type(exc).__name__)
    return False


def register_webhook() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        return
    if not config.TELEGRAM_SECRET or not config.APP_BASE_URL.startswith("https://"):
        log.warning("Telegram webhook needs a public HTTPS APP_BASE_URL and TELEGRAM_SECRET")
        return
    bot_call("setWebhook", url=f"{config.APP_BASE_URL}/hooks/telegram", secret_token=config.TELEGRAM_SECRET,
             allowed_updates=["message", "callback_query"])


def notify_parent_scan(user: dict, scan_id: str, filename: str) -> bool:
    if user["role"] != "parent" or not config.TELEGRAM_BOT_TOKEN:
        return False
    chat_id = db.paired_chat(user["id"])
    if chat_id is None:
        return False
    subject = f"the file '{filename[:200]}'" if filename else "a wedding invitation message"
    detail = " An Android app may be able to read SMS." if filename.lower().endswith(tuple(ANDROID_EXTENSIONS)) else ""
    message = (f"Card Kholo alert: {user['name'][:150]} received {subject}. "
               f"Card Kholo flagged it as dangerous.{detail} Ask them to leave it unopened and call them now.")
    sent = bot_call("sendMessage", chat_id=chat_id, text=message, reply_markup={"inline_keyboard": [[
        {"text": "This was a real invite", "callback_data": f"fa:{scan_id}"}
    ]]})
    if sent:
        _recent.appendleft({"time": datetime.now(UTC).isoformat(), "type": "family_alert", "verdict": "DANGEROUS"})
    return sent


def recent_alerts() -> list[dict]:
    return list(_recent)


def notify_rollback(chat_id: int, pack: str) -> bool:
    sent = bot_call("sendMessage", chat_id=chat_id,
                    text=f"Card Kholo: the {pack} rule pack was causing false alarms and has been rolled back.")
    if sent:
        _recent.appendleft({"time": datetime.now(UTC).isoformat(), "type": "rollback", "pack": pack})
    return sent


def _start(message: dict) -> None:
    chat, sender = message.get("chat"), message.get("from")
    if not isinstance(chat, dict) or not isinstance(sender, dict) or chat.get("type") != "private":
        return
    chat_id = chat.get("id")
    if type(chat_id) is not int or not 0 < chat_id < 2**63 or chat_id != sender.get("id"):
        return
    text = message.get("text")
    words = text.split() if isinstance(text, str) else []
    if len(words) != 2 or words[0].split("@", 1)[0] != "/start":
        return
    parent = db.pair_child(words[1], chat_id, str(sender.get("first_name") or ""))
    reply = (f"Linked! You'll get an alert if {parent[:150]} receives a fake wedding card."
             if parent is not None else "This pairing link is invalid or already in use.")
    bot_call("sendMessage", chat_id=chat_id, text=reply)


def handle_update(update: dict, record_feedback) -> None:
    query = update.get("callback_query")
    if isinstance(query, dict) and isinstance(query.get("id"), str):
        reply = "This button is unavailable."
        data, sender = query.get("data"), query.get("from")
        if isinstance(data, str) and data.startswith("fa:") and isinstance(sender, dict):
            chat_id = sender.get("id")
            if type(chat_id) is int and record_feedback(data[3:], True, child_chat_id=chat_id):
                reply = "Thank you. Your feedback was recorded."
        bot_call("answerCallbackQuery", callback_query_id=query["id"], text=reply)
    elif isinstance(update.get("message"), dict):
        _start(update["message"])
