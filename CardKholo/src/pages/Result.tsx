import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, type Lang, type WeddingFunction } from '../api'
import AppShell from '../components/AppShell'
import FunctionList from '../components/FunctionList'
import { IAlert, ICheck, IDownload, ITelegram, IWhatsApp, IX } from '../components/Icons'
import { HearButton, WarningPlayer } from '../components/Voice'
import { btnClass, Button, Exhibit, Pill, Stamp } from '../components/ui'
import { fill, LANG_NAMES, warningText } from '../i18n/strings'
import { fmtDay, fmtTime } from '../lib/format'
import { getChild, getScan, saveWedding, updateFunctions, type SavedScan } from '../state/scans'
import { useUser } from '../state/user'
import NotFound from './NotFound'

export default function Result() {
  const { scanId } = useParams()
  const saved = getScan(scanId)
  const { t } = useUser()
  if (!saved) return <NotFound message={t('scanMissing')} />
  const v = saved.res.verdict
  if (v === 'OK') return <SafeResult saved={saved} />
  if (v === 'SUSPICIOUS') return <CheckResult saved={saved} />
  return <StopResult saved={saved} />
}

/* ======================= SAFE ======================= */

function SafeResult({ saved }: { saved: SavedScan }) {
  const { lang, t } = useUser()
  const nav = useNavigate()
  const res = saved.res
  const [fns, setFns] = useState<WeddingFunction[]>(res.functions ?? [])
  const couple = res.couple || 'The wedding'
  const n = fns.length
  const summary = useMemo(() => spokenSummary(couple, fns, lang), [couple, fns, lang])
  const toCalendar = () => { saveWedding(res, fns); nav('/calendar') }

  return (
    <AppShell
      back="/check"
      center={<span className="font-mono text-[0.85rem]">{saved.label}</span>}
      aside={{
        eyebrow: 'Real card',
        title: <>Every function, <span className="accent-gold">one tap</span> from your calendar.</>,
        body: 'Sarvam read the card and pulled out each function with its date, time and venue. If anything is misread, edit the row.',
        extra: (
          <ul className="mt-8 space-y-2.5">
            {(['checked1', 'checked2', 'checked3'] as const).map((k) => (
              <li key={k} className="flex items-center gap-3 text-paper/85">
                <span className="grid h-7 w-7 place-items-center rounded-full bg-safe text-paper"><ICheck size={15} strokeWidth={3} /></span>{t(k)}
              </li>
            ))}
          </ul>
        ),
      }}
      footer={
        n > 0 ? (
          <>
            <Button onClick={toCalendar} className="w-full"><IDownload size={20} /> {fill(t('addAll'), { n })}</Button>
            <Button variant="outline" size="md" onClick={toCalendar} className="w-full">{t('seeFunctions')}</Button>
          </>
        ) : (
          <Link to="/check" className={btnClass('primary', 'lg', 'w-full')}>{t('checkAnother')}</Link>
        )
      }
    >
      <div className="flex flex-col gap-5 animate-rise">
        <Exhibit label={saved.label} stamp={<Stamp kind="SAFE" label={t('SAFE')} size="md" />} />

        <div>
          <p className="font-display text-[1.75rem] leading-tight">
            <span className="italic text-wine">{couple}</span>
            {res.host_family && <span className="text-ink">, {fill(t('safeFrom'), { family: res.host_family })}</span>}
          </p>
          <p className="mt-1 text-lg text-ink-2">{n > 0 ? fill(t('safeLine'), { n }) : t('noFunctions')}</p>
          {res.verified_from && <Pill tone="safe" className="mt-3"><ICheck size={15} /> {t('verifiedFrom')}</Pill>}
        </div>

        {n > 0 && (
          <>
            <div><HearButton audio={res.audio_b64} text={summary} lang={lang} label={`${t('hearIt')} · ${LANG_NAMES[lang]}`} /></div>
            <FunctionList
              functions={fns}
              title={couple}
              directionsHref={(i) => `/directions/${i}`}
              onVenue={() => saveWedding(res, fns)}
              onChange={(next) => { setFns(next); updateFunctions(res.scan_id, next) }}
            />
          </>
        )}

        <Link to="/check" className="text-center text-[0.95rem] font-medium text-ink-2 underline underline-offset-4">{t('checkAnother')}</Link>

        <details className="group rounded-2xl bg-paper-2/70 px-4 py-3 text-[0.95rem]">
          <summary className="cursor-pointer list-none font-medium text-ink-2 marker:hidden">{t('whatWeChecked')} <span className="text-ink-3 group-open:hidden">+</span></summary>
          <ul className="mt-2 space-y-1.5 text-ink-2">
            {(['checked1', 'checked2', 'checked3'] as const).map((k) => (
              <li key={k} className="flex items-center gap-2"><ICheck size={16} className="text-safe" /> {t(k)}</li>
            ))}
          </ul>
        </details>
      </div>
    </AppShell>
  )
}

function spokenSummary(couple: string, fns: WeddingFunction[], lang: Lang): string {
  const parts = fns.map((f) => {
    const day = fmtDay(f.date, lang, { day: 'numeric', month: 'long' })
    const time = fmtTime(f.time, lang)
    if (lang === 'hi') return `${f.name_original || f.name} ${day} को ${time ? time + ' बजे ' : ''}${f.venue_name ?? ''} में है।`
    return `${f.name} is on ${day}${time ? ' at ' + time : ''}${f.venue_name ? ', at ' + f.venue_name : ''}.`
  })
  const head = lang === 'hi' ? `${couple}। ${fns.length} कार्यक्रम हैं।` : `${couple}. ${fns.length} functions.`
  return [head, ...parts].join(' ')
}

/* ======================= Feedback ("this was a real invite") ======================= */

function useFeedback(scanId: string) {
  const [state, setState] = useState<'idle' | 'busy' | 'done'>('idle')
  const [count, setCount] = useState<number | null>(null)
  const send = async () => {
    setState('busy')
    try {
      const r = await api.feedback(scanId)
      const fa = r.pack_false_alarms
      setCount(typeof fa === 'number' ? fa : fa ? Math.max(...Object.values(fa)) : null)
      setState('done')
    } catch {
      setState('idle')
    }
  }
  return { state, count, send }
}

/* ======================= CHECK (amber) ======================= */

function CheckResult({ saved }: { saved: SavedScan }) {
  const { lang, t } = useUser()
  const res = saved.res
  const fb = useFeedback(res.scan_id)
  const reasons = res.reasons ?? []
  const wa = `https://wa.me/?text=${encodeURIComponent(`Is this wedding card real? Card Kholo flagged it: ${saved.label}. ${reasons.join('. ')}`)}`

  return (
    <AppShell
      back="/check"
      center={<span className="font-mono text-[0.85rem]">{saved.label}</span>}
      aside={{ eyebrow: 'Something looks off', title: <>Real families send <span className="accent-gold">links.</span> Thieves send files.</>, body: 'A short link or an "install to view" message is a common first step of the wedding-card scam. We say exactly what we found and why.' }}
      footer={
        <>
          <a href={wa} target="_blank" rel="noreferrer" className={btnClass('primary', 'lg', 'w-full')}><IWhatsApp size={20} /> {t('askFamily')}</a>
          <FeedbackButton fb={fb} />
        </>
      }
    >
      <div className="flex flex-col gap-5 animate-rise">
        <div className="h-1.5 rounded-full bg-check" aria-hidden="true" />
        <Exhibit label={saved.label} stamp={<Stamp kind="CHECK" label={t('CHECK')} size="md" />} />
        <div>
          <h1 className="display-md">{t('checkTitleAmber')}</h1>
          <p className="mt-2 text-lg text-ink-2">{t('checkSub')}</p>
        </div>
        <HearButton audio={res.audio_b64} text={`${t('checkTitleAmber')} ${reasons.join('. ')}. ${t('checkSub')}`} lang={lang} label={`${t('hearIt')} · ${LANG_NAMES[lang]}`} />
        <section className="card p-5">
          <h2 className="eyebrow mb-3 font-sans text-check">{t('whyFlagged')}</h2>
          <ul className="space-y-3">
            {reasons.map((r) => (
              <li key={r} className="flex items-start gap-3 text-[1.02rem]"><IAlert size={20} className="mt-0.5 shrink-0 text-check" /> {r}</li>
            ))}
          </ul>
        </section>
        <Link to="/check" className="text-center text-[0.95rem] font-medium text-ink-2 underline underline-offset-4">{t('checkAnother')}</Link>
      </div>
    </AppShell>
  )
}

/* ======================= STOP ======================= */

function StopResult({ saved }: { saved: SavedScan }) {
  const { user, lang, t } = useUser()
  const nav = useNavigate()
  const res = saved.res
  const style = res.warning_style ?? 'calm'
  const w = warningText[lang][style]
  const fb = useFeedback(res.scan_id)
  const shown = useRef(false)

  useEffect(() => {
    if (shown.current) return
    shown.current = true
    api.event(res.scan_id, 'warning_shown')
  }, [res.scan_id])

  const childName = getChild()?.child_name
  const told = res.alert_sent ? (childName ? fill(t('toldOnTelegram'), { name: childName }) : t('familyTold')) : null

  return (
    <AppShell
      tone="stop"
      close="/check"
      hideLang
      center={told ? <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1"><ITelegram size={16} /> {told}</span> : undefined}
      aside={{
        eyebrow: 'Fake card stopped',
        title: <>This isn't a card. It's a <span className="accent-gold">thief</span> in a wedding envelope.</>,
        body: 'The warning plays out loud in the parent’s language, and the linked son or daughter gets a Telegram alert at the same moment.',
        extra: res.alert_sent ? <TelegramPreview who={user?.name?.split(' ')[0] || 'Papa'} file={saved.label} /> : undefined,
      }}
      footer={
        <>
          <button type="button" onClick={() => { api.event(res.scan_id, 'opened_anyway'); nav(`/first-hour/${res.scan_id}`) }} className={btnClass('danger', 'lg', 'w-full')}>{t('alreadyOpened')}</button>
          <FeedbackButton fb={fb} dark />
        </>
      }
    >
      <div className="flex flex-col gap-5 animate-rise">
        <Exhibit dark caption={t('exhibit')} label={saved.label} stamp={<Stamp kind="STOP" label={t('STOP')} size="md" light />} />

        <h1 className="display-md text-paper" lang={lang}>{w.title}</h1>
        <p className="text-[1.12rem] leading-relaxed text-paper/90">{t('stopBody')}</p>

        <WarningPlayer
          audio={res.audio_b64}
          text={`${w.title} ${w.body}`}
          lang={lang}
          quote={w.title}
          label={t('playWarning')}
          autoPlay
          onStart={() => api.event(res.scan_id, 'warning_played')}
          onComplete={() => api.event(res.scan_id, 'warning_completed')}
        />

        <ul className="space-y-2.5 rounded-[22px] bg-black/10 p-5">
          {(res.reasons ?? []).map((r) => (
            <li key={r} className="flex items-start gap-3 text-[1.02rem]"><IX size={20} strokeWidth={2.6} className="mt-0.5 shrink-0" /> {r}</li>
          ))}
        </ul>
      </div>
    </AppShell>
  )
}

function FeedbackButton({ fb, dark = false }: { fb: ReturnType<typeof useFeedback>; dark?: boolean }) {
  const { t: tt } = useUser()
  if (fb.state === 'done') {
    return (
      <p role="status" className={`rounded-2xl px-4 py-3 text-center text-[0.95rem] ${dark ? 'bg-black/15 text-paper' : 'bg-safe-soft text-safe'}`}>
        {tt('thanksFeedback')}{fb.count != null && <span className="block text-sm opacity-80">{fill(tt('feedbackCount'), { n: fb.count })}</span>}
      </p>
    )
  }
  return (
    <button type="button" disabled={fb.state === 'busy'} onClick={fb.send} className={btnClass(dark ? 'light' : 'ghost', 'md', `w-full ${dark ? '' : 'text-ink-2'}`)}>
      {tt('realInvite')}
    </button>
  )
}

/** Desktop-only: what the linked son or daughter sees on Telegram at the same moment. */
function TelegramPreview({ who, file }: { who: string; file: string }) {
  return (
    <div className="mt-10 max-w-[25rem] rotate-[-1.5deg] rounded-[24px] bg-night p-5 text-paper shadow-lift ring-1 ring-white/10">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#6f8196] text-white"><ITelegram size={22} /></span>
        <div className="flex-1">
          <div className="text-sm font-semibold">Card Kholo</div>
          <div className="text-xs text-paper/60">now · on the family's phone</div>
        </div>
      </div>
      <p className="mt-4 text-[0.98rem] leading-relaxed">
        <b>{who} just received a fake wedding card</b> (<span className="font-mono text-[0.85rem] text-gold-2 [overflow-wrap:anywhere]">{file}</span>).
        It's an app that can read SMS. We warned them not to open it. Call now.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-2 text-sm font-semibold">
        <span className="rounded-xl bg-white/10 py-2.5 text-center">Called</span>
        <span className="rounded-xl bg-white/10 py-2.5 text-center">Real invite</span>
      </div>
    </div>
  )
}
