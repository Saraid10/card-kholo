import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import type { Lang } from '../../api'
import AppShell from '../../components/AppShell'
import { ICheck, ILink, IWhatsApp } from '../../components/Icons'
import { HearButton } from '../../components/Voice'
import { btnClass, Pill, Seal } from '../../components/ui'
import { LANG_NAMES } from '../../i18n/strings'
import { getHost, saveHost } from '../../state/scans'

export default function HostPreview() {
  const host = getHost()
  const last = host?.last
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(last?.invite_text ?? '')
  if (!host || !last) return <Navigate to="/host" replace />

  const parsed = (last.parsed ?? {}) as { guest?: string; lang?: Lang; functions?: string[] }
  const guest = parsed.guest ?? last.guest ?? 'Your guest'
  const lang: Lang = parsed.lang ?? (/[ऀ-ॿ]/.test(text) ? 'hi' : /[ಀ-೿]/.test(text) ? 'kn' : 'en')
  const wa = `https://wa.me/?text=${encodeURIComponent(text)}`
  const short = (last.invite_url ?? '').replace(/^https?:\/\//, '')

  return (
    <AppShell
      back="/host/speak"
      center={<span className="font-display italic text-wine">{host.couple}</span>}
      right={<button type="button" onClick={() => {
        if (editing) saveHost({ ...host, last: { ...last, invite_text: text } })
        setEditing((e) => !e)
      }} className="rounded-full px-3 py-1.5 text-[0.95rem] font-semibold text-wine hover:bg-paper-2">{editing ? 'Done' : 'Edit'}</button>}
      hideLang
      aside={{ eyebrow: 'Preview and send', title: <>A link, <span className="accent-gold">never a file.</span></>, body: 'Guests can tell it’s really you: the link opens a page verified by Card Kholo, with every function one tap from their calendar.' }}
      footer={
        <>
          <a href={wa} target="_blank" rel="noreferrer" className={btnClass('primary', 'lg', 'w-full')}><IWhatsApp size={20} /> Send on WhatsApp</a>
          <Link to="/host/speak" className={btnClass('ghost', 'md', 'w-full text-ink-2')}>Invite another guest</Link>
        </>
      }
    >
      <div className="flex flex-col gap-5 animate-rise">
        <h1 className="display-md">{guest}'s invite is <span className="accent">ready.</span></h1>
        <div className="flex flex-wrap gap-2">
          <Pill tone="gold">{LANG_NAMES[lang]}</Pill>
          {(parsed.functions ?? []).map((f) => <Pill key={f}>{f}</Pill>)}
        </div>

        {/* The invite as a printed card */}
        <div className="relative rounded-[26px] bg-card p-7 shadow-lift ring-1 ring-line">
          <div className="pointer-events-none absolute inset-3 rounded-[18px] border border-gold/60" />
          <div className="pointer-events-none absolute inset-[17px] rounded-[15px] border border-gold/30" />
          <div className="relative flex justify-center"><Seal size={44} /></div>
          {editing ? (
            <textarea className="field relative mt-4 min-h-[220px]" value={text} onChange={(e) => setText(e.target.value)} lang={lang} />
          ) : (
            <p className="relative mt-4 whitespace-pre-line text-center font-display text-[1.12rem] leading-relaxed" lang={lang}>
              {text.split('\n').filter((l) => !/https?:\/\//.test(l)).join('\n').trim()}
            </p>
          )}
        </div>

        <div className="card flex items-center gap-3 p-4">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-safe-soft text-safe"><ICheck size={20} strokeWidth={2.6} /></span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold text-safe">Verified invite</div>
            <a href={last.invite_url} target="_blank" rel="noreferrer" className="block truncate font-mono text-[0.9rem] text-ink-2 underline-offset-2 hover:underline"><ILink size={14} className="mr-1 inline" />{short}</a>
          </div>
        </div>
        <HearButton audio={last.audio_b64} text={text} lang={lang} label="Play the voice note" />

        <p className="text-center text-[0.95rem] text-ink-3">A link, never a file. Guests can tell it's really you.</p>
      </div>
    </AppShell>
  )
}
