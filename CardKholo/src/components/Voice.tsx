import type { Lang } from '../api/types'
import { useVoice } from '../lib/useVoice'
import { IPause, IPlay, IVolume } from './Icons'

/** Pill button: "Hear it in Hindi". */
export function HearButton({ audio, text, lang, label, dark = false, onStart, onComplete }: {
  audio?: string | null; text: string; lang: Lang; label: string; dark?: boolean; onStart?: () => void; onComplete?: () => void
}) {
  const v = useVoice(audio, text, lang, { onStart, onComplete })
  const playing = v.state === 'playing'
  return (
    <button
      type="button"
      onClick={() => (playing ? v.stop() : v.play())}
      aria-pressed={playing}
      className={`relative inline-flex min-h-[46px] items-center gap-2.5 overflow-hidden rounded-full px-4 text-[0.98rem] font-semibold transition-colors ${
        dark ? 'bg-white/12 text-paper hover:bg-white/20' : 'bg-card text-ink ring-1 ring-line hover:bg-paper-2'
      }`}
    >
      <span className={`absolute inset-y-0 left-0 ${dark ? 'bg-white/10' : 'bg-gold/15'}`} style={{ width: `${v.progress * 100}%` }} aria-hidden="true" />
      <span className="relative">{playing ? <IPause size={18} /> : <IVolume size={19} />}</span>
      <span className="relative">{label}</span>
    </button>
  )
}

/** Big round player used on the STOP screen. */
export function WarningPlayer({ audio, text, lang, quote, label, autoPlay, onStart, onComplete }: {
  audio?: string | null; text: string; lang: Lang; quote: string; label: string; autoPlay?: boolean
  onStart?: () => void; onComplete?: () => void
}) {
  const v = useVoice(audio, text, lang, { onStart, onComplete })
  const playing = v.state === 'playing'
  return (
    <div className="flex items-center gap-4 rounded-[22px] bg-black/15 p-4 ring-1 ring-white/15">
      <button
        type="button"
        aria-label={label}
        onClick={() => (playing ? v.stop() : v.play())}
        ref={(el) => {
          // Try to speak straight away; browsers may block it until a tap, so the button stays.
          if (el && autoPlay && !el.dataset.auto) {
            el.dataset.auto = '1'
            setTimeout(() => v.play(), 450)
          }
        }}
        className={`grid h-16 w-16 shrink-0 place-items-center rounded-full bg-paper text-stop shadow-lg transition-transform active:scale-95 ${playing ? '' : 'animate-pulse-ring'}`}
      >
        {playing ? <IPause size={24} /> : <IPlay size={24} />}
      </button>
      <div className="min-w-0 flex-1">
        <p className="font-display text-[1.18rem] italic leading-snug" lang={lang}>“{quote}”</p>
        <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/20">
          <div className="h-full rounded-full bg-paper transition-[width] duration-150" style={{ width: `${v.progress * 100}%` }} />
        </div>
      </div>
    </div>
  )
}
