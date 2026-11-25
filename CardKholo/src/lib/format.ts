import type { Lang } from '../api/types'

const LOCALE: Record<Lang, string> = { en: 'en-IN', hi: 'hi-IN', kn: 'kn-IN' }

export function parseDate(date?: string): Date | null {
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null
  const [y, m, d] = date.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function fmtTime(time: string | undefined, lang: Lang): string {
  if (!time || !/^\d{1,2}:\d{2}$/.test(time)) return ''
  const [h, m] = time.split(':').map(Number)
  return new Date(2000, 0, 1, h, m).toLocaleTimeString(LOCALE[lang], { hour: 'numeric', minute: '2-digit' })
}

export function fmtDay(date: string | undefined, lang: Lang, opts: Intl.DateTimeFormatOptions): string {
  const d = parseDate(date)
  return d ? d.toLocaleDateString(LOCALE[lang], opts) : ''
}

export function fmtClock(isoStr?: string): string {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (Number.isNaN(d.getTime())) return isoStr
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function fmtHM(isoStr?: string): string {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (Number.isNaN(d.getTime())) return isoStr
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

export const speechLang: Record<Lang, string> = { en: 'en-IN', hi: 'hi-IN', kn: 'kn-IN' }
