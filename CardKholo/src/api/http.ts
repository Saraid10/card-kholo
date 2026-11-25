import { API_BASE } from '../lib/env'

export type ApiErrorKind = 'timeout' | 'network' | 'http' | 'parse'

export class ApiError extends Error {
  kind: ApiErrorKind
  status?: number
  constructor(kind: ApiErrorKind, message: string, status?: number) {
    super(message)
    this.kind = kind
    this.status = status
  }
}

export const TIMEOUT = { scan: 35_000, default: 15_000, events: 5_000, wake: 60_000 }

// Render's free tier sleeps. Until the first response arrives, a call slower than 4 s
// tells the UI to show "Waking up the server".
let warmed = false
const slowListeners = new Set<(slow: boolean) => void>()
export function onSlowStart(fn: (slow: boolean) => void): () => void {
  slowListeners.add(fn)
  return () => { slowListeners.delete(fn) }
}
const emitSlow = (slow: boolean) => slowListeners.forEach((fn) => fn(slow))

interface Opts {
  method?: 'GET' | 'POST'
  json?: unknown
  form?: FormData
  timeoutMs?: number
}

export async function request<T>(path: string, opts: Opts = {}): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), opts.timeoutMs ?? TIMEOUT.default)
  const slowTimer = warmed ? undefined : setTimeout(() => emitSlow(true), 4000)
  const init: RequestInit = { method: opts.method ?? 'GET', signal: ctrl.signal }
  if (opts.form) {
    init.body = opts.form // browser sets multipart boundary
  } else if (opts.json !== undefined) {
    init.body = JSON.stringify(opts.json)
    init.headers = { 'Content-Type': 'application/json' }
  }

  let res: Response
  try {
    res = await fetch(API_BASE + path, init)
  } catch (e) {
    clearTimeout(timer)
    clearTimeout(slowTimer)
    if ((e as Error).name === 'AbortError') throw new ApiError('timeout', `Timed out: ${path}`)
    throw new ApiError('network', `Network error: ${path}`)
  }
  clearTimeout(timer)
  clearTimeout(slowTimer)
  if (!warmed) {
    warmed = true
    emitSlow(false)
  }

  if (!res.ok) {
    let detail = ''
    try {
      detail = (await res.text()).slice(0, 300)
    } catch {
      /* ignore */
    }
    throw new ApiError('http', `HTTP ${res.status} on ${path} ${detail}`, res.status)
  }
  try {
    return (await res.json()) as T
  } catch {
    throw new ApiError('parse', `Bad JSON from ${path}`)
  }
}
