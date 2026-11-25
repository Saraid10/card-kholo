// Frame for every in-app screen.
// Mobile: full-bleed column, top bar, sticky bottom actions.
// Tablet: the same column, centred and roomier.
// Desktop: split. Left is an editorial panel (step headline, tagline, QR to open on a phone),
// right is the phone-width flow.
import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { useUser } from '../state/user'
import { IArrowLeft, IClose } from './Icons'
import { LangSwitch, Logo } from './ui'

export type Tone = 'paper' | 'maroon' | 'stop'

interface Props {
  children: ReactNode
  /** Back target. `-1` = history back. Omit for no back button (shows the logo instead). */
  back?: string | -1
  close?: string
  center?: ReactNode
  right?: ReactNode
  footer?: ReactNode
  tone?: Tone
  aside?: { eyebrow?: string; title: ReactNode; body?: ReactNode; extra?: ReactNode }
  hideLang?: boolean
}

const toneBg: Record<Tone, string> = {
  paper: 'paper-bg text-ink',
  maroon: 'maroon-bg text-paper',
  stop: 'bg-stop text-paper',
}

export default function AppShell({ children, back, close, center, right, footer, tone = 'paper', aside, hideLang }: Props) {
  const nav = useNavigate()
  const { t } = useUser()
  const dark = tone !== 'paper'
  const iconBtn = `grid h-11 w-11 place-items-center rounded-full transition-colors ${dark ? 'bg-white/10 hover:bg-white/20' : 'bg-card ring-1 ring-line hover:bg-paper-2'}`

  return (
    <div className={`min-h-dvh lg:grid lg:grid-cols-[minmax(380px,1fr)_minmax(520px,640px)] xl:grid-cols-[1fr_640px] ${dark ? '' : 'bg-paper'}`}>
      {/* Desktop editorial panel */}
      <aside className={`${tone === 'stop' ? 'stop-bg' : 'maroon-bg'} relative hidden overflow-hidden text-paper lg:flex lg:sticky lg:top-0 lg:h-dvh lg:flex-col lg:justify-between lg:p-12 xl:p-16`}>
        <Logo dark />
        <div className="max-w-[34rem] animate-rise">
          {aside?.eyebrow && <div className="eyebrow mb-5 text-gold-2">{aside.eyebrow}</div>}
          <h2 className="display-lg text-paper">{aside?.title ?? <>The safe way to <span className="accent-gold">open</span> a wedding card.</>}</h2>
          {aside?.body && <p className="mt-6 max-w-[30rem] text-lg leading-relaxed text-paper/80">{aside.body}</p>}
          {aside?.extra}
        </div>
        <div className="flex items-end justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="rounded-xl bg-paper p-2"><QRCodeSVG value={typeof window !== 'undefined' ? window.location.href : 'https://cardkholo.app'} size={76} fgColor="#22181A" bgColor="#F7F1E7" /></div>
            <p className="max-w-[12rem] text-sm leading-snug text-paper/70">Open this screen on your phone. Scan with the camera.</p>
          </div>
          <p className="text-right text-xs text-paper/50">Sarvam AI · Flagsmith · NudgeBee</p>
        </div>
        <Ornament />
      </aside>

      {/* Flow column */}
      <div className={`relative flex min-h-dvh flex-col ${toneBg[tone]} lg:border-l lg:border-line`}>
        <div className="mx-auto flex w-full max-w-[560px] flex-1 flex-col lg:max-w-[520px]">
          <header className={`sticky top-0 z-20 flex h-[68px] items-center justify-between gap-3 px-5 backdrop-blur-md sm:px-6 ${tone === 'paper' ? 'bg-paper/90' : tone === 'maroon' ? 'bg-maroon/90' : 'bg-stop/95'}`}>
            <div className="flex min-w-0 items-center gap-3">
              {back !== undefined ? (
                <button type="button" aria-label={t('back')} className={iconBtn} onClick={() => (back === -1 ? nav(-1) : nav(back))}>
                  <IArrowLeft size={20} />
                </button>
              ) : close ? (
                <Link to={close} aria-label={t('close')} className={iconBtn}><IClose size={20} /></Link>
              ) : (
                <span className="lg:hidden"><Logo dark={dark} /></span>
              )}
              {center && <div className={`min-w-0 truncate text-[0.95rem] font-medium ${dark ? 'text-paper/85' : 'text-ink-2'}`}>{center}</div>}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {right}
              {!hideLang && <LangSwitch compact dark={dark} />}
            </div>
          </header>

          <main className="flex flex-1 flex-col px-5 pb-6 pt-2 sm:px-6">{children}</main>

          {footer && (
            <div className={`sticky bottom-0 z-20 px-5 pt-3 safe-bottom backdrop-blur-md sm:px-6 ${tone === 'paper' ? 'bg-paper/90' : tone === 'maroon' ? 'bg-maroon/90' : 'bg-stop/95'}`}>
              <div className="flex flex-col gap-2">{footer}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/** Thin gold ornamental frame in the corner of the maroon panel, like a printed card. */
export function Ornament({ className = 'pointer-events-none absolute -right-24 -top-24 h-[420px] w-[420px] opacity-[.18]' }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden="true">
      <g fill="none" stroke="#d8c6a0" strokeWidth=".6">
        {Array.from({ length: 12 }).map((_, i) => (
          <ellipse key={i} cx="100" cy="100" rx="90" ry="34" transform={`rotate(${i * 15} 100 100)`} />
        ))}
        <circle cx="100" cy="100" r="96" />
        <circle cx="100" cy="100" r="22" />
      </g>
    </svg>
  )
}
