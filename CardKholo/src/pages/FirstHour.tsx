import { useEffect, useState, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { api, type OpenedRes } from '../api'
import AppShell from '../components/AppShell'
import { IBank, IChevron, IGlobe, IPhone, IPlane, ITrash, IWhatsApp } from '../components/Icons'
import { HearButton } from '../components/Voice'
import { btnClass, CopyButton } from '../components/ui'
import { fill, type StringKey } from '../i18n/strings'
import { getScan } from '../state/scans'
import { useUser } from '../state/user'

export default function FirstHour() {
  const { scanId = '' } = useParams()
  const { lang, t } = useUser()
  const saved = getScan(scanId)
  const file = saved?.label ?? 'Wedding_Card.apk'
  const [opened, setOpened] = useState<OpenedRes | null>(null)

  useEffect(() => {
    let live = true
    if (scanId) api.opened(scanId).then((r) => live && setOpened(r)).catch(() => {})
    return () => { live = false }
  }, [scanId])

  const steps: { k: StringKey; sub?: string | ReactNode; icon: ReactNode }[] = [
    { k: 'stepAirplane', sub: t('stepAirplaneSub'), icon: <IPlane size={22} /> },
    { k: 'stepBank', sub: t('stepBankSub'), icon: <IBank size={22} /> },
    { k: 'stepReport', sub: <a href="https://cybercrime.gov.in" target="_blank" rel="noreferrer" className="font-medium text-wine underline underline-offset-2">cybercrime.gov.in</a>, icon: <IGlobe size={22} /> },
    { k: 'stepRemove', sub: t('stepRemoveSub'), icon: <ITrash size={22} /> },
  ]
  const complaint = fill(t('complaint'), { file, date: new Date().toLocaleDateString('en-IN') })
  const spoken = opened?.steps?.length && lang === 'en'
    ? opened.steps.join(' ')
    : [`1. ${t('call1930')}: 1930.`, ...steps.map((s, i) => `${i + 2}. ${t(s.k)}.`)].join(' ')
  const wa = `https://wa.me/?text=${encodeURIComponent(fill(t('tellFamilyMsg'), { file }))}`

  return (
    <AppShell
      back={`/result/${scanId}`}
      right={<HearButton audio={opened?.audio_b64} text={spoken} lang={lang} label={t('hearSteps')} />}
      hideLang
      aside={{ eyebrow: 'The first hour', title: <>Opened it? <span className="accent-gold">Don't panic.</span> Do these, in order.</>, body: 'Speed matters more than anything else. Call 1930 first; the national helpline can freeze money in transit if you report quickly.' }}
      footer={<a href={wa} target="_blank" rel="noreferrer" className={btnClass('outline', 'lg', 'w-full')}><IWhatsApp size={20} className="text-[#55705d]" /> {t('tellFamily')}</a>}
    >
      <div className="flex flex-col gap-5 animate-rise">
        <h1 className="display-md">{t('firstHourTitle')}</h1>

        <a href="tel:1930" className="group relative flex items-center gap-4 overflow-hidden rounded-[24px] bg-stop p-5 text-paper no-underline shadow-lift">
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-paper text-stop animate-pulse-ring"><IPhone size={26} /></span>
          <span className="flex-1">
            <span className="block text-[0.95rem] text-paper/85">1. {t('call1930')}</span>
            <span className="block font-display text-[2.6rem] leading-none tracking-tight">1930</span>
          </span>
          <IChevron size={24} className="transition-transform group-hover:translate-x-1" />
        </a>

        <ol className="card stagger divide-y divide-line/80 p-0">
          {steps.map((s, i) => (
            <li key={s.k} className="flex items-start gap-4 p-4 sm:p-5">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-paper-2 text-maroon">{s.icon}</span>
              <div className="flex-1">
                <div className="text-[1.08rem] font-semibold"><span className="mr-1.5 font-display italic text-wine">{i + 2}</span>{t(s.k)}</div>
                <div className="text-[0.95rem] text-ink-2">{s.sub}</div>
                {s.k === 'stepReport' && (
                  <div className="mt-3 rounded-2xl bg-paper-2/70 p-3">
                    <p className="text-[0.9rem] text-ink-2">{complaint}</p>
                    <CopyButton text={complaint} label={t('copyText')} done={t('copied')} className="mt-3" />
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </AppShell>
  )
}
