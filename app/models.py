from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Identify(BaseModel):
    name: str
    lang: Literal["hi", "kn", "en"]
    role: Literal["parent", "child", "host"]
    beta: bool = False


class Identity(BaseModel):
    user_id: str
    pair_link: str | None


class PairingStatus(BaseModel):
    linked: bool
    child_name: str | None


class TextScan(BaseModel):
    user_id: str
    text: str


class Function(BaseModel):
    name: str
    name_original: str
    date: str
    time: str
    venue_name: str
    venue_address: str
    city: str
    gcal_url: str
    maps_url: str


class Scan(BaseModel):
    scan_id: str
    verdict: Literal["DANGEROUS", "SUSPICIOUS", "OK"]
    reasons: list[str]
    pack_hits: list[str]
    verified_from: str | None
    audio_b64: str | None
    functions: list[Function]
    ics_url: str | None
    alert_sent: bool
    warning_style: Literal["calm", "urgent"] | None = None


class ScanRef(BaseModel):
    scan_id: str


class ExperimentEvent(ScanRef):
    event: str


class Opened(BaseModel):
    steps: list[str]
    audio_b64: str | None


class Feedback(ScanRef):
    real_invite: bool


class Ack(BaseModel):
    ok: bool


class FeedbackResult(Ack):
    pack_false_alarms: dict[str, int]


class Pack(BaseModel):
    name: str
    enabled: bool
    false_alarms_5m: int


class FlagChange(BaseModel):
    time: str
    feature: str
    summary: str
    source: str


class Variant(BaseModel):
    name: str
    shown: int
    played: int
    completed: int
    opened_anyway: int
    completion_rate: float


class Experiment(BaseModel):
    flag: str
    variants: list[Variant]


class Status(BaseModel):
    packs: list[Pack]
    incidents: list[dict]
    last_alerts: list[dict]
    flag_changes: list[FlagChange] = Field(default_factory=list)
    experiment: Experiment | None = None


class Wedding(BaseModel):
    user_id: str
    couple: str
    host_family: str
    functions: list[Function]


class WeddingRef(BaseModel):
    wedding_id: str


class ParsedInvite(BaseModel):
    guest_name: str
    guest_lang: str
    function_names: list[str]
    phone: str
    tone: str


class VoiceInvite(BaseModel):
    transcript: str
    parsed: ParsedInvite
    invite_text: str
    invite_url: str
    wa_url: str
    audio_b64: str | None


class Rollback(BaseModel):
    # NudgeBee templates may send the ID as a number.
    model_config = ConfigDict(coerce_numbers_to_str=True)
    incident_id: str
    pack: str
    approver: str
