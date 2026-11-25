"""Deterministic file and text checks. URLs are parsed locally."""

import io
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from ipaddress import ip_address
from pathlib import PureWindowsPath
from urllib.parse import SplitResult, urlsplit
from zipfile import BadZipFile, ZipFile, is_zipfile

from . import config
from .flags import UserFlags


SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "rb.gy", "shorturl.at"}
ANDROID_EXTENSIONS = {".apk", ".xapk", ".apks", ".apkm"}
EXECUTABLE_EXTENSIONS = {".apk", ".exe", ".bat", ".scr", ".js", ".vbs"}
HEADERS = (
    ("PDF", {".pdf"}, {"application/pdf"}, b"%PDF"),
    ("JPEG", {".jpg", ".jpeg"}, {"image/jpeg", "image/jpg"}, b"\xff\xd8\xff"),
    ("PNG", {".png"}, {"image/png"}, b"\x89PNG"),
)
LINK = re.compile(
    r"""https?://[^\s<>"']+|(?<![\w@./-])(?:[\w-]+\.)+[\w-]+(?::\d+)?(?:/[^\s<>"']*)?""",
    re.IGNORECASE,
)
RANK = {"OK": 0, "SUSPICIOUS": 1, "DANGEROUS": 2}


def card_mime(data: bytes) -> str | None:
    for _, _, media_types, header in HEADERS:
        if data.startswith(header):
            return "image/jpeg" if "image/jpeg" in media_types else next(iter(media_types))
    return None


@dataclass
class Result:
    verdict: str = "OK"
    reasons: list[str] = field(default_factory=list)
    pack_hits: list[str] = field(default_factory=list)
    verified_from: str | None = None

    def hit(self, severity: str, reason: str, pack: str | None = None) -> None:
        if RANK[severity] > RANK[self.verdict]:
            self.verdict = severity
        if reason not in self.reasons:
            self.reasons.append(reason)
        if pack and pack not in self.pack_hits:
            self.pack_hits.append(pack)


def _check_file(result: Result, data: bytes, filename: str, content_type: str) -> None:
    stream = io.BytesIO(data)
    try:
        if is_zipfile(stream):
            with ZipFile(stream) as archive:
                if {"AndroidManifest.xml", "classes.dex"}.issubset(archive.namelist()):
                    result.hit("DANGEROUS", "The archive contains Android application files.")
    except (BadZipFile, UnicodeError, OSError, NotImplementedError):
        pass  # No confirmed Android archive match. Still check the name and header.

    name = filename.lower()
    suffixes = PureWindowsPath(name).suffixes
    extension = next((ext for ext in ANDROID_EXTENSIONS if name.endswith(ext)), None)
    if extension:
        result.hit("DANGEROUS", f"The filename ends in the Android app extension {extension}.")
    if len(suffixes) >= 2 and suffixes[-1] in EXECUTABLE_EXTENSIONS:
        result.hit("DANGEROUS", "The filename has a double extension ending in an executable type.")
    mime = content_type.partition(";")[0].strip().lower()
    for label, extensions, media_types, header in HEADERS:
        if (name.endswith(tuple(extensions)) or mime in media_types) and not data.startswith(header):
            result.hit("SUSPICIOUS", f"The file claims to be {label}, but its header does not match.")


def _matches_domain(host: str, domain: str) -> bool:
    domain = domain.lower().strip().rstrip(".")
    return host == domain or host.endswith("." + domain)


def _invite_token(url: SplitResult) -> str | None:
    if url.scheme not in ("http", "https") or url.username is not None or url.query or url.fragment:
        return None
    try:
        base = urlsplit(config.APP_BASE_URL)
        default_port = 443 if url.scheme == "https" else 80
        port = url.port if url.port is not None else default_port
        base_port = base.port if base.port is not None else default_port
        if (url.scheme, url.hostname, port) != (base.scheme, base.hostname, base_port):
            return None
    except ValueError:
        return None
    prefix = base.path.rstrip("/") + "/i/"
    if url.path.startswith(prefix):
        token = url.path[len(prefix):]
        if re.fullmatch(r"[A-Za-z0-9_-]+", token):
            return token
    return None


def _check_links(result: Result, text: str,
                 lookup_invite: Callable[[str], str | None] | None) -> tuple[set[str], str | None]:
    hosts = set()
    link_count = 0
    family = None
    for match in LINK.finditer(text):
        link_count += 1
        link = match.group().rstrip(".,;:!?)}")
        if link.endswith("]") and link.count("]") > link.count("["):
            link = link[:-1]
        try:
            url = urlsplit(link if "://" in link[:8] else "//" + link)
            host = (url.hostname or "").lower().rstrip(".")
        except ValueError:
            continue
        if not host:
            continue
        hosts.add(host)
        if (lookup_invite is not None and match.group() == link
                and (match.start() == 0 or text[match.start() - 1].isspace())):
            token = _invite_token(url)
            if token is not None:
                family = lookup_invite(token)
                if family:
                    continue
        if any(_matches_domain(host, domain) for domain in SHORTENERS):
            result.hit("SUSPICIOUS", "A link uses a URL shortener.")
        if url.scheme == "http":
            result.hit("SUSPICIOUS", "A link uses unencrypted HTTP.")
        if any(label.startswith("xn--") for label in host.split(".")):
            result.hit("SUSPICIOUS", "A link contains a punycode domain.")
        try:
            ip_address(host)
        except ValueError:
            continue
        result.hit("SUSPICIOUS", "A link uses an IP address as its host.")
    return hosts, family if link_count == 1 else None


def evaluate(settings: UserFlags, *, data: bytes | None = None, filename: str = "",
             content_type: str = "", text: str | None = None,
             lookup_invite: Callable[[str], str | None] | None = None) -> Result:
    result = Result()
    if data is not None:
        _check_file(result, data, filename, content_type)
    hosts, family = _check_links(result, text or "", lookup_invite)
    for rule in settings.active_rules():
        pattern = rule["pattern"]
        if rule["type"] == "domain":
            matched = any(_matches_domain(host, pattern) for host in hosts)
        elif rule["type"] == "filename_regex":
            matched = data is not None and re.search(pattern, filename) is not None
        else:
            matched = text is not None and re.search(pattern, text) is not None
        if matched:
            result.hit(rule["severity"], rule["label"], rule["pack"])
    if result.verdict == "SUSPICIOUS" and settings.enabled["strict_mode"]:
        result.hit("DANGEROUS", "Strict mode raised this suspicious scan to dangerous.")
    if family and data is None and result.verdict == "OK":
        result.verified_from = family
        result.reasons.append(f"Verified invite from the {family} family")
    if not result.reasons:
        result.reasons.append("No configured scan rule flagged this input.")
    return result
