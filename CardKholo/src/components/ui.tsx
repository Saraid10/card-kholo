import { useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { Lang, Verdict } from '../api/types'
import { LANG_LABELS } from '../i18n/strings'
import { useUser } from '../state/user'
import { ICheck, ICopy } from './Icons'

/* ---------- Brand ---------- */

export function Seal({ size = 34, tone = 'maroon' }: { size?: number; tone?: 'maroon' | 'gold' }) {
  const bg = tone === 'maroon' ? '#5b2a33' : '#b39a6b'
  const fg = tone === 'maroon' ? '#d8c6a0' : '#3a0d17'
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path fill={bg} d="M32 2c3 0 4.6 3 7.4 3.8 2.9.8 5.9-.9 8.3.8 2.4 1.8 2 5.1 3.8 7.4 1.8 2.3 5.1 3 5.9 5.9.8 2.8-1.5 5.3-1.5 8.1s2.3 5.3 1.5 8.1c-.8 2.9-4.1 3.6-5.9 5.9-1.8 2.3-1.4 5.6-3.8 7.4-2.4 1.7-5.4 0-8.3.8C36.6 51 35 54 32 54s-4.6-3-7.4-3.8c-2.9-.8-5.9.9-8.3-.8-2.4-1.8-2-5.1-3.8-7.4-1.8-2.3-5.1-3-5.9-5.9-.8-2.8 1.5-5.3 1.5-8.1S5.8 22.7 6.6 19.9c.8-2.9 4.1-3.6 5.9-5.9 1.8-2.3 1.4-5.6 3.8-7.4 2.4-1.7 5.4 0 8.3-.8C27.4 5 29 2 32 2Z" transform="translate(0 4)" />
      <circle cx="32" cy="32" r="19" fill="none" stroke={fg} strokeWidth="1.2" strokeDasharray="1.5 2.5" opacity=".8" />
      <text x="32" y="40" textAnchor="middle" fontFamily="Fraunces, Georgia, serif" fontStyle="italic" fontSize="22" fill={fg}>ck</text>
    </svg>
  )
}

export function Logo({ dark = false, to = '/' }: { dark?: boolean; to?: string }) {
  return (
    <Link to={to} className="inline-flex items-center gap-2.5 no-underline" aria-label="Card Kholo home">
      <Seal size={32} tone={dark ? 'gold' : 'maroon'} />
      <span className={`font-display text-[1.45rem] leading-none tracking-tight ${dark ? 'text-paper' : 'text-ink'}`}>
        card<span className={`italic ${dark ? 'text-gold-2' : 'text-wine'}`}>kholo</span>
      </span>
    </Link>
  )
}

/* ---------- Buttons ---------- */

type BtnVariant = 'primary' | 'maroon' | 'ghost' | 'outline' | 'danger' | 'light' | 'gold'
const variants: Record<BtnVariant, string> = {
  primary: 'bg-ink text-paper hover:bg-maroon',
  maroon: 'bg-maroon text-paper hover:bg-wine',
  gold: 'bg-marigold text-night hover:bg-gold-2',
  ghost: 'bg-transparent text-ink hover:bg-paper-2',
  outline: 'bg-card text-ink border-[1.5px] border-ink/80 hover:bg-paper-2',
  danger: 'bg-paper text-stop hover:bg-white',
  light: 'bg-white/10 text-paper border border-white/25 hover:bg-white/15',
}

export function btnClass(variant: BtnVariant = 'primary', size: 'md' | 'lg' | 'sm' = 'lg', extra = '') {
  const sz = size === 'lg' ? 'min-h-[58px] px-6 text-[1.08rem]' : size === 'md' ? 'min-h-[48px] px-5 text-base' : 'min-h-[38px] px-3.5 text-sm'
  return `inline-flex items-center justify-center gap-2.5 rounded-full font-semibold no-underline transition-[background,transform,box-shadow] duration-150 active:scale-[.98] disabled:opacity-50 disabled:pointer-events-none ${sz} ${variants[variant]} ${extra}`
}

export function Button({ variant = 'primary', size = 'lg', className = '', ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; size?: 'md' | 'lg' | 'sm' }) {
  return <button type="button" className={btnClass(variant, size, className)} {...rest} />
}

export function CopyButton({ text, label, done, className = '', variant = 'outline' }: { text: string; label: string; done: string; className?: string; variant?: BtnVariant }) {
  const [ok, setOk] = useState(false)
  return (
    <button
      type="button"
      className={btnClass(variant, 'md', className)}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text)
        } catch {
          const ta = document.createElement('textarea')
          ta.value = text
          document.body.appendChild(ta)
          ta.select()
          document.execCommand('copy')
          ta.remove()
        }
        setOk(true)
        setTimeout(() => setOk(false), 1800)
      }}
    >
      {ok ? <ICheck size={18} /> : <ICopy size={18} />}
      <span aria-live="polite">{ok ? done : label}</span>
    </button>
  )
}

/* ---------- Verdict stamp ---------- */

export type StampKind = 'SAFE' | 'CHECK' | 'STOP'
export const verdictToStamp = (v: Verdict): StampKind => (v === 'OK' ? 'SAFE' : v === 'SUSPICIOUS' ? 'CHECK' : 'STOP')

const stampColor: Record<StampKind, string> = { SAFE: 'text-safe', CHECK: 'text-check', STOP: 'text-stop' }

export function Stamp({ kind, label, size = 'md', animate = true, className = '', light = false }: {
  kind: StampKind; label?: string; size?: 'sm' | 'md' | 'lg'; animate?: boolean; className?: string; light?: boolean
}) {
  const sz = size === 'lg' ? 'text-[2.6rem] px-5 py-1.5 border-[3px]' : size === 'md' ? 'text-[1.6rem] px-3.5 py-0.5 border-[2.5px]' : 'text-[0.95rem] px-2 py-0 border-2'
  return (
    <span
      className={`inline-block rounded-lg font-display font-bold uppercase leading-[1.15] tracking-[0.06em] ${light ? 'text-paper' : stampColor[kind]} ${sz} ${animate ? 'animate-stamp' : '-rotate-6'} ${className}`}
      style={{ borderStyle: 'double', borderColor: 'currentColor', fontVariationSettings: "'opsz' 40, 'wdth' 80", boxShadow: 'inset 0 0 0 1px currentColor' }}
    >
      {label ?? kind}
    </span>
  )
}

/** Filename that wraps at _ . - boundaries instead of mid-word. */
export function FileName({ name }: { name: string }) {
  const parts = name.split(/(?<=[_.\-/])/)
  return <>{parts.map((p, i) => <span key={i}>{p}{i < parts.length - 1 && <wbr />}</span>)}</>
}

/* ---------- Exhibit (the file as an evidence tag) ---------- */

export function Exhibit({ label, caption, stamp, dark = false, children }: {
  label: string; caption?: string; stamp?: ReactNode; dark?: boolean; children?: ReactNode
}) {
  return (
    <div className={`relative rounded-[18px] px-5 pb-5 pt-4 ${dark ? 'bg-white/[.08] ring-1 ring-white/20' : 'card'}`}>
      <span className={`absolute -top-2.5 left-5 h-5 w-5 rounded-full ${dark ? 'bg-stop' : 'bg-paper'} ring-1 ${dark ? 'ring-white/25' : 'ring-line'}`} aria-hidden="true" />
      {caption && <div className={`eyebrow mb-2 pl-7 ${dark ? 'text-white/70' : 'text-ink-3'}`}>{caption}</div>}
      <div className="flex items-start justify-between gap-3">
        <div className={`min-w-0 font-mono text-[0.95rem] leading-snug [overflow-wrap:anywhere] ${dark ? 'text-paper' : 'text-ink'}`}><FileName name={label} /></div>
        {stamp && <div className="shrink-0 -mt-1">{stamp}</div>}
      </div>
      {children}
    </div>
  )
}

/* ---------- Language switch ---------- */

export function LangSwitch({ compact = false, dark = false }: { compact?: boolean; dark?: boolean }) {
  const { lang, setLang, t } = useUser()
  return (
    <div role="group" aria-label={t('language')} className={`inline-flex rounded-full p-1 ${dark ? 'bg-white/10' : 'bg-paper-2'}`}>
      {(['hi', 'kn', 'en'] as Lang[]).map((l) => (
        <button
          key={l}
          type="button"
          lang={l}
          aria-pressed={lang === l}
          onClick={() => setLang(l)}
          className={`rounded-full ${compact ? 'px-2.5 py-1 text-sm' : 'px-3.5 py-1.5 text-[0.95rem]'} font-medium transition-colors ${
            lang === l ? (dark ? 'bg-paper text-ink' : 'bg-card text-ink shadow-sm') : dark ? 'text-paper/75 hover:text-paper' : 'text-ink-2 hover:text-ink'
          }`}
        >
          {compact && l === 'en' ? 'EN' : LANG_LABELS[l]}
        </button>
      ))}
    </div>
  )
}

/* ---------- Misc ---------- */

export function Spinner({ className = '' }: { className?: string }) {
  return <span className={`inline-block h-5 w-5 animate-spin rounded-full border-2 border-current border-r-transparent ${className}`} aria-hidden="true" />
}

export function Pill({ children, tone = 'neutral', className = '' }: { children: ReactNode; tone?: 'neutral' | 'safe' | 'stop' | 'check' | 'gold' | 'dark'; className?: string }) {
  const tones = {
    neutral: 'bg-paper-2 text-ink-2',
    safe: 'bg-safe-soft text-safe',
    stop: 'bg-stop-soft text-stop',
    check: 'bg-check-soft text-check',
    gold: 'bg-gold/15 text-maroon',
    dark: 'bg-white/10 text-paper',
  }
  return <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${tones[tone]} ${className}`}>{children}</span>
}

export function Dot({ tone = 'safe', pulse = false }: { tone?: 'safe' | 'stop' | 'gold' | 'muted'; pulse?: boolean }) {
  const c = { safe: 'bg-safe', stop: 'bg-stop', gold: 'bg-gold', muted: 'bg-ink-3' }[tone]
  return (
    <span className="relative inline-flex h-2.5 w-2.5">
      {pulse && <span className={`absolute inset-0 animate-ping rounded-full opacity-60 ${c}`} />}
      <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${c}`} />
    </span>
  )
}

export function ErrorNote({ message, onRetry, retryLabel }: { message: string; onRetry?: () => void; retryLabel?: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-2xl bg-stop-soft px-4 py-3 text-stop">
      <span className="mt-0.5 font-bold">!</span>
      <div className="flex-1 text-[0.98rem]">{message}</div>
      {onRetry && <button type="button" onClick={onRetry} className="font-semibold underline underline-offset-2">{retryLabel}</button>}
    </div>
  )
}
