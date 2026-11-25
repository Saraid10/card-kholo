// Operator / projector screen. Polls /api/status every 3 s.
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type StatusRes } from '../api'
import { Dot, Seal } from '../components/ui'
import { USE_MOCKS } from '../lib/env'
import { fmtClock, fmtHM } from '../lib/format'

export default function ControlRoom() {
  const [s, setS] = useState<StatusRes | null>(null)
  const [stale, setStale] = useState(false)
  const [fresh, setFresh] = useState<string | null>(null) // newest flag change, highlighted for 5 s
  const lastKey = useRef<string | null | undefined>(undefined)
  const freshTimer = useRef<number | undefined>(undefined)

  useEffect(() => {
    let live = true
    const load = () => api.status().then((r) => { if (live) { setS(r); setStale(false) } }).catch(() => live && setStale(true))
    load()
    const id = window.setInterval(load, 3000)
    return () => { live = false; window.clearInterval(id) }
  }, [])

  useEffect(() => {
    const c = s?.flag_changes?.[0]
    if (!s) return
    const key = c ? `${c.time}|${c.feature}|${c.summary}` : null
    const first = lastKey.current === undefined
    if (key === lastKey.current) return
    lastKey.current = key
    if (first || !key) return
    setFresh(key)
    window.clearTimeout(freshTimer.current)
    freshTimer.current = window.setTimeout(() => setFresh(null), 5000)
  }, [s])
  useEffect(() => () => window.clearTimeout(freshTimer.current), [])

  const packs = s?.packs ?? []
  const incidents = s?.incidents ?? []
  const openInc = incidents.find((i) => i.status === 'open')
  const variants = s?.experiment?.variants ?? []
  const best = variants.reduce<number>((m, v) => Math.max(m, v.completion_rate ?? 0), 0)
  // Call a leader only once every variant has been shown at least 5 times.
  const enoughData = variants.length > 1 && variants.every((v) => (v.shown ?? 0) >= 5)

  return (
    <div className="min-h-dvh bg-night text-paper">
      <header className="border-b border-white/10">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-10">
          <div className="flex items-center gap-4">
            <Link to="/" aria-label="Card Kholo home"><Seal size={40} tone="gold" /></Link>
            <h1 className="font-display text-[2rem] leading-none">Control <span className="italic text-gold-2">room</span></h1>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className={`inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 ${stale ? 'bg-stop/20 text-[#d9a39b]' : 'bg-safe/25 text-[#b7cbb9]'}`}>
              <Dot tone={stale ? 'stop' : 'safe'} pulse={!stale} /> {stale ? 'Reconnecting' : 'Live'}
            </span>
            <span className="rounded-full bg-white/10 px-3.5 py-1.5 text-paper/75">{USE_MOCKS ? 'Demo data' : 'Development'}</span>
          </div>
        </div>
      </header>

      {openInc && (
        <div className="border-b border-check/40 bg-check/20">
          <div className="mx-auto flex max-w-[1440px] items-center gap-3 px-5 py-3 text-[1.05rem] sm:px-10">
            <Dot tone="gold" pulse /> <b>Incident open:</b> <span className="font-mono">{openInc.pack}</span> flagged {openInc.count} real invites. Waiting for approval in NudgeBee…
          </div>
        </div>
      )}

      <main className="mx-auto grid max-w-[1440px] gap-5 px-5 py-8 sm:px-10 lg:grid-cols-12">
        <Panel title="Scam rule packs" className="lg:col-span-5">
          <ul className="divide-y divide-white/10">
            {packs.map((p) => {
              const fa = p.false_alarms_5m ?? 0
              return (
                <li key={p.name} className={`flex items-center justify-between gap-4 py-4 ${fa >= 3 ? '-mx-3 rounded-2xl bg-stop/25 px-3 ring-1 ring-stop/50' : ''}`}>
                  <div>
                    <div className="font-mono text-[1.1rem]">
                      {p.name}
                      {p.name === 'pack_broad_test' && <span className="ml-2 rounded-full bg-gold/25 px-2 py-0.5 align-middle font-sans text-xs font-semibold text-gold-2">canary 20%</span>}
                    </div>
                    <div className={`text-sm ${fa >= 3 ? 'text-[#d9a39b]' : fa > 0 ? 'text-gold-2' : 'text-paper/55'}`}>
                      {fa} false alarm{fa === 1 ? '' : 's'} in 5 min
                    </div>
                  </div>
                  <span className={`rounded-full px-4 py-1.5 text-sm font-semibold ${p.enabled ? 'bg-safe text-paper' : 'bg-white/10 text-paper/60'}`}>{p.enabled ? 'On' : 'Off'}</span>
                </li>
              )
            })}
            {!packs.length && <Empty />}
          </ul>
        </Panel>

        <Panel title="Live flag changes" className="lg:col-span-7">
          <ul className="space-y-3">
            {(s?.flag_changes ?? []).map((c, i) => (
              <li key={`${c.time}-${i}`} className={`grid grid-cols-[6.5rem_1fr] gap-3 rounded-2xl px-4 py-3 transition-colors duration-700 ${i === 0 && fresh === `${c.time}|${c.feature}|${c.summary}` ? 'bg-gold/25 ring-2 ring-gold-2' : 'bg-white/[.04]'}`}>
                <span className="font-mono text-sm text-paper/55">{fmtClock(c.time)}</span>
                <div>
                  <div className={`text-xs font-semibold uppercase tracking-wider ${/nudgebee/i.test(c.source ?? '') ? 'text-gold-2' : 'text-paper/55'}`}>{c.source}</div>
                  <div className="text-[1.02rem]">{c.summary}</div>
                </div>
              </li>
            ))}
            {!s?.flag_changes?.length && <Empty />}
          </ul>
        </Panel>

        <Panel title="Incidents" className="lg:col-span-5">
          <ul className="space-y-3">
            {incidents.map((inc, i) => {
              const tone = inc.status === 'rolled_back' ? 'bg-safe text-paper' : inc.status === 'open' ? 'bg-check text-paper' : 'bg-white/10 text-paper/70'
              const label = inc.status === 'rolled_back' ? 'Rolled back' : inc.status === 'open' ? 'Open' : inc.status === 'rejected' ? 'Rejected' : inc.status
              return (
                <li key={inc.id ?? i} className="flex items-start justify-between gap-3 rounded-2xl bg-white/[.04] p-4">
                  <div>
                    <div className="text-[1.02rem]"><span className="font-mono">{inc.pack}</span> flagged {inc.count} real invites</div>
                    <div className="text-sm text-paper/55">Opened {fmtHM(inc.opened_at)}{inc.closed_at ? `, closed ${fmtHM(inc.closed_at)}` : ''}</div>
                  </div>
                  <span className={`shrink-0 rounded-full px-3 py-1 text-sm font-semibold ${tone}`}>{label}</span>
                </li>
              )
            })}
            {!incidents.length && <Empty />}
          </ul>
        </Panel>

        <Panel title="Family alerts sent" className="lg:col-span-3">
          <ul className="space-y-3">
            {(s?.last_alerts ?? []).map((a, i) => (
              <li key={i} className="rounded-2xl bg-stop/15 p-4 ring-1 ring-stop/30">
                <div className="font-mono text-sm text-paper/55">{fmtHM(a.time)}</div>
                {a.type === 'rollback'
                  ? <div>Rollback notice sent: <span className="font-mono text-sm text-gold-2">{a.pack}</span></div>
                  : <div>Family alerted on Telegram{a.verdict ? <span className="font-mono text-sm text-[#d9a39b]"> ({a.verdict})</span> : null}</div>}
              </li>
            ))}
            {!s?.last_alerts?.length && <Empty />}
          </ul>
        </Panel>

        <Panel title={`Experiment: ${s?.experiment?.flag ?? 'warning_style'}`} className="lg:col-span-4">
          <p className="mb-4 text-sm text-paper/60">Who listened to the whole warning</p>
          <div className="space-y-5">
            {variants.map((v) => {
              const pct = Math.round((v.completion_rate ?? 0) * 100)
              const lead = enoughData && (v.completion_rate ?? 0) === best && best > 0
              return (
                <div key={v.name}>
                  <div className="flex items-baseline justify-between">
                    <span className="text-lg capitalize">{v.name}</span>
                    <span className="font-display text-[2.2rem] leading-none">{pct}%</span>
                  </div>
                  <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-white/10">
                    <div className={`h-full rounded-full ${lead ? 'bg-gold-2' : 'bg-paper/40'}`} style={{ width: `${pct}%` }} />
                  </div>
                  <div className="mt-1 text-sm text-paper/55">{v.completed} of {v.shown}{lead ? '. Leading' : ''}</div>
                </div>
              )
            })}
            {!variants.length && <Empty />}
          </div>
        </Panel>
      </main>
    </div>
  )
}

function Panel({ title, className = '', children }: { title: string; className?: string; children: React.ReactNode }) {
  return (
    <section className={`rounded-[26px] bg-night-2 p-6 ring-1 ring-white/10 ${className}`}>
      <h2 className="mb-4 font-display text-[1.5rem] text-paper">{title}</h2>
      {children}
    </section>
  )
}

const Empty = () => <li className="list-none py-3 text-paper/45">Nothing yet</li>
