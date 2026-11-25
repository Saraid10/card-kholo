import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import { QRCodeSVG } from 'qrcode.react'
import AppShell from '../components/AppShell'
import { ITelegram, IWhatsApp } from '../components/Icons'
import { btnClass, CopyButton, Dot } from '../components/ui'
import { fill } from '../i18n/strings'
import { BOT_USERNAME } from '../lib/env'
import { getChild, saveChild } from '../state/scans'
import { useUser } from '../state/user'

/** Polls GET /api/pairing/{user_id} every 4 s until linked. Stops quietly on 404 / error. */
function usePairing(userId: string | undefined, enabled: boolean): string | null {
  const [child, setChild] = useState<string | null>(() => getChild()?.child_name ?? null)
  useEffect(() => {
    if (!userId || !enabled || child) return
    let stopped = false
    let timer: number | undefined
    const tick = async () => {
      try {
        const r = await api.pairing(userId)
        if (stopped) return
        if (r.linked) {
          const name = r.child_name || 'Your family'
          saveChild(name)
          setChild(name)
          return
        }
        timer = window.setTimeout(tick, 4000)
      } catch (e) {
        // 404: route missing, stop quietly. Anything else (cold start, network blip): keep polling.
        if (!stopped && !(e instanceof ApiError && e.status === 404)) timer = window.setTimeout(tick, 4000)
      }
    }
    tick()
    return () => { stopped = true; window.clearTimeout(timer) }
  }, [userId, enabled, child])
  return child
}

export default function LinkFamily() {
  const { user, t } = useUser()
  const child = usePairing(user?.user_id, user?.role !== 'child')
  if (!user) return <Navigate to="/start" replace />

  // Child: nothing to scan here, explain how pairing works from their side.
  if (user.role === 'child') {
    const bot = BOT_USERNAME || 'CardKholoBot'
    return (
      <AppShell back="/start" center={t('step2')} aside={{ eyebrow: 'For the family IT support', title: <>Every scam says don't tell your family. <span className="accent-gold">Card Kholo tells your family.</span></> }}
        footer={<Link to="/check" className={btnClass('primary', 'lg', 'w-full')}>{t('checkCard')}</Link>}>
        <div className="flex flex-col gap-6 animate-rise">
          <h1 className="display-md">{t('childTitle')}</h1>
          <p className="text-ink-2">{t('childSub')}</p>
          <div className="card flex items-center gap-4 p-5">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#6f8196] text-white"><ITelegram size={24} /></span>
            <div className="flex-1">
              <div className="font-semibold">@{bot}</div>
              <div className="text-sm text-ink-2">Alerts arrive here, with “Called them” and “This was a real invite” buttons.</div>
            </div>
          </div>
          <a href={`https://t.me/${bot}`} target="_blank" rel="noreferrer" className={btnClass('outline', 'md')}>Open the bot in Telegram</a>
        </div>
      </AppShell>
    )
  }

  const link = user.pair_link ?? `https://t.me/${BOT_USERNAME || 'CardKholoBot'}?start=${user.user_id}`
  const wa = `https://wa.me/?text=${encodeURIComponent(`${t('linkWaMsg')} ${link}`)}`

  return (
    <AppShell
      back="/start"
      center={t('step2')}
      aside={{
        eyebrow: 'Step 2 of 2',
        title: <>Every scam says don't tell your family. <span className="accent-gold">We tell them.</span></>,
        body: 'One scan links a son or daughter. When a fake card reaches this phone, theirs buzzes on Telegram at the same second.',
      }}
      footer={
        <>
          <Link to="/check" className={btnClass('primary', 'lg', 'w-full')}>{t('linkDone')}</Link>
          <Link to="/check" className={btnClass('ghost', 'md', 'w-full text-ink-2')}>{t('skip')}</Link>
        </>
      }
    >
      <div className="flex flex-col gap-6 animate-rise">
        <div>
          <h1 className="display-md">{t('linkTitle')}</h1>
          <p className="mt-2 text-ink-2">{t('linkSub')}</p>
        </div>

        <div className="card relative mx-auto w-full max-w-[340px] p-6 text-center">
          <div className="absolute inset-3 rounded-[16px] border border-gold/50" aria-hidden="true" />
          <div className="relative mx-auto w-fit rounded-xl bg-paper p-3" role="img" aria-label="QR code that opens the Card Kholo Telegram bot">
            <QRCodeSVG value={link} size={200} fgColor="#22181A" bgColor="#F7F1E7" level="M" />
          </div>
          <p className="relative mt-4 text-[0.95rem] text-ink-2">{t('linkHow')}</p>
          <div role="status" className={`relative mt-4 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium ${child ? 'bg-safe-soft text-safe' : 'bg-paper-2 text-ink-2'}`}>
            {child ? <><Dot tone="safe" /> {fill(t('isLinked'), { name: child })}</> : <><Dot tone="gold" pulse /> {t('waiting')}</>}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2.5 min-[420px]:grid-cols-2">
          <a href={wa} target="_blank" rel="noreferrer" className={btnClass('outline', 'md')}>
            <IWhatsApp size={20} className="text-[#55705d]" /> {t('sendWhatsApp')}
          </a>
          <CopyButton text={link} label={t('copyLink')} done={t('copied')} />
        </div>
      </div>
    </AppShell>
  )
}
