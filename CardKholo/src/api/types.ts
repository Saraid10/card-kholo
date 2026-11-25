// Mirrors the fixed API contract. Everything the backend might omit is optional here.

export type Lang = 'hi' | 'kn' | 'en'
export type Role = 'parent' | 'child' | 'host'
export type Verdict = 'DANGEROUS' | 'SUSPICIOUS' | 'OK'
export type WarningStyle = 'calm' | 'urgent'
export type ExperimentEvent = 'warning_shown' | 'warning_played' | 'warning_completed' | 'opened_anyway'

export interface IdentifyReq { name: string; lang: Lang; role: Role; beta: boolean }
export interface IdentifyRes { user_id: string; pair_link: string | null }

export interface WeddingFunction {
  name?: string
  name_original?: string
  date?: string
  time?: string
  venue_name?: string
  venue_address?: string
  city?: string
  gcal_url?: string
  maps_url?: string
}

export interface ScanRes {
  scan_id: string
  verdict: Verdict
  reasons?: string[]
  pack_hits?: string[]
  verified_from?: string | null
  audio_b64?: string | null
  functions?: WeddingFunction[]
  ics_url?: string | null
  alert_sent?: boolean
  warning_style?: WarningStyle | null
  /** Optional extras from card reading (Extract schema). */
  couple?: string | null
  host_family?: string | null
}

export interface OpenedRes { steps?: string[]; audio_b64?: string | null }
export interface FeedbackRes { ok?: boolean; pack_false_alarms?: number | Record<string, number> }

export interface Pack { name?: string; enabled?: boolean; false_alarms_5m?: number }
export interface Incident {
  id?: string | number
  pack?: string
  count?: number
  status?: 'open' | 'rolled_back' | 'rejected' | string
  opened_at?: string
  closed_at?: string | null
}
/** Backend omits personal details: family_alert has verdict, rollback has pack. */
export interface AlertItem { time?: string; type?: 'family_alert' | 'rollback' | string; verdict?: string; pack?: string }
export interface FlagChange { time?: string; feature?: string; summary?: string; source?: string }
export interface Variant {
  name?: string
  shown?: number
  played?: number
  completed?: number
  opened_anyway?: number
  completion_rate?: number
}
export interface Experiment { flag?: string; variants?: Variant[] }
export interface StatusRes {
  packs?: Pack[]
  incidents?: Incident[]
  last_alerts?: AlertItem[]
  flag_changes?: FlagChange[]
  experiment?: Experiment | null
}

export interface WeddingReq {
  user_id: string
  couple: string
  host_family: string
  functions: WeddingFunction[]
}
export interface WeddingRes { wedding_id: string }

export interface VoiceRes {
  transcript?: string
  parsed?: unknown
  invite_text?: string
  invite_url?: string
  wa_url?: string
  audio_b64?: string | null
}

/** Verified invite page (/i/:id). Not in the original contract: GET /api/invites/:id. */
export interface InviteRes {
  invite_id: string
  guest?: string
  lang?: Lang
  couple?: string
  couple_original?: string
  host_family?: string
  functions?: WeddingFunction[]
  ics_url?: string | null
  audio_b64?: string | null
}

/** OPTIONAL backend route GET /api/pairing/{user_id}. */
export interface PairingRes { linked: boolean; child_name?: string | null }
