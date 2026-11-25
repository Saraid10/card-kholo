// Mock backend. Follows the contract; only used when USE_MOCKS is true.
// It is stateful so the demo tells the whole story offline: scans, family alerts,
// false-alarm taps, a NudgeBee incident and an automatic rollback.
import { buildGcalUrl, buildMapsUrl } from '../lib/calendar'
import { buildIcs } from '../lib/ics'
import { readJSON, writeJSON } from '../lib/storage'
import type {
  ExperimentEvent, FeedbackRes, FlagChange, IdentifyReq, IdentifyRes, Incident, InviteRes, PairingRes,
  OpenedRes, ScanRes, StatusRes, VoiceRes, WarningStyle, WeddingFunction, WeddingReq, WeddingRes,
} from './types'

export const MOCK_DELAY = 700
export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))
const id = (p: string) => `${p}_${Math.random().toString(36).slice(2, 10)}`
const iso = (ms: number) => new Date(ms).toISOString()

const COUPLE = 'Priya weds Arjun'

function fn(name: string, original: string, date: string, time: string, venue: string, addr: string, city: string): WeddingFunction {
  const location = [venue, addr, city].filter(Boolean).join(', ')
  return {
    name, name_original: original, date, time,
    venue_name: venue, venue_address: addr, city,
    gcal_url: buildGcalUrl({ title: `${name}: ${COUPLE}`, date, time, location, details: 'Added with Card Kholo' }) ?? '',
    maps_url: buildMapsUrl(`${venue} ${addr} ${city}`),
  }
}

export const DEMO_FUNCTIONS: WeddingFunction[] = [
  fn('Mehendi', 'मेहंदी', '2026-12-04', '16:00', 'Agarwal Bhawan', 'C-Scheme', 'Jaipur'),
  fn('Sangeet', 'संगीत', '2026-12-05', '19:00', 'Shagun Gardens', 'Tonk Road', 'Jaipur'),
  fn('Phere', 'फेरे', '2026-12-06', '11:00', 'Shagun Gardens', '', 'Jaipur'),
  fn('Reception', 'स्वागत समारोह', '2026-12-07', '20:00', 'Hotel Rajputana', 'MI Road', 'Jaipur'),
]

const IDENT_KEY = 'cardkholo_mock_identified_at'

export function mockIdentify(req: IdentifyReq): IdentifyRes {
  const user_id = id('u')
  writeJSON(IDENT_KEY, { [user_id]: Date.now() })
  return {
    user_id,
    pair_link: req.role === 'parent' ? `https://t.me/CardKholoBot?start=${user_id}` : null,
  }
}

export function mockPairing(userId: string): PairingRes {
  const seen = readJSON<Record<string, number>>(IDENT_KEY) ?? {}
  // Users identified before this mock existed: start their 15 s now.
  if (!seen[userId]) writeJSON(IDENT_KEY, { ...seen, [userId]: Date.now() })
  const at = seen[userId] ?? Date.now()
  return Date.now() - at >= 15_000 ? { linked: true, child_name: 'Rohan' } : { linked: false, child_name: null }
}

// ---------------- live demo state ----------------
const started = Date.now()
let styleToggle: WarningStyle = 'urgent'
const styleByScan = new Map<string, WarningStyle>()
const packByScan = new Map<string, string>()
const nextStyle = (scanId: string): WarningStyle => {
  styleToggle = styleToggle === 'calm' ? 'urgent' : 'calm'
  styleByScan.set(scanId, styleToggle)
  return styleToggle
}

const packs = {
  pack_core: { enabled: true, fa: [] as number[] },
  pack_wedding_2026: { enabled: true, fa: [] as number[] },
  pack_broad_test: { enabled: true, fa: [] as number[] },
}
type PackName = keyof typeof packs

const changes: FlagChange[] = [
  { time: iso(started - 9 * 60_000), feature: 'pack_broad_test', summary: 'pack_broad_test turned on for canary_20', source: 'Dashboard' },
  { time: iso(started - 15 * 60_000), feature: 'scam_signatures', summary: 'scam_signatures updated: +1 rule (wed-02)', source: 'Dashboard' },
  { time: iso(started - 40 * 60_000), feature: 'strict_mode', summary: 'strict_mode on for segment "parents"', source: 'Dashboard' },
]
const incidents: Incident[] = [
  { id: 'inc_0', pack: 'pack_broad_test', count: 3, status: 'rejected', opened_at: iso(started - 85 * 60_000), closed_at: iso(started - 84 * 60_000) },
]
const alerts = [
  { time: iso(started - 22 * 60_000), parent: 'Mummy', filename: 'Wedding_Invitation.apk' },
]
const exp = {
  calm: { shown: 18, played: 16, completed: 14, opened_anyway: 1 },
  urgent: { shown: 17, played: 13, completed: 9, opened_anyway: 2 },
}

function role(): string {
  return readJSON<{ role?: string }>('cardkholo_user')?.role ?? 'parent'
}
function userName(): string {
  const r = role()
  return r === 'parent' ? 'Papa' : (readJSON<{ name?: string }>('cardkholo_user')?.name ?? 'Guest')
}

export function mockScan(input: { filename?: string; text?: string }): ScanRes {
  const scan_id = id('s')
  const filename = input.filename ?? ''
  const name = filename.toLowerCase()
  const text = (input.text ?? '').toLowerCase()
  const strict = role() === 'parent'

  const danger = (reasons: string[], pack: PackName): ScanRes => {
    packByScan.set(scan_id, pack)
    alerts.unshift({ time: iso(Date.now()), parent: userName(), filename: filename || 'a message with a link' })
    return {
      scan_id, verdict: 'DANGEROUS', reasons, pack_hits: [pack], verified_from: null, audio_b64: null,
      functions: [], ics_url: null, alert_sent: true, warning_style: nextStyle(scan_id),
    }
  }

  // 1. Android app hidden as a card
  if (/\.(apk|xapk|apks)$/.test(name)) {
    return danger([
      'File ends in .apk, not .pdf',
      'Asks to read your messages',
      'Sent from a number not in your contacts',
    ], /(shaadi|wedding|invitation|nimantran)/.test(name) ? 'pack_wedding_2026' : 'pack_core')
  }

  // 2. Over-broad test pack (incident demo): flags any "invitation" file while it's on
  if (packs.pack_broad_test.enabled && /invitation/.test(name)) {
    return danger(['File name matches a new scam rule (broad-01)', 'Ask your family before opening'], 'pack_broad_test')
  }

  // 3. Messages
  const asksInstall = /(download|install).{0,20}(app|apk)/.test(text)
  const shortLink = /(bit\.ly|tinyurl|t\.co|cutt\.ly|is\.gd)\//.test(text)
  const plainHttp = /http:\/\//.test(text)
  if (asksInstall || shortLink || plainHttp) {
    const reasons = [
      ...(asksInstall ? ['Asks you to install an app to see a card'] : []),
      ...(shortLink ? ["Short link hides where it really goes"] : []),
      ...(plainHttp ? ['Link is not secure (http)'] : []),
    ]
    if (strict && asksInstall) return danger(reasons, 'pack_wedding_2026')
    packByScan.set(scan_id, 'pack_wedding_2026')
    return {
      scan_id, verdict: 'SUSPICIOUS', reasons, pack_hits: ['pack_wedding_2026'], verified_from: null, audio_b64: null,
      functions: [], ics_url: null, alert_sent: false, warning_style: nextStyle(scan_id),
    }
  }

  // 4. Real card
  return {
    scan_id, verdict: 'OK', reasons: [], pack_hits: [],
    verified_from: text.includes('cardkholo.app/i/') ? 'Agarwal family' : null,
    audio_b64: null, functions: DEMO_FUNCTIONS, ics_url: `data:text/calendar;charset=utf-8,${encodeURIComponent(buildIcs(COUPLE, DEMO_FUNCTIONS))}`, alert_sent: false,
    couple: COUPLE, host_family: 'Agarwal family',
  }
}

export function mockOpened(): OpenedRes {
  return {
    steps: [
      'Call 1930, the national cybercrime helpline, and report it.',
      'Turn on airplane mode now.',
      'Call your bank. Block your cards and UPI.',
      'Report it online at cybercrime.gov.in.',
      'Remove the app: Settings, Apps, then uninstall.',
    ],
    audio_b64: null,
  }
}

export function mockFeedback(scanId?: string): FeedbackRes {
  const pack = (scanId && packByScan.get(scanId)) as PackName | undefined
  const p = packs[pack ?? 'pack_broad_test'] ?? packs.pack_broad_test
  const now = Date.now()
  p.fa = [...p.fa.filter((t) => now - t < 5 * 60_000), now]
  const name = (pack ?? 'pack_broad_test') as PackName
  if (p.fa.length >= 3 && p.enabled && !incidents.some((i) => i.pack === name && i.status === 'open')) {
    const inc: Incident = { id: id('inc'), pack: name, count: p.fa.length, status: 'open', opened_at: iso(now), closed_at: null }
    incidents.unshift(inc)
    // NudgeBee approval + Flagsmith rollback arrive a few seconds later
    setTimeout(() => {
      p.enabled = false
      inc.status = 'rolled_back'
      inc.closed_at = iso(Date.now())
      changes.unshift({ time: iso(Date.now()), feature: name, summary: `${name} turned off`, source: 'NudgeBee rollback' })
    }, 6000)
  }
  return { ok: true, pack_false_alarms: p.fa.length }
}

export function mockEvent(scanId: string, event: ExperimentEvent): void {
  const v = exp[styleByScan.get(scanId) ?? 'calm']
  if (event === 'warning_shown') v.shown++
  if (event === 'warning_played') v.played++
  if (event === 'warning_completed') v.completed++
}

export function mockStatus(): StatusRes {
  const now = Date.now()
  const rate = (v: { shown: number; completed: number }) => (v.shown ? v.completed / v.shown : 0)
  return {
    packs: (Object.keys(packs) as PackName[]).map((n) => ({
      name: n, enabled: packs[n].enabled, false_alarms_5m: packs[n].fa.filter((t) => now - t < 5 * 60_000).length,
    })),
    incidents: incidents.map((i) => ({ ...i })),
    last_alerts: alerts.slice(0, 6),
    flag_changes: changes.slice(0, 8),
    experiment: {
      flag: 'warning_style',
      variants: (['calm', 'urgent'] as const).map((n) => ({ name: n, ...exp[n], completion_rate: rate(exp[n]) })),
    },
  }
}

export function mockWedding(_req: WeddingReq): WeddingRes {
  return { wedding_id: id('w') }
}

export function mockVoice(): VoiceRes {
  const invite_url = `${window.location.origin}/i/k3P9xQ`
  const invite_text =
    'आदरणीय शर्मा जी,\nअग्रवाल परिवार आपको प्रिया और अर्जुन के विवाह में सादर आमंत्रित करता है।\n\n' +
    'मेहंदी: गुरुवार 4 दिसंबर, शाम 4 बजे\nरिसेप्शन: रविवार 7 दिसंबर, रात 8 बजे\n\n' +
    `निमंत्रण देखें: ${invite_url}`
  return {
    transcript: 'Sharma ji ko Hindi mein invite bhejo, mehendi aur reception ke liye.',
    parsed: { guest: 'Sharma ji', lang: 'hi', functions: ['Mehendi', 'Reception'] },
    invite_text, invite_url,
    wa_url: `https://wa.me/?text=${encodeURIComponent(invite_text)}`,
    audio_b64: null,
  }
}

export function mockInvite(inviteId: string): InviteRes {
  return {
    invite_id: inviteId,
    guest: 'Sharma ji',
    lang: 'hi',
    couple: COUPLE,
    couple_original: 'प्रिया और अर्जुन का विवाह',
    host_family: 'Agarwal family',
    functions: [DEMO_FUNCTIONS[0], DEMO_FUNCTIONS[3]],
    ics_url: null,
    audio_b64: null,
  }
}
