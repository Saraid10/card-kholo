import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { api, type WeddingFunction } from '../../api'
import { DEMO_FUNCTIONS } from '../../api/mocks'
import AppShell from '../../components/AppShell'
import { IClose } from '../../components/Icons'
import { Button, ErrorNote, Spinner } from '../../components/ui'
import { buildGcalUrl, buildMapsUrl } from '../../lib/calendar'
import { errorKey } from '../../lib/errors'
import { getHost, saveHost } from '../../state/scans'
import { useUser } from '../../state/user'

const blank: WeddingFunction = { name: '', date: '', time: '', venue_name: '', city: '' }

export default function HostSetup() {
  const { user, t } = useUser()
  const nav = useNavigate()
  const prev = getHost()
  const [couple, setCouple] = useState(prev?.couple ?? '')
  const [family, setFamily] = useState(prev?.host_family ?? '')
  const [fns, setFns] = useState<WeddingFunction[]>(prev?.functions?.length ? prev.functions : [{ ...blank }])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  if (!user) return <Navigate to="/start?role=host" replace />

  const set = (i: number, p: Partial<WeddingFunction>) => setFns((f) => f.map((x, j) => (j === i ? { ...x, ...p } : x)))
  const useDemo = () => {
    setCouple('Priya weds Arjun')
    setFamily('Agarwal family')
    setFns(DEMO_FUNCTIONS.map(({ gcal_url: _g, maps_url: _m, ...f }) => f))
  }

  async function submit() {
    setErr(null)
    const clean = fns
      .filter((f) => f.name?.trim())
      .map((f) => {
        const location = [f.venue_name, f.venue_address, f.city].filter(Boolean).join(', ')
        // The backend requires every Function field as a string.
        return { name: '', name_original: '', date: '', time: '', venue_name: '', venue_address: '', city: '', ...f, gcal_url: buildGcalUrl({ title: `${f.name}: ${couple}`, date: f.date ?? '', time: f.time ?? '', location }) ?? '', maps_url: buildMapsUrl(location) }
      })
    if (!couple.trim() || !clean.length) {
      setErr('Add the couple and at least one function.')
      return
    }
    setBusy(true)
    try {
      const r = await api.createWedding({ user_id: user!.user_id, couple, host_family: family, functions: clean })
      saveHost({ wedding_id: r.wedding_id, couple, host_family: family, functions: clean })
      nav('/host/speak')
    } catch (e) {
      setErr(t(errorKey(e)))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShell
      back="/start?role=host"
      center="Your wedding"
      hideLang
      aside={{ eyebrow: 'For hosts', title: <>Real families send <span className="accent-gold">links,</span> never files.</>, body: 'Add the functions once. Then just say who to invite and in which language; every guest gets a verified link their phone can trust.' }}
      footer={<Button onClick={submit} disabled={busy} className="w-full">{busy ? <Spinner /> : 'Continue to invites'}</Button>}
    >
      <div className="flex flex-col gap-6 animate-rise">
        <div className="flex items-start justify-between gap-3">
          <h1 className="display-md">Tell us about the <span className="accent">wedding.</span></h1>
          <button type="button" onClick={useDemo} className="shrink-0 rounded-full bg-paper-2 px-3 py-1.5 text-sm font-medium text-ink-2 hover:bg-blush/60">Use demo</button>
        </div>

        <label className="block"><span className="mb-2 block text-[0.95rem] font-medium text-ink-2">Couple</span>
          <input className="field" placeholder="Priya weds Arjun" value={couple} onChange={(e) => setCouple(e.target.value)} />
        </label>
        <label className="block"><span className="mb-2 block text-[0.95rem] font-medium text-ink-2">Inviting family</span>
          <input className="field" placeholder="Agarwal family" value={family} onChange={(e) => setFamily(e.target.value)} />
        </label>

        <section className="flex flex-col gap-3">
          <h2 className="font-sans text-[0.95rem] font-medium tracking-normal text-ink-2">Functions</h2>
          {fns.map((f, i) => (
            <div key={i} className="card relative grid grid-cols-2 gap-2 p-4">
              {fns.length > 1 && (
                <button type="button" aria-label="Remove function" onClick={() => setFns((x) => x.filter((_, j) => j !== i))} className="absolute right-6 top-[26px] z-10 grid h-8 w-8 place-items-center rounded-full text-ink-3 hover:bg-paper-2">
                  <IClose size={16} />
                </button>
              )}
              <input className="field col-span-2 pr-12" placeholder="Mehendi" value={f.name ?? ''} onChange={(e) => set(i, { name: e.target.value })} aria-label="Function name" />
              <input type="date" className="field" value={f.date ?? ''} onChange={(e) => set(i, { date: e.target.value })} aria-label="Date" />
              <input type="time" className="field" value={f.time ?? ''} onChange={(e) => set(i, { time: e.target.value })} aria-label="Time" />
              <input className="field" placeholder="Venue" value={f.venue_name ?? ''} onChange={(e) => set(i, { venue_name: e.target.value })} aria-label="Venue" />
              <input className="field" placeholder="City" value={f.city ?? ''} onChange={(e) => set(i, { city: e.target.value })} aria-label="City" />
            </div>
          ))}
          <button type="button" onClick={() => setFns((x) => [...x, { ...blank }])} className="rounded-2xl border-[1.5px] border-dashed border-line py-3.5 font-medium text-ink-2 hover:border-ink-3 hover:text-ink">
            + Add a function
          </button>
        </section>

        {err && <ErrorNote message={err} />}
      </div>
    </AppShell>
  )
}
