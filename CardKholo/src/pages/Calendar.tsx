// /calendar: Your functions, read from the saved wedding (cardkholo_wedding).
import { useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import type { WeddingFunction } from '../api'
import { api } from '../api'
import AppShell from '../components/AppShell'
import { ICalPlus, IChevron, IClock, IPin } from '../components/Icons'
import MapEmbed from '../components/MapEmbed'
import { btnClass, Seal } from '../components/ui'
import { fill } from '../i18n/strings'
import { fmtDay, fmtTime, parseDate } from '../lib/format'
import { leaveAround, sortKey } from '../lib/map'
import { getWedding } from '../state/scans'
import { useUser } from '../state/user'

type Item = WeddingFunction & { i: number }
const dayKey = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function Calendar() {
  const { lang, t } = useUser()
  const wedding = getWedding()
  const [sel, setSel] = useState<string | null>(null)
  const refs = useRef<Record<string, HTMLElement | null>>({})

  // Keep the original index: /directions/:index reads the saved array as stored.
  const items: Item[] = useMemo(
    () => (wedding?.functions ?? []).map((f, i) => ({ ...f, i })).sort((a, b) => sortKey(a).localeCompare(sortKey(b))),
    [wedding],
  )

  // Week strip: 7 days from the day before the first function.
  const days = useMemo(() => {
    const first = items.map((f) => parseDate(f.date)).find(Boolean)
    if (!first) return []
    const start = new Date(first)
    start.setDate(start.getDate() - 1)
    return Array.from({ length: 7 }, (_, k) => { const d = new Date(start); d.setDate(start.getDate() + k); return d })
  }, [items])

  if (!wedding || items.length === 0) {
    return (
      <AppShell back="/check" footer={<Link to="/check" className={btnClass('primary', 'lg', 'w-full')}>{t('checkCard')}</Link>}>
        <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center animate-rise">
          <Seal size={60} />
          <h1 className="display-md">{t('calEmptyTitle')}</h1>
          <p className="max-w-[22rem] text-ink-2">{t('calEmptySub')}</p>
        </div>
      </AppShell>
    )
  }

  const today = dayKey(new Date())
  const tomorrow = dayKey(new Date(Date.now() + 86_400_000))
  const nowKey = `${today} ${new Date().toTimeString().slice(0, 5)}`
  const next = items.find((f) => sortKey(f) >= nowKey) ?? items[0]
  const rest = items.filter((f) => f !== next)
  const ics = api.icsUrl(wedding.ics_url)

  const rel = (date?: string) =>
    date === today ? t('today') : date === tomorrow ? t('tomorrow') : fmtDay(date, lang, { weekday: 'short', day: 'numeric', month: 'short' }).replace(',', '')
  const timeOf = (f: WeddingFunction) => fmtTime(f.time, lang) || t('timeNotPrinted')

  function pick(k: string) {
    const on = sel === k ? null : k
    setSel(on)
    const target = on && items.find((f) => f.date === on)
    if (target) refs.current[String(target.i)]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
  const hl = (f: Item) => (sel && f.date === sel ? 'ring-2 ring-wine ring-offset-2 ring-offset-paper' : '')

  return (
    <AppShell
      back={`/result/${wedding.scan_id}`}
      center={wedding.couple ? <span className="font-display italic text-wine">{wedding.couple}</span> : undefined}
      aside={{ eyebrow: t('yourFunctions'), title: <>Mehendi to reception, <span className="accent-gold">in order.</span></>, body: 'Tap a day to find its function. Every venue opens straight into directions.' }}
    >
      <div className="flex flex-col gap-6 animate-rise">
        <h1 className="display-md">{t('yourFunctions')}</h1>

        <div className="no-scrollbar -mx-5 flex gap-2 overflow-x-auto px-5 sm:-mx-6 sm:px-6">
          {days.map((d) => {
            const k = dayKey(d)
            const has = items.some((f) => f.date === k)
            const on = sel === k
            return (
              <button key={k} type="button" disabled={!has} aria-pressed={on} onClick={() => pick(k)}
                className={`flex min-w-[58px] flex-1 flex-col items-center rounded-2xl px-2 py-2.5 transition-colors ${
                  on ? 'bg-maroon text-paper' : has ? 'bg-card ring-1 ring-line hover:ring-ink-3' : 'text-ink-3 opacity-60'
                }`}>
                <span className="text-xs font-medium uppercase tracking-wider">{fmtDay(k, lang, { weekday: 'short' })}</span>
                <span className="font-display text-2xl leading-tight">{d.getDate()}</span>
                <span className={`mt-0.5 h-1.5 w-1.5 rounded-full ${has ? (on ? 'bg-gold-2' : 'bg-wine') : 'bg-transparent'}`} />
              </button>
            )
          })}
        </div>

        {/* Next up */}
        <section ref={(el) => { refs.current[String(next.i)] = el }} className={`maroon-bg relative overflow-hidden rounded-[26px] text-paper shadow-lift transition-shadow ${hl(next)}`}>
          <span className="pointer-events-none absolute inset-2.5 z-10 rounded-[20px] border border-gold/40" aria-hidden="true" />
          <div className="relative p-6 pb-5">
            <div className="eyebrow text-gold-2">{t('nextUp')} · {rel(next.date)}{next.time ? `, ${fmtTime(next.time, lang)}` : ''}</div>
            <div className="mt-2 flex flex-wrap items-baseline gap-x-3">
              <span className="font-display text-[2.2rem] leading-none">{next.name}</span>
              {next.name_original && <span className="text-lg text-paper/70" lang="hi">{next.name_original}</span>}
            </div>
            <div className="mt-3 flex items-center gap-2 text-paper/85"><IPin size={18} /> {[next.venue_name, next.venue_address].filter(Boolean).join(', ')}</div>
            <div className="mt-1 flex items-center gap-2 text-paper/70">
              <IClock size={18} />
              {leaveAround(next.time) ? fill(t('leaveAround'), { time: fmtTime(leaveAround(next.time)!, lang) }) : t('timeNotPrinted')}
            </div>
          </div>
          <Link to={`/directions/${next.i}`} aria-label={`${t('directions')}: ${next.venue_name ?? ''}`} className="relative mx-4 block overflow-hidden rounded-[18px] ring-1 ring-white/15">
            <MapEmbed fn={next} interactive={false} className="h-36" />
          </Link>
          <div className="relative p-6 pt-4">
            <Link to={`/directions/${next.i}`} className={btnClass('gold', 'md')}>{t('directions')} <IChevron size={18} /></Link>
          </div>
        </section>

        {/* The rest */}
        <ol className="stagger relative flex flex-col gap-3 pl-6 before:absolute before:bottom-3 before:left-[7px] before:top-3 before:w-px before:bg-gold/60">
          {rest.map((f) => (
            <li key={f.i} ref={(el) => { refs.current[String(f.i)] = el }} className="relative">
              <span className="absolute -left-6 top-5 h-[15px] w-[15px] rounded-full border-2 border-gold bg-paper" aria-hidden="true" />
              <div className={`card flex items-center gap-4 p-4 transition-shadow ${hl(f)}`}>
                <div className={`w-[5.2rem] shrink-0 font-display leading-tight text-wine ${f.time ? 'whitespace-nowrap text-[1.15rem]' : 'text-[0.85rem] italic'}`}>{timeOf(f)}</div>
                <div className="min-w-0 flex-1">
                  <div className="text-[1.08rem] font-semibold">{f.name}</div>
                  <div className="truncate text-[0.92rem] text-ink-2">{fmtDay(f.date, lang, { weekday: 'short', day: 'numeric' })}, {f.venue_name}</div>
                </div>
                <Link to={`/directions/${f.i}`} aria-label={`${t('directions')}: ${f.venue_name ?? ''}`} className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-paper-2 text-ink hover:bg-blush/60">
                  <IPin size={20} />
                </Link>
              </div>
            </li>
          ))}
        </ol>

        {ics && (
          <a href={ics} download="wedding.ics" className="inline-flex items-center justify-center gap-2 self-center text-[0.98rem] font-medium text-wine underline decoration-gold decoration-2 underline-offset-4">
            <ICalPlus size={18} /> {t('remindLink')}
          </a>
        )}
      </div>
    </AppShell>
  )
}
