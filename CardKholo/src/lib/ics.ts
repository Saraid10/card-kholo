// Client-side .ics so "Add all to calendar" works even without the backend's ics_url.
import type { WeddingFunction } from '../api/types'

const pad = (n: number) => String(n).padStart(2, '0')
const esc = (s: string) => s.replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/([,;])/g, '\\$1')

function stamp(date: string, time: string, addHours = 0): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null
  const [y, m, d] = date.split('-').map(Number)
  if (!/^\d{1,2}:\d{2}$/.test(time)) return null
  const [h, min] = time.split(':').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d, h + addHours, min))
  return `${dt.getUTCFullYear()}${pad(dt.getUTCMonth() + 1)}${pad(dt.getUTCDate())}T${pad(dt.getUTCHours())}${pad(dt.getUTCMinutes())}00`
}

export function buildIcs(title: string, fns: WeddingFunction[]): string {
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Card Kholo//EN', 'CALSCALE:GREGORIAN']
  fns.forEach((f, i) => {
    if (!f.date) return
    const loc = [f.venue_name, f.venue_address, f.city].filter(Boolean).join(', ')
    const start = stamp(f.date, f.time ?? '')
    const end = stamp(f.date, f.time ?? '', 3)
    lines.push('BEGIN:VEVENT', `UID:ck-${Date.now()}-${i}@cardkholo.app`, `DTSTAMP:${stamp(new Date().toISOString().slice(0, 10), '00:00')}Z`)
    if (start && end) {
      lines.push(`DTSTART;TZID=Asia/Kolkata:${start}`, `DTEND;TZID=Asia/Kolkata:${end}`)
    } else {
      lines.push(`DTSTART;VALUE=DATE:${f.date.replace(/-/g, '')}`)
    }
    lines.push(`SUMMARY:${esc(`${f.name ?? 'Function'}: ${title}`)}`)
    if (loc) lines.push(`LOCATION:${esc(loc)}`)
    if (f.maps_url) lines.push(`URL:${f.maps_url}`)
    lines.push('BEGIN:VALARM', 'TRIGGER:-PT1H', 'ACTION:DISPLAY', `DESCRIPTION:${esc(f.name ?? 'Function')}`, 'END:VALARM', 'END:VEVENT')
  })
  lines.push('END:VCALENDAR')
  return lines.join('\r\n')
}

export function downloadIcs(title: string, fns: WeddingFunction[]): void {
  const blob = new Blob([buildIcs(title, fns)], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${title.replace(/[^\w]+/g, '_') || 'wedding'}.ics`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
