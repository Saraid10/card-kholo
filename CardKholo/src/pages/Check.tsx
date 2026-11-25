import { useEffect, useRef, useState, type DragEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { api, type ScanRes } from '../api'
import AppShell from '../components/AppShell'
import { IFile, IShield, IUpload } from '../components/Icons'
import { Button, Dot, ErrorNote, Pill, Seal, Spinner, Stamp, verdictToStamp } from '../components/ui'
import { errorKey } from '../lib/errors'
import { fill } from '../i18n/strings'
import { getChild, getMemoryScan, getRecent, saveScan } from '../state/scans'
import { useUser } from '../state/user'

const VERDICT_COLOR = { SAFE: 'text-safe', CHECK: 'text-check', STOP: 'text-stop' } as const

// Harmless demo files, built in the browser. The "APK" is a few bytes of text with a scary name:
// no real malware anywhere (spec 5.7).
const SAMPLES = {
  // The real sample is demo/sample-invite.pdf (public/), so the backend can read actual functions from it.
  real: async () => {
    try {
      const res = await fetch('/sample-invite.pdf')
      if (!res.ok) throw new Error(String(res.status))
      return new File([await res.blob()], 'Wedding_Invite_Priya.pdf', { type: 'application/pdf' })
    } catch {
      return new File(['%PDF-1.4\n% Card Kholo demo card\n'], 'Wedding_Invite_Priya.pdf', { type: 'application/pdf' })
    }
  },
  fake: () => new File(['PK\u0003\u0004 Card Kholo harmless test file'], 'Shaadi_Card_Priya.pdf.apk', { type: 'application/vnd.android.package-archive' }),
  broad: () => new File(['%PDF-1.4\n% demo\n'], 'Wedding_Invitation_Sharma.pdf', { type: 'application/pdf' }),
}

export default function Check() {
  const { user, t } = useUser()
  const nav = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState<null | { label: string }>(null)
  const [stage, setStage] = useState(0)
  const [err, setErr] = useState<string | null>(null)
  const [drag, setDrag] = useState(false)
  const lastRun = useRef<() => void>(() => {})
  const startOfDay = new Date(); startOfDay.setHours(0, 0, 0, 0)
  const today = getRecent().filter((r) => new Date(r.time) >= startOfDay)
  const child = getChild()?.child_name
  const chip = child ? <Pill tone="safe" className="whitespace-nowrap"><Dot tone="safe" /> {fill(t('isLinked'), { name: child })}</Pill> : null

  useEffect(() => {
    if (!busy) return
    setStage(0)
    const a = setTimeout(() => setStage(1), 1400)
    const b = setTimeout(() => setStage(2), 12000)
    return () => { clearTimeout(a); clearTimeout(b) }
  }, [busy])

  if (!user) return <Navigate to="/start" replace />

  async function run(kind: 'file' | 'text', payload: File | string) {
    const label = kind === 'file' ? (payload as File).name : (payload as string).trim().slice(0, 40)
    lastRun.current = () => run(kind, payload)
    setErr(null)
    setBusy({ label })
    try {
      const res: ScanRes = kind === 'file' ? await api.scanFile(payload as File, user!.user_id) : await api.scanText(payload as string, user!.user_id)
      saveScan({ res, label, kind, at: Date.now() })
      nav(`/result/${res.scan_id}`)
    } catch (e) {
      setErr(t(errorKey(e)))
      setBusy(null)
    }
  }

  function onFiles(files: FileList | null) {
    const f = files?.[0]
    if (f) run('file', f)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDrag(false)
    onFiles(e.dataTransfer.files)
  }

  const stageText = [t('checkingRules'), t('readingCard'), t('readingSlow')][stage]

  return (
    <AppShell
      right={chip ? <span className="hidden sm:inline-flex">{chip}</span> : undefined}
      aside={{
        eyebrow: 'Check a card',
        title: <>Got a card? <span className="accent-gold">Check it</span> before you tap.</>,
        body: 'Drop a photo, a PDF or the file exactly as WhatsApp saved it. Rules look for hidden apps and fake links first; only then does Sarvam read the functions.',
        extra: (
          <div className="mt-10 grid max-w-[28rem] grid-cols-3 gap-3">
            {(['SAFE', 'CHECK', 'STOP'] as const).map((k) => (
              <div key={k} className="rounded-2xl bg-paper p-3 text-center">
                <Stamp kind={k} size="sm" animate={false} />
                <div className="mt-2 text-xs leading-snug text-ink-2">{k === 'SAFE' ? 'Dates to your calendar' : k === 'CHECK' ? 'Looks off, here is why' : 'Warning + family alert'}</div>
              </div>
            ))}
          </div>
        ),
      }}
      footer={
        <Button onClick={() => text.trim() && run('text', text)} disabled={!text.trim() || !!busy} className="w-full">
          {t('checkMessage')}
        </Button>
      }
    >
      <div className="flex flex-col gap-6 animate-rise" onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)} onDrop={onDrop}>
        {chip && <div className="-mt-1 sm:hidden">{chip}</div>}
        <h1 className="display-md">{t('checkTitle')}</h1>

        <input ref={fileRef} type="file" className="sr-only" onChange={(e) => { onFiles(e.target.files); e.target.value = '' }} aria-label={t('chooseCard')} />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className={`group relative flex items-center gap-4 overflow-hidden rounded-[24px] p-5 text-left transition-all ${
            drag ? 'bg-maroon text-paper ring-2 ring-gold' : 'bg-maroon text-paper hover:bg-wine'
          }`}
        >
          <span className="absolute inset-2 rounded-[18px] border border-gold/40" aria-hidden="true" />
          <span className="relative grid h-14 w-14 shrink-0 place-items-center rounded-full bg-marigold text-night transition-transform group-hover:-translate-y-0.5">
            <IUpload size={26} strokeWidth={2.4} />
          </span>
          <span className="relative">
            <span className="block text-[1.2rem] font-semibold">{drag ? t('dropHere') : t('chooseCard')}</span>
            <span className="block text-[0.95rem] text-paper/75">{t('chooseCardSub')}</span>
          </span>
        </button>

        <label className="block">
          <span className="mb-2 block text-[0.95rem] font-medium text-ink-2">{t('orPaste')}</span>
          <textarea rows={3} className="field resize-none" value={text} placeholder={t('pastePh')} onChange={(e) => setText(e.target.value)} />
        </label>

        {err && <ErrorNote message={err} onRetry={() => lastRun.current()} retryLabel={t('retry')} />}

        {today.length > 0 && (
          <section>
            <h2 className="mb-2 font-sans text-[0.95rem] font-medium tracking-normal text-ink-2">{t('checkedToday')}</h2>
            <ul className="card divide-y divide-line/80 overflow-hidden p-0">
              {today.map((h) => {
                const kind = verdictToStamp(h.verdict)
                // Full results are kept in memory only: after a reload the row stays but a tap does nothing.
                const open = () => { if (getMemoryScan(h.scan_id)) nav(`/result/${h.scan_id}`) }
                return (
                  <li key={h.scan_id}>
                    <button type="button" onClick={open} className="flex w-full items-center gap-3 px-4 py-3.5 text-left hover:bg-paper-2/60">
                      <IFile size={20} className="shrink-0 text-ink-3" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-mono text-[0.88rem]">{h.label}</span>
                        <span className="text-[0.8rem] text-ink-3">{new Date(h.time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</span>
                      </span>
                      <span className={`font-display text-[1.05rem] font-bold uppercase tracking-[0.06em] ${VERDICT_COLOR[kind]}`}>{t(kind)}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
        )}

        <section>
          <h2 className="mb-2 font-sans text-[0.95rem] font-medium tracking-normal text-ink-2">{t('samples')}</h2>
          <div className="flex flex-wrap gap-2">
            <SampleChip label={t('sampleReal')} file="Wedding_Invite_Priya.pdf" onClick={async () => run('file', await SAMPLES.real())} />
            <SampleChip label={t('sampleFake')} file="Shaadi_Card_Priya.pdf.apk" onClick={() => run('file', SAMPLES.fake())} />
            <SampleChip label={t('sampleBroad')} file="Wedding_Invitation_Sharma.pdf" onClick={() => run('file', SAMPLES.broad())} />
          </div>
        </section>

        <p className="flex items-start gap-2 text-sm text-ink-3"><IShield size={17} className="mt-0.5 shrink-0" /> {t('privacy')}</p>
      </div>

      {busy && <Checking label={busy.label} text={stageText} title={t('checking')} />}
    </AppShell>
  )
}

function SampleChip({ label, file, onClick }: { label: string; file: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="lift flex flex-col items-start rounded-2xl bg-card px-3.5 py-2 text-left ring-1 ring-line hover:ring-ink-3">
      <span className="text-[0.92rem] font-semibold">{label}</span>
      <span className="max-w-[11rem] truncate font-mono text-[0.72rem] text-ink-3">{file}</span>
    </button>
  )
}

function Checking({ label, text, title }: { label: string; text: string; title: string }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-paper/85 p-6 backdrop-blur-sm" role="status" aria-live="polite">
      <div className="card w-full max-w-[360px] animate-rise p-7 text-center">
        <div className="relative mx-auto grid h-20 w-20 place-items-center">
          <span className="absolute inset-0 animate-spin rounded-full border-2 border-gold/30 border-t-maroon [animation-duration:1.2s]" />
          <Seal size={48} />
        </div>
        <div className="mt-5 font-display text-2xl">{title}</div>
        <div className="mx-auto mt-2 max-w-full truncate font-mono text-sm text-ink-3">{label}</div>
        <div className="mt-5 flex items-center justify-center gap-2 text-[0.95rem] text-ink-2"><Spinner className="h-4 w-4 text-wine" /> {text}</div>
      </div>
    </div>
  )
}
