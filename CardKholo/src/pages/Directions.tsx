// /directions/:index: venue map (top 60%) + bottom sheet. Reads the saved wedding.
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { IArrowLeft, IAuto, ICar, IPin, ISend, ITrain } from '../components/Icons'
import MapEmbed from '../components/MapEmbed'
import { btnClass } from '../components/ui'
import { fill, type StringKey } from '../i18n/strings'
import { fmtDay, fmtTime } from '../lib/format'
import { dirUrl, leaveAround, type TravelMode } from '../lib/map'
import { getWedding } from '../state/scans'
import { useUser } from '../state/user'

const MODES: { k: StringKey; mode: TravelMode; icon: typeof ICar }[] = [
  { k: 'car', mode: 'driving', icon: ICar },
  { k: 'bike', mode: 'two-wheeler', icon: IAuto },
  { k: 'metro', mode: 'transit', icon: ITrain },
]

export default function Directions() {
  const { index = '0' } = useParams()
  const nav = useNavigate()
  const { lang, t } = useUser()
  const [mode, setMode] = useState<TravelMode>('driving')
  const fn = getWedding()?.functions?.[Number(index)]

  if (!fn) {
    return (
      <div className="paper-bg grid min-h-dvh place-items-center p-6 text-center">
        <div className="flex flex-col items-center gap-4">
          <h1 className="display-md">{t('calEmptyTitle')}</h1>
          <Link to="/calendar" className={btnClass('primary', 'md')}>{t('yourFunctions')}</Link>
        </div>
      </div>
    )
  }

  const maps = dirUrl(fn, mode)
  const date = fmtDay(fn.date, lang, { weekday: 'short', day: 'numeric', month: 'short' }).replace(',', '')
  const start = fmtTime(fn.time, lang)
  const leave = leaveAround(fn.time)
  const share = `https://wa.me/?text=${encodeURIComponent(fill(t('shareMsg'), {
    name: fn.name ?? '', date, time: start || t('timeNotPrinted'), venue: [fn.venue_name, fn.venue_address, fn.city].filter(Boolean).join(', '), url: maps,
  }))}`

  return (
    <div className="paper-bg relative flex min-h-dvh flex-col">
      <div className="relative h-[60dvh] min-h-[300px] w-full">
        <MapEmbed fn={fn} className="h-full w-full" />
        <button type="button" aria-label={t('back')} onClick={() => nav(-1)}
          className="absolute left-4 top-16 z-10 grid h-12 w-12 place-items-center rounded-full bg-card text-ink shadow-lift ring-1 ring-line hover:bg-paper-2 sm:left-6 sm:top-16">
          <IArrowLeft size={20} />
        </button>
      </div>

      <section className="relative z-10 -mt-7 flex flex-1 flex-col rounded-t-[28px] bg-paper px-5 pb-4 pt-2.5 shadow-[0_-12px_30px_-18px_rgb(60_30_20/.35)] sm:px-6">
        <div className="mx-auto flex w-full max-w-[560px] flex-1 flex-col gap-3 animate-rise">
          <span className="mx-auto h-1.5 w-11 rounded-full bg-line" aria-hidden="true" />

          <div>
            <div className="eyebrow text-wine">{fn.name}{date ? `, ${date}` : ''}{start ? ` · ${start}` : ''}</div>
            <h1 className="mt-1 font-display text-[1.6rem] leading-tight">{fn.venue_name}</h1>
            <p className="mt-0.5 flex items-start gap-2 text-[0.95rem] text-ink-2"><IPin size={17} className="mt-1 shrink-0" /> {[fn.venue_address, fn.city].filter(Boolean).join(', ')}</p>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Stat label={t('starts')} value={start || '—'} />
            <Stat label={t('leaveBy')} value={leave ? fmtTime(leave, lang) : '—'} />
            <Stat label={t('dateLabel')} value={fmtDay(fn.date, lang, { day: 'numeric', month: 'short' }) || '—'} />
          </div>

          <div role="radiogroup" aria-label="Travel mode" className="grid grid-cols-3 gap-1 rounded-full bg-paper-2 p-1">
            {MODES.map(({ k, mode: m, icon: Icon }) => (
              <button key={m} type="button" role="radio" aria-checked={mode === m} onClick={() => setMode(m)}
                className={`flex items-center justify-center gap-2 rounded-full py-2 text-[0.95rem] font-medium transition-colors ${mode === m ? 'bg-ink text-paper' : 'text-ink-2 hover:text-ink'}`}>
                <Icon size={19} /> {t(k)}
              </button>
            ))}
          </div>

          <div className="mt-auto flex items-center gap-3 pt-1 safe-bottom">
            <a href={maps} target="_blank" rel="noreferrer" className={btnClass('primary', 'lg', 'flex-1')}>{t('startMaps')}</a>
            <a href={share} target="_blank" rel="noreferrer" aria-label={t('share')} title={t('share')}
              className="grid h-[58px] w-[58px] shrink-0 place-items-center rounded-full bg-card text-ink ring-[1.5px] ring-ink/80 hover:bg-paper-2">
              <ISend size={21} />
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card px-2 py-2 text-center">
      <div className="truncate text-[0.7rem] font-medium uppercase tracking-wider text-ink-3">{label}</div>
      <div className="mt-0.5 whitespace-nowrap font-display text-[1.1rem] leading-tight text-ink">{value}</div>
    </div>
  )
}
