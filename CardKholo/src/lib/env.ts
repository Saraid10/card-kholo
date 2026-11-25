const raw = import.meta.env

export const API_BASE: string = (raw.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '')

// Mocks are on when explicitly "true", or when no backend URL is set (so the app never calls a blank host).
export const USE_MOCKS: boolean =
  raw.VITE_USE_MOCKS === 'true' || (raw.VITE_USE_MOCKS !== 'false' && API_BASE === '')

export const BOT_USERNAME: string = (raw.VITE_TELEGRAM_BOT_USERNAME ?? '').replace(/^@/, '')

/** Prefix relative paths (e.g. ics_url "/api/ics/123") with the backend URL. */
export function resolveUrl(path: string | null | undefined): string | null {
  if (!path) return null
  if (/^(https?:\/\/|data:|blob:)/i.test(path)) return path
  return API_BASE + (path.startsWith('/') ? path : '/' + path)
}
