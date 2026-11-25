// Venue → Google Maps URLs (no API key) and "leave around" time.
import type { WeddingFunction } from '../api/types'

export type TravelMode = 'driving' | 'two-wheeler' | 'transit'

/** "venue_name, venue_address, city", skipping empty parts. */
export function venueText(f: WeddingFunction): string {
  return [f.venue_name, f.venue_address, f.city].filter((x) => x && x.trim()).join(', ')
}

export function embedUrl(f: WeddingFunction): string {
  return `https://maps.google.com/maps?q=${encodeURIComponent(venueText(f))}&z=15&output=embed`
}

export function dirUrl(f: WeddingFunction, mode: TravelMode): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(venueText(f))}&travelmode=${mode}`
}

/** Start time minus 45 minutes as "HH:MM", or null when no time is printed. */
export function leaveAround(time?: string): string | null {
  if (!time || !/^\d{1,2}:\d{2}$/.test(time)) return null
  const [h, m] = time.split(':').map(Number)
  const t = (h * 60 + m - 45 + 24 * 60) % (24 * 60)
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`
}

/** Sort key: date, then time; a function with no time goes last on its day. */
export function sortKey(f: WeddingFunction): string {
  const time = f.time && /^\d{1,2}:\d{2}$/.test(f.time) ? f.time.padStart(5, '0') : '99:99'
  return `${f.date ?? '9999-99-99'} ${time}`
}
