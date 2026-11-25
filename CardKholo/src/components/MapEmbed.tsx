// Google Maps embed (no API key). If it hasn't loaded in 6 s, a placeholder with a pin
// and the venue name takes its place.
import { useEffect, useState } from 'react'
import type { WeddingFunction } from '../api/types'
import { embedUrl } from '../lib/map'
import { IPin } from './Icons'

/** Muted to sit on the paper theme. The spec's dark-theme filter would be:
 *  'invert(90%) hue-rotate(180deg) saturate(0.6)'. */
export const MAP_FILTER = 'saturate(0.6) sepia(0.12)'

export default function MapEmbed({ fn, className = '', interactive = true }: { fn: WeddingFunction; className?: string; interactive?: boolean }) {
  const [loaded, setLoaded] = useState(false)
  const [timedOut, setTimedOut] = useState(false)

  useEffect(() => {
    const id = window.setTimeout(() => setTimedOut(true), 6000)
    return () => window.clearTimeout(id)
  }, [])

  const fallback = timedOut && !loaded

  return (
    <div className={`relative overflow-hidden bg-paper-2 ${className}`}>
      {!fallback && (
        <iframe
          title={`Map of ${fn.venue_name ?? 'the venue'}`}
          src={embedUrl(fn)}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          onLoad={() => setLoaded(true)}
          className={`absolute inset-0 h-full w-full border-0 transition-opacity duration-500 ${loaded ? 'opacity-100' : 'opacity-0'} ${interactive ? '' : 'pointer-events-none'}`}
          style={{ filter: MAP_FILTER }}
          tabIndex={interactive ? 0 : -1}
        />
      )}
      {!loaded && (
        <div className="maroon-bg absolute inset-0 grid place-items-center text-paper">
          <div className="flex flex-col items-center gap-2 px-6 text-center">
            <span className={`grid h-12 w-12 place-items-center rounded-full bg-white/10 text-gold-2 ${fallback ? '' : 'animate-pulse'}`}><IPin size={24} /></span>
            <span className="font-display text-xl leading-tight">{fn.venue_name}</span>
            {fallback && <span className="text-sm text-paper/70">{[fn.venue_address, fn.city].filter(Boolean).join(', ')}</span>}
          </div>
        </div>
      )}
    </div>
  )
}
