import { useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { api } from '../../api'
import AppShell from '../../components/AppShell'
import { IMic } from '../../components/Icons'
import { ErrorNote, Spinner } from '../../components/ui'
import { errorKey } from '../../lib/errors'
import { getHost, saveHost } from '../../state/scans'
import { useUser } from '../../state/user'

type Phase = 'ready' | 'recording' | 'sending'

export default function HostSpeak() {
  const { user, t } = useUser()
  const nav = useNavigate()
  const host = getHost()
  const [phase, setPhase] = useState<Phase>('ready')
  const [secs, setSecs] = useState(0)
  const [level, setLevel] = useState<number[]>(Array(28).fill(0.15))
  const [err, setErr] = useState<string | null>(null)
  const rec = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const stopAll = useRef<() => void>(() => {})

  useEffect(() => () => stopAll.current(), [])

  if (!user) return <Navigate to="/start?role=host" replace />
  if (!host) return <Navigate to="/host" replace />

  async function send(blob: Blob) {
    setPhase('sending')
    try {
      const r = await api.voiceInvite(blob, user!.user_id)
      const guest = (r.parsed as { guest?: string } | undefined)?.guest
      saveHost({ ...host!, last: { ...r, guest } })
      nav('/host/preview')
    } catch (e) {
      setErr(t(errorKey(e)))
      setPhase('ready')
    }
  }

  async function start() {
    setErr(null)
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setErr("This browser can't record audio. Try Chrome on your phone.")
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      chunks.current = []
      mr.ondataavailable = (e) => e.data.size && chunks.current.push(e.data)
      mr.onstop = () => send(new Blob(chunks.current, { type: mr.mimeType || 'audio/webm' }))
      mr.start()
      rec.current = mr

      // live level meter
      const ctx = new AudioContext()
      const an = ctx.createAnalyser()
      an.fftSize = 64
      ctx.createMediaStreamSource(stream).connect(an)
      const buf = new Uint8Array(an.frequencyBinCount)
      const t0 = Date.now()
      const tick = window.setInterval(() => {
        an.getByteFrequencyData(buf)
        const avg = buf.reduce((a, b) => a + b, 0) / buf.length / 255
        setLevel((l) => [...l.slice(1), Math.max(0.08, Math.min(1, avg * 2.2))])
        setSecs(Math.floor((Date.now() - t0) / 1000))
      }, 90)
      stopAll.current = () => {
        window.clearInterval(tick)
        stream.getTracks().forEach((tr) => tr.stop())
        ctx.close().catch(() => {})
      }
      setPhase('recording')
    } catch {
      setErr('Microphone permission was blocked. Allow it in the browser and try again.')
    }
  }

  function finish() {
    stopAll.current()
    rec.current?.stop()
  }

  const recording = phase === 'recording'

  return (
    <AppShell
      tone="maroon"
      back="/host"
      center={<span className="font-display italic text-gold-2">{host.couple}</span>}
      hideLang
      aside={{ eyebrow: 'Speak the invite', title: <>Say it like you'd say it <span className="accent-gold">on the phone.</span></>, body: 'Saaras turns your voice into text, sarvam-105b writes a respectful invite in the guest’s language, and Bulbul reads it back as a voice note.' }}
    >
      <div className="flex flex-1 flex-col items-center justify-between gap-8 pb-4 pt-4 text-center animate-rise">
        <div>
          <h1 className="display-md text-paper">Who should we invite?</h1>
          <p className="mt-3 text-paper/75">Say their name, language and which functions.</p>
        </div>

        <div className="flex flex-col items-center gap-6">
          <button
            type="button"
            onClick={recording ? finish : start}
            disabled={phase === 'sending'}
            aria-label={recording ? 'Stop recording' : 'Start recording'}
            className={`relative grid h-40 w-40 place-items-center rounded-full transition-transform active:scale-95 ${recording ? 'bg-paper' : 'bg-marigold'} text-night shadow-[0_20px_60px_-15px_rgba(0,0,0,.6)]`}
          >
            <span className="absolute -inset-4 rounded-full border border-gold/40" />
            <span className="absolute -inset-9 rounded-full border border-gold/20" />
            {phase === 'sending' ? <Spinner className="h-10 w-10 text-maroon" /> : recording ? <span className="h-12 w-12 rounded-xl bg-stop" /> : <IMic size={56} />}
          </button>

          <div className="flex h-14 items-center gap-[3px]" aria-hidden="true">
            {level.map((v, i) => (
              <span key={i} className="w-[4px] rounded-full bg-gold-2 transition-[height] duration-100" style={{ height: `${recording ? v * 100 : 12}%`, opacity: recording ? 1 : 0.4 }} />
            ))}
          </div>

          <div className="text-paper/85" aria-live="polite">
            {phase === 'sending' ? 'Writing the invite…' : recording ? <><span className="font-mono">0:{String(secs).padStart(2, '0')}</span> · Listening. Tap to finish.</> : 'Tap the mic and speak.'}
          </div>
        </div>

        <div className="w-full">
          {err && <div className="mb-4"><ErrorNote message={err} /></div>}
          <div className="rounded-[22px] border border-gold/30 bg-white/[.06] p-5 text-left">
            <div className="eyebrow text-gold-2">Try saying</div>
            <p className="mt-2 font-display text-[1.25rem] italic leading-snug text-paper">“Sharma ji ko Hindi mein invite bhejo, mehendi aur reception ke liye.”</p>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
