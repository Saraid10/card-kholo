// Client-side Google Calendar + Maps link builders (used by mocks and the Edit flow).

export interface CalInput {
  title: string
  date: string // YYYY-MM-DD
  time: string // HH:MM or ""
  location: string
  details?: string
}

const pad = (n: number) => String(n).padStart(2, '0')

function addDays(date: string, days: number): string {
  const [y, m, d] = date.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d + days))
  return `${dt.getUTCFullYear()}${pad(dt.getUTCMonth() + 1)}${pad(dt.getUTCDate())}`
}

/** START/END for Google's `dates=` param. Timed: 3 h default in local wall time (ctz=Asia/Kolkata). */
export function gcalDates(date: string, time: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null
  const ymd = date.replace(/-/g, '')
  if (!/^\d{1,2}:\d{2}$/.test(time)) return `${ymd}/${addDays(date, 1)}`
  const [h, min] = time.split(':').map(Number)
  const endH = h + 3
  const endDate = endH >= 24 ? addDays(date, 1) : ymd
  return `${ymd}T${pad(h)}${pad(min)}00/${endDate}T${pad(endH % 24)}${pad(min)}00`
}

export function buildGcalUrl(c: CalInput): string | null {
  const dates = gcalDates(c.date, c.time)
  if (!dates) return null
  const p = new URLSearchParams({ action: 'TEMPLATE', text: c.title, dates, ctz: 'Asia/Kolkata' })
  if (c.location) p.set('location', c.location)
  if (c.details) p.set('details', c.details)
  return `https://calendar.google.com/calendar/render?${p.toString()}`
}

export function buildMapsUrl(query: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`
}
