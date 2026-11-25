import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Lang, WeddingFunction } from '../api/types'
import { fill } from '../i18n/strings'
import { buildGcalUrl, buildMapsUrl } from '../lib/calendar'
import { fmtDay, fmtTime } from '../lib/format'
import { useUser } from '../state/user'
import { ICalPlus, IEdit } from './Icons'
import { Button } from './ui'

interface Props {
  functions: WeddingFunction[]
  title: string
  /** Where tapping the venue goes. Defaults to the Google Maps link. */
  directionsHref?: (i: number) => string
  /** Runs before navigating to directionsHref (e.g. save the wedding it reads). */
  onVenue?: (i: number) => void
  onChange?: (fns: WeddingFunction[]) => void
  dark?: boolean
}

export default function FunctionList({ functions, title, directionsHref, onVenue, onChange, dark = false }: Props) {
  const { lang, t } = useUser()
  const [editing, setEditing] = useState<number | null>(null)

  return (
    <ol className={`stagger overflow-hidden rounded-[22px] ${dark ? 'bg-white/[.06] ring-1 ring-white/15' : 'card'}`}>
      {functions.map((f, i) => (
        <li key={i} className={`border-b last:border-0 ${dark ? 'border-white/10' : 'border-line/80'}`}>
          {editing === i ? (
            <EditRow
              fn={f}
              title={title}
              onCancel={() => setEditing(null)}
              onSave={(nf) => {
                const next = functions.map((x, j) => (j === i ? nf : x))
                onChange?.(next)
                setEditing(null)
              }}
            />
          ) : (
            <Row fn={f} lang={lang} dark={dark}
              venueHref={directionsHref?.(i)}
              onVenue={() => onVenue?.(i)}
              addLabel={fill(t('addToCal'), { name: f.name ?? '' })}
              editLabel={onChange ? t('edit') : undefined}
              onEdit={() => setEditing(i)} />
          )}
        </li>
      ))}
    </ol>
  )
}

function Row({ fn, lang, dark, venueHref, onVenue, addLabel, editLabel, onEdit }: {
  fn: WeddingFunction; lang: Lang; dark: boolean; venueHref?: string; onVenue?: () => void; addLabel: string; editLabel?: string; onEdit: () => void
}) {
  const month = fmtDay(fn.date, lang, { month: 'short' })
  const day = fmtDay(fn.date, lang, { day: 'numeric' })
  const wd = fmtDay(fn.date, lang, { weekday: 'short' })
  const time = fmtTime(fn.time, lang)
  const venue = [fn.venue_name, fn.venue_address].filter(Boolean).join(', ')
  const mapsHref = fn.maps_url || buildMapsUrl([fn.venue_name, fn.venue_address, fn.city].filter(Boolean).join(' '))
  const muted = dark ? 'text-paper/65' : 'text-ink-3'

  return (
    <div className="flex items-stretch gap-4 px-4 py-4 sm:px-5">
      <div className={`flex w-14 shrink-0 flex-col items-center justify-center rounded-2xl py-2 ${dark ? 'bg-white/10' : 'bg-paper-2'}`}>
        <span className={`text-[0.72rem] font-semibold uppercase tracking-wider ${dark ? 'text-gold-2' : 'text-wine'}`}>{month}</span>
        <span className="font-display text-[1.6rem] leading-none">{day || '?'}</span>
        <span className={`text-[0.72rem] ${muted}`}>{wd}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-[1.12rem] font-semibold">{fn.name || 'Function'}</span>
          {fn.name_original && fn.name_original !== fn.name && <span className={`text-[0.95rem] ${muted}`} lang="hi">{fn.name_original}</span>}
        </div>
        <div className={`text-[0.95rem] ${dark ? 'text-paper/85' : 'text-ink-2'}`}>
          {time && <span className="font-medium">{time}</span>}
          {time && venue && ', '}
          {venue && (venueHref ? (
            <Link to={venueHref} onClick={onVenue} className="underline decoration-gold decoration-2 underline-offset-[3px]">{venue}</Link>
          ) : (
            <a href={mapsHref} target="_blank" rel="noreferrer" className="underline decoration-gold decoration-2 underline-offset-[3px]">{venue}</a>
          ))}
        </div>
        {editLabel && (
          <button type="button" onClick={onEdit} className={`mt-1 inline-flex items-center gap-1 text-sm font-medium ${muted} hover:text-wine`}>
            <IEdit size={14} /> {editLabel}
          </button>
        )}
      </div>
      {fn.gcal_url && (
        <a href={fn.gcal_url} target="_blank" rel="noreferrer" aria-label={addLabel} title={addLabel}
          className={`grid h-12 w-12 shrink-0 place-items-center self-center rounded-full transition-colors ${dark ? 'bg-paper text-maroon hover:bg-white' : 'bg-ink text-paper hover:bg-maroon'}`}>
          <ICalPlus size={21} />
        </a>
      )}
    </div>
  )
}

function EditRow({ fn, title, onSave, onCancel }: { fn: WeddingFunction; title: string; onSave: (f: WeddingFunction) => void; onCancel: () => void }) {
  const { t } = useUser()
  const [date, setDate] = useState(fn.date ?? '')
  const [time, setTime] = useState(fn.time ?? '')
  const [venue, setVenue] = useState(fn.venue_name ?? '')

  function save() {
    const location = [venue, fn.venue_address, fn.city].filter(Boolean).join(', ')
    onSave({
      ...fn, date, time, venue_name: venue,
      gcal_url: buildGcalUrl({ title: `${fn.name}: ${title}`, date, time, location }) ?? fn.gcal_url,
      maps_url: buildMapsUrl([venue, fn.venue_address, fn.city].filter(Boolean).join(' ')),
    })
  }

  return (
    <div className="flex flex-col gap-3 bg-paper-2/60 p-4 text-ink sm:p-5">
      <div className="font-semibold">{fn.name}</div>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-sm text-ink-2">{t('date')}<input type="date" className="field mt-1" value={date} onChange={(e) => setDate(e.target.value)} /></label>
        <label className="text-sm text-ink-2">{t('time')}<input type="time" className="field mt-1" value={time} onChange={(e) => setTime(e.target.value)} /></label>
      </div>
      <label className="text-sm text-ink-2">{t('venue')}<input className="field mt-1" value={venue} onChange={(e) => setVenue(e.target.value)} /></label>
      <div className="flex gap-2">
        <Button size="md" onClick={save} className="flex-1">{t('save')}</Button>
        <Button size="md" variant="ghost" onClick={onCancel}>{t('cancel')}</Button>
      </div>
    </div>
  )
}
