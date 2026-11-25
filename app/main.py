import asyncio
import hashlib
import io
import logging
import secrets
from contextlib import aclosing, asynccontextmanager, suppress
from pathlib import PureWindowsPath
from typing import Annotated

import qrcode
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from qrcode.exceptions import DataOverflowError
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from . import alerts, calendar_links, config, db, examples, flag_changes, flags, guest_page, incidents, invites, models, sarvam_client, scan_rules, voice

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.check_startup(logging.getLogger("uvicorn.error"))
    db.initialize()
    flag_changes.initialize()
    sarvam_client.load_cache()
    voice.CLIPS.clear()
    await asyncio.gather(voice.warm_clips(), asyncio.to_thread(alerts.register_webhook))
    retry = asyncio.create_task(voice.retry_missing())
    notifications = asyncio.create_task(incidents.retry_notifications())
    try:
        yield
    finally:
        retry.cancel()
        notifications.cancel()
        for task in (retry, notifications):
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="Card Kholo", version="0.8.0", lifespan=lifespan, description=(
    "Identify a user, then scan an invite file or pasted message using deterministic rules."
))
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS,
                   allow_methods=["GET", "POST"], allow_headers=["*"])


class MemoryFormParser(MultiPartParser):
    # A zero spool threshold keeps temporary uploads in memory until closed.
    spool_max_size = 0


async def limited_stream(request: Request, limit: int):
    used = 0
    for length in request.headers.getlist("content-length"):
        if not length.isascii() or not length.isdigit() or len(length) > 19:
            raise HTTPException(400, "Invalid Content-Length")
        if int(length) > limit:
            raise HTTPException(413, "Request body exceeds the size limit")
    async for chunk in request.stream():
        used += len(chunk)
        if used > limit:
            raise HTTPException(413, "Request body exceeds the size limit")
        yield chunk


def upload_schema(field: str) -> dict:
    return {"schema": {
        "type": "object", "required": ["user_id", field],
        "properties": {"user_id": {"type": "string"}, field: {"type": "string", "format": "binary"}},
    }}


@asynccontextmanager
async def uploaded_form(request: Request, field: str):
    if request.headers.get("content-type", "").split(";")[0].lower() != "multipart/form-data":
        raise HTTPException(415, "Expected multipart/form-data")
    try:
        async with aclosing(limited_stream(request, config.MAX_FORM_BYTES)) as stream:
            form = await MemoryFormParser(request.headers, stream, max_files=1, max_fields=1).parse()
    except (MultiPartException, ValueError) as exc:
        raise HTTPException(400, "Invalid multipart form") from exc
    try:
        user_id, upload = form.get("user_id"), form.get(field)
        if not isinstance(user_id, str) or not isinstance(upload, UploadFile):
            raise HTTPException(422, f"Supply user_id and a {field} upload")
        yield user_id, upload
    finally:
        await form.close()


def require_secret(supplied: str | None, expected: str) -> None:
    if not expected or not supplied or not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(403, "Invalid hook secret")


HookSecret = Annotated[str | None, Header(alias="X-Hook-Secret")]
TelegramSecret = Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")]


@app.api_route("/health", methods=["GET", "HEAD"], response_model=models.Ack)  # HEAD for uptime pingers
def health():
    return {"ok": True}


@app.post("/api/identify", response_model=models.Identity)
def identify(body: models.Identify):
    user, code = db.create_user(body)
    flags.for_user(user)
    link = f"https://t.me/{config.TELEGRAM_BOT_USERNAME}?start={code}" if code else None
    return {"user_id": user["id"], "pair_link": link}


@app.get("/api/pairing/{user_id}", response_model=models.PairingStatus)
def pairing(user_id: str):
    return db.pairing_status(user_id)


def _classify(user_id: str, data: bytes | None, filename: str, content_type: str, text: str | None):
    user = db.get_user(user_id)
    if user is None:
        raise HTTPException(404, "Unknown user_id. Identify the user before scanning.")
    settings = flags.for_user(user)
    result = scan_rules.evaluate(settings, data=data, filename=filename,
                                 content_type=content_type, text=text, lookup_invite=db.invite_family)
    file_hash = hashlib.sha256(data).hexdigest() if data is not None else None
    style = settings.warning_style if result.verdict != "OK" else None
    scan_id = db.save_scan(user_id, result.verdict, result.pack_hits, file_hash, filename or None, style)
    warning = None
    if result.verdict == "DANGEROUS" and settings.enabled["spoken_summary"]:
        warning = voice.CLIPS.get((user["lang"], "warning"))
    return user["lang"], file_hash, {
        "scan_id": scan_id, "verdict": result.verdict, "reasons": result.reasons,
        "pack_hits": result.pack_hits, "verified_from": result.verified_from, "audio_b64": warning,
        "functions": [], "ics_url": None, "warning_style": style,
        "alert_sent": result.verdict == "DANGEROUS" and alerts.notify_parent_scan(user, scan_id, filename),
    }


async def scan_input(user_id: str, *, data: bytes | None = None, filename: str = "",
                     content_type: str = "", text: str | None = None) -> dict:
    lang, digest, scan = await asyncio.to_thread(_classify, user_id, data, filename, content_type, text)
    if data is None or scan["verdict"] != "OK":
        return scan
    mime = scan_rules.card_mime(data)
    if mime:
        card = await sarvam_client.read_card(data, filename, mime, lang, digest)
        if card is None:
            scan["reasons"].append(sarvam_client.UNREADABLE)
        else:
            calendar_links.remember(scan["scan_id"], card)
            asyncio.get_running_loop().call_later(calendar_links.TTL_SECONDS, calendar_links.forget, scan["scan_id"])
            scan["functions"] = card["functions"]
            scan["ics_url"] = f'{config.APP_BASE_URL}/api/ics/{scan["scan_id"]}'
    return scan


@app.post("/api/scan", response_model=models.Scan, openapi_extra={"requestBody": {
    "required": True, "content": {
        "application/json": {"schema": models.TextScan.model_json_schema()},
        "multipart/form-data": upload_schema("file"),
    },
}})
async def scan(request: Request):
    if request.headers.get("content-type", "").split(";")[0].lower() == "application/json":
        try:
            raw = bytearray()
            async for chunk in limited_stream(request, config.MAX_TEXT_BYTES):
                raw.extend(chunk)
            body = models.TextScan.model_validate_json(raw)
        except ValidationError as exc:
            raise HTTPException(422, "Expected JSON with user_id and text") from exc
        if not body.text.strip():
            raise HTTPException(422, "Supply a nonempty message or link")
        return await scan_input(body.user_id, text=body.text)
    async with uploaded_form(request, "file") as (user_id, upload):
        filename = PureWindowsPath(upload.filename or "").name
        data = await upload.read()
        content_type = upload.content_type or ""
    if not data:
        raise HTTPException(422, "Supply a nonempty file")
    return await scan_input(user_id, data=data, filename=filename, content_type=content_type)


@app.post("/api/opened", response_model=models.Opened)
def opened(body: models.ScanRef):
    context = db.scan_context(body.scan_id)
    if context is None:
        raise HTTPException(404, "Unknown scan_id")
    audio = voice.CLIPS.get((context["lang"], "first_hour")) if flags.for_user(context).enabled["spoken_summary"] else None
    return {"steps": voice.first_hour_steps(context), "audio_b64": audio}


@app.post("/api/feedback", response_model=models.FeedbackResult)
def feedback(body: models.Feedback):
    result = incidents.record_feedback(body.scan_id, body.real_invite)
    if result is None:
        raise HTTPException(404, "Unknown scan_id")
    return result


@app.post("/api/events", response_model=models.Ack)
def experiment_event(body: models.ExperimentEvent):
    if body.event not in db.EVENTS:
        raise HTTPException(400, f"Unknown event. Use one of: {', '.join(db.EVENTS)}")
    if not db.record_event(body.scan_id, body.event):
        raise HTTPException(404, "Unknown scan_id")
    return {"ok": True}


@app.get("/api/status", response_model=models.Status)
def status():
    return incidents.status()


class CalendarResponse(Response):
    media_type = "text/calendar"


@app.get("/api/ics/{scan_id}", response_class=CalendarResponse)
def calendar(scan_id: str):
    content = calendar_links.lookup(scan_id)
    if content is None:
        raise HTTPException(404, "Calendar unavailable or expired")
    return CalendarResponse(content, headers={"Content-Disposition": 'attachment; filename="card-kholo.ics"',
                                              "Cache-Control": "no-store"})


@app.post("/api/invites/wedding", response_model=models.WeddingRef)
def wedding(body: models.Wedding):
    return invites.save_wedding(body)


@app.post("/api/invites/voice", response_model=models.VoiceInvite, openapi_extra={"requestBody": {
    "required": True, "content": {"multipart/form-data": upload_schema("audio")},
}})
async def voice_invite(request: Request):
    async with uploaded_form(request, "audio") as (user_id, upload):
        audio = await upload.read()
        return await asyncio.to_thread(invites.create, user_id, PureWindowsPath(upload.filename or "note.wav").name,
                                       audio, upload.content_type or "application/octet-stream")


def guest_invite(token: str) -> dict:
    if token == "demo":
        return {"token": "demo", "preview": True, "couple": examples.COUPLE, "host_family": "Sharma",
                "guest_name": "Sharma ji", "functions": [examples.FUNCTION.model_dump()], "audio_b64": None,
                "created_at": "2026-01-01 00:00:00"}
    invite = db.get_invite(token)
    if invite is None:
        raise HTTPException(404, "Unknown invitation")
    return invite


@app.get("/i/{token}", response_class=HTMLResponse)
def invite_page(token: str):
    return HTMLResponse(guest_page.render(guest_invite(token)),
                        headers={"Referrer-Policy": "no-referrer", "Cache-Control": "private, no-store"})


@app.get("/i/{token}/calendar.ics", response_class=CalendarResponse)
def guest_calendar(token: str):
    invite = guest_invite(token)
    stamp = invite["created_at"].translate(str.maketrans({"-": "", ":": "", " ": "T"})) + "Z"
    content = calendar_links.render_ics(token, invite, stamp)
    return CalendarResponse(content, headers={"Content-Disposition": 'attachment; filename="card-kholo.ics"',
                                              "Cache-Control": "private, no-store"})


@app.post("/hooks/telegram", response_model=models.Ack)
def telegram(update: dict, secret: TelegramSecret = None):
    require_secret(secret, config.TELEGRAM_SECRET)
    alerts.handle_update(update, incidents.record_feedback)
    return {"ok": True}


@app.post("/hooks/rolled-back", response_model=models.Ack)
def rolled_back(body: models.Rollback, secret: HookSecret = None):
    require_secret(secret, config.HOOK_SECRET)
    return incidents.rollback(body.incident_id, confirmed_pack=body.pack)


@app.post("/hooks/flagsmith", response_model=models.Ack, openapi_extra={
    "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
})
async def flagsmith_webhook(request: Request, token: str | None = None):
    require_secret(token, config.HOOK_SECRET)
    raw = bytearray()
    async for chunk in limited_stream(request, config.MAX_TEXT_BYTES):
        raw.extend(chunk)
    await asyncio.to_thread(flag_changes.record, bytes(raw))
    return {"ok": True}


@app.post("/api/admin/fallback-rollback/{incident_id}", response_model=models.Ack)
def fallback_rollback(incident_id: str, secret: HookSecret = None):
    require_secret(secret, config.HOOK_SECRET)
    return incidents.rollback(incident_id)


class PNGResponse(Response):
    media_type = "image/png"


@app.get("/qr", response_class=PNGResponse, responses={200: {
    "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}}
}})
def qr(url: str | None = None):
    value = url or config.APP_BASE_URL
    if len(value) > 7089:
        raise HTTPException(422, "URL exceeds QR capacity")
    try:
        image = qrcode.make(value)
    except DataOverflowError as exc:
        raise HTTPException(422, "URL exceeds QR capacity") from exc
    output = io.BytesIO()
    image.save(output, format="PNG")
    return PNGResponse(output.getvalue())
