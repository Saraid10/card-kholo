import { useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, type Lang, type Role } from '../api'
import AppShell from '../components/AppShell'
import { IBank, ICheck, IMic, IShield, ITelegram } from '../components/Icons'
import { Button, ErrorNote, Spinner } from '../components/ui'
import { LANG_LABELS } from '../i18n/strings'
import { errorKey } from '../lib/errors'
import { useUser } from '../state/user'

const isRole = (r: string | null): r is Role => r === 'parent' || r === 'child' || r === 'host'

export default function Welcome() {
  const [params] = useSearchParams()
  const nav = useNavigate()
  const { user, lang, setLang, saveUser, t } = useUser()
  const initialRole = params.get('role')
  const [name, setName] = useState(user?.name ?? '')
  const [role, setRole] = useState<Role>(isRole(initialRole) ? initialRole : user?.role ?? 'parent')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [nameErr, setNameErr] = useState(false)

  async function submit() {
    if (!name.trim()) {
      setNameErr(true)
      return
    }
    setBusy(true)
    setErr(null)
    try {
      const beta = params.get('beta') === '1'
      const res = await api.identify({ name: name.trim(), lang, role, beta })
      saveUser({ user_id: res.user_id, name: name.trim(), lang, role, beta, pair_link: res.pair_link })
      nav(role === 'host' ? '/host' : '/link')
    } catch (e) {
      setErr(t(errorKey(e)))
    } finally {
      setBusy(false)
    }
  }

  const roles: { r: Role; title: string; sub: string; icon: ReactNode }[] = [
    { r: 'parent', title: t('roleParent'), sub: t('roleParentSub'), icon: <IShield size={24} /> },
    { r: 'child', title: t('roleChild'), sub: t('roleChildSub'), icon: <ITelegram size={22} /> },
    { r: 'host', title: t('roleHost'), sub: t('roleHostSub'), icon: <IMic size={22} /> },
  ]

  return (
    <AppShell
      back="/"
      center={t('step1')}
      hideLang
      aside={{
        eyebrow: 'Step 1 of 2',
        title: <>Nobody installs a scam app. Everyone wants the <span className="accent-gold">wedding date</span> in their calendar.</>,
        body: 'The safety rides along. Pick your language once: every warning, summary and step is spoken in it.',
      }}
      footer={
        <Button onClick={submit} disabled={busy} className="w-full">
          {busy ? <Spinner /> : t('continue')}
        </Button>
      }
    >
      <form className="flex flex-col gap-7 animate-rise" onSubmit={(e) => { e.preventDefault(); submit() }}>
        <div>
          <h1 className="display-md">{t('welcomeTitle')}</h1>
          <p className="mt-2 text-ink-2">{t('welcomeSub')}</p>
        </div>

        <label className="block">
          <span className="mb-2 block text-[0.95rem] font-medium text-ink-2">{t('yourName')}</span>
          <input
            className="field"
            value={name}
            autoComplete="name"
            placeholder={t('namePh')}
            aria-invalid={nameErr}
            onChange={(e) => { setName(e.target.value); setNameErr(false) }}
          />
          {nameErr && <span className="mt-2 block text-sm text-stop">{t('nameNeeded')}</span>}
        </label>

        <fieldset>
          <legend className="mb-2 text-[0.95rem] font-medium text-ink-2">{t('voiceIn')}</legend>
          <div className="grid grid-cols-3 gap-2">
            {(['hi', 'kn', 'en'] as Lang[]).map((l) => (
              <button
                key={l}
                type="button"
                lang={l}
                aria-pressed={lang === l}
                onClick={() => setLang(l)}
                className={`min-h-[56px] rounded-2xl text-[1.1rem] font-semibold transition-all ${
                  lang === l ? 'bg-maroon text-paper shadow-md' : 'bg-card text-ink ring-1 ring-line hover:ring-ink-3'
                }`}
              >
                {LANG_LABELS[l]}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-2 text-[0.95rem] font-medium text-ink-2">{t('iWantTo')}</legend>
          <div className="flex flex-col gap-2.5" role="radiogroup">
            {roles.map(({ r, title, sub, icon }) => {
              const on = role === r
              return (
                <button
                  key={r}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => setRole(r)}
                  className={`flex items-center gap-4 rounded-[20px] p-4 text-left transition-all ${
                    on ? 'bg-card ring-2 ring-maroon shadow-[var(--shadow-card)]' : 'bg-card/60 ring-1 ring-line hover:bg-card'
                  }`}
                >
                  <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-full ${on ? 'bg-maroon text-gold-2' : 'bg-paper-2 text-ink-2'}`}>{icon}</span>
                  <span className="flex-1">
                    <span className="block text-[1.08rem] font-semibold leading-tight">{title}</span>
                    <span className="block text-[0.92rem] text-ink-2">{sub}</span>
                  </span>
                  <span className={`grid h-6 w-6 place-items-center rounded-full border-2 ${on ? 'border-maroon bg-maroon text-paper' : 'border-line'}`}>
                    {on && <ICheck size={14} strokeWidth={3} />}
                  </span>
                </button>
              )
            })}
          </div>
        </fieldset>

        {err && <ErrorNote message={err} onRetry={submit} retryLabel={t('retry')} />}
        <button type="submit" hidden />
        <p className="flex items-center gap-2 text-sm text-ink-3"><IBank size={16} /> {t('privacy')}</p>
      </form>
    </AppShell>
  )
}
