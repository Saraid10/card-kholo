import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, type InviteRes } from '../api'
import { Ornament } from '../components/AppShell'
import FunctionList from '../components/FunctionList'
import { ICalPlus, IShield } from '../components/Icons'
import { HearButton } from '../components/Voice'
import { Button, ErrorNote, LangSwitch, Logo, Spinner } from '../components/ui'
import { fmtDay, fmtTime } from '../lib/format'
import { downloadIcs } from '../lib/ics'
import { useUser } from '../state/user'

export default function Invite() {
  const { inviteId = '' } = useParams()
  const { t } = useUser()
  const [inv, setInv] = useState<InviteRes | null>(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    api.invite(inviteId).then(setInv).catch(() => setErr(true))
  }, [inviteId])

  if (err) return <div className="mx-auto max-w-md p-6"><ErrorNote message={t('errServer')} /></div>
  if (!inv) return <div className="grid min-h-dvh place-items-center text-wine"><Spinner className="h-8 w-8" /></div>

  const fns = inv.functions ?? []
  const lang = inv.lang ?? 'hi'
  const spoken = lang === 'hi'
    ? `${inv.guest ?? ''}, ${inv.couple_original ?? inv.couple}। ` + fns.map((f) => `${f.name_original ?? f.name}, ${fmtDay(f.date, 'hi', { day: 'numeric', month: 'long' })}, ${fmtTime(f.time, 'hi')}, ${f.venue_name}।`).join(' ')
    : `${inv.guest ?? ''}, ${inv.host_family} invites you to ${inv.couple}. ` + fns.map((f) => `${f.name} on ${fmtDay(f.date, 'en', { day: 'numeric', month: 'long' })} at ${fmtTime(f.time, 'en')}, ${f.venue_name}.`).join(' ')

  return (
    <div className="min-h-dvh bg-paper">
      <header className="maroon-bg relative overflow-hidden text-paper">
        <Ornament />
        <div className="relative mx-auto max-w-[640px] px-5 pb-14 pt-5 sm:px-8">
          <div className="flex items-center justify-between gap-3">
            <Logo dark />
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 text-sm font-medium text-gold-2"><IShield size={16} /> Verified</span>
          </div>
          <div className="mt-12 text-center animate-rise">
            <p className="text-[1.05rem] text-paper/80">{inv.guest ? `${inv.guest}, the ` : 'The '}{inv.host_family ?? 'family'} invites you to</p>
            <h1 className="display-lg mt-4 italic text-paper">{inv.couple}</h1>
            {inv.couple_original && <p className="mt-3 font-display text-2xl text-gold-2" lang="hi">{inv.couple_original}</p>}
            <div className="mx-auto mt-7 w-28 rule-double" />
            <div className="mt-7 flex justify-center"><HearButton audio={inv.audio_b64} text={spoken} lang={lang} label="Hear the invite" dark /></div>
          </div>
        </div>
      </header>

      <main className="relative mx-auto -mt-6 flex max-w-[640px] flex-col gap-5 px-5 pb-12 sm:px-8">
        <FunctionList functions={fns} title={inv.couple ?? 'Wedding'} />
        <Button onClick={() => downloadIcs(inv.couple ?? 'Wedding', fns)} className="w-full"><ICalPlus size={20} /> {fns.length === 2 ? 'Add both to calendar' : `Add all ${fns.length} to calendar`}</Button>
        <p className="flex items-start gap-3 rounded-2xl bg-paper-2 p-4 text-[0.95rem] text-ink-2">
          <IShield size={20} className="mt-0.5 shrink-0 text-safe" />
          Card Kholo never sends files. A card that asks you to install an app is fake.
        </p>
        <div className="flex justify-center"><LangSwitch compact /></div>
      </main>
    </div>
  )
}
