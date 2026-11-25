// Scan results live in session storage so result / functions / directions / first-hour
// screens survive a refresh. History ("Checked today") is kept in local storage.
import type { ScanRes, VoiceRes, WeddingFunction } from '../api/types'
import { readJSON, writeJSON } from '../lib/storage'

export interface SavedScan {
  res: ScanRes
  label: string // filename or first words of the pasted text
  kind: 'file' | 'text'
  at: number
}

const SCANS_KEY = 'cardkholo_scans'
const RECENT_KEY = 'cardkholo_recent'
const WEDDING_KEY = 'cardkholo_wedding'
const CHILD_KEY = 'cardkholo_child'

/** Full results for this page load only (Checked today rows reopen these until a reload). */
const memory = new Map<string, SavedScan>()
const HOST_KEY = 'cardkholo_host'

function readSession<T>(key: string): T | null {
  try {
    const raw = window.sessionStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : readJSON<T>(key)
  } catch {
    return readJSON<T>(key)
  }
}
function writeSession(key: string, value: unknown) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    writeJSON(key, value)
  }
}

export function saveScan(s: SavedScan): void {
  const all = readSession<Record<string, SavedScan>>(SCANS_KEY) ?? {}
  // audio can be large; keep it for the live screen only
  all[s.res.scan_id] = s
  writeSession(SCANS_KEY, all)
  memory.set(s.res.scan_id, s)
  const recent = getRecent().filter((r) => r.scan_id !== s.res.scan_id)
  recent.unshift({ scan_id: s.res.scan_id, label: s.label.slice(0, 40), verdict: s.res.verdict, time: new Date(s.at).toISOString() })
  writeJSON(RECENT_KEY, recent.slice(0, 5))
}

export function getMemoryScan(id: string): SavedScan | null {
  return memory.get(id) ?? null
}

export function getScan(id: string | undefined): SavedScan | null {
  if (!id) return null
  return readSession<Record<string, SavedScan>>(SCANS_KEY)?.[id] ?? null
}

export function updateFunctions(id: string, fns: WeddingFunction[]): void {
  const all = readSession<Record<string, SavedScan>>(SCANS_KEY) ?? {}
  if (!all[id]) return
  all[id] = { ...all[id], res: { ...all[id].res, functions: fns } }
  writeSession(SCANS_KEY, all)
}

export interface RecentItem {
  scan_id: string
  label: string
  verdict: ScanRes['verdict']
  time: string // ISO
}
export function getRecent(): RecentItem[] {
  const r = readJSON<RecentItem[]>(RECENT_KEY)
  return Array.isArray(r) ? r : []
}

// ---------- saved wedding (/calendar, /directions) ----------
export interface SavedWedding {
  scan_id: string
  functions: WeddingFunction[]
  ics_url: string | null
  saved_at: string
  /** Extra beyond the spec: shown as the screen subtitle. */
  couple?: string | null
}
export function getWedding(): SavedWedding | null {
  const w = readJSON<SavedWedding>(WEDDING_KEY)
  return w && Array.isArray(w.functions) ? w : null
}
export function saveWedding(res: ScanRes, functions: WeddingFunction[]): void {
  writeJSON(WEDDING_KEY, {
    scan_id: res.scan_id, functions, ics_url: res.ics_url ?? null, saved_at: new Date().toISOString(), couple: res.couple ?? null,
  } satisfies SavedWedding)
}

// ---------- linked child ----------
export function getChild(): { child_name: string } | null {
  const c = readJSON<{ child_name?: string }>(CHILD_KEY)
  return c?.child_name ? { child_name: c.child_name } : null
}
export function saveChild(child_name: string): void {
  writeJSON(CHILD_KEY, { child_name })
}

// ---------- host flow ----------
export interface HostDraft {
  wedding_id?: string
  couple: string
  host_family: string
  functions: WeddingFunction[]
  last?: VoiceRes & { guest?: string }
}
export function getHost(): HostDraft | null {
  return readJSON<HostDraft>(HOST_KEY)
}
export function saveHost(h: HostDraft): void {
  writeJSON(HOST_KEY, h)
}
