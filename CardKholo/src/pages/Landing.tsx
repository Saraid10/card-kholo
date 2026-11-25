import { Link } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { Ornament } from '../components/AppShell'
import { ICalPlus, IPlay, ITelegram, IX, IMic, IArrowRight } from '../components/Icons'
import { btnClass, Dot, FileName, Logo, Seal, Stamp } from '../components/ui'
import { useUser } from '../state/user'

export default function Landing() {
  const { user } = useUser()
  const startHref = user ? (user.role === 'host' ? '/host' : user.role === 'child' ? '/link' : '/check') : '/start'

  return (
    <div className="paper-bg overflow-x-clip text-ink">
      {/* ---------- Nav ---------- */}
      <header className="sticky top-0 z-30 border-b border-line/70 bg-paper/85 backdrop-blur-md">
        <div className="mx-auto flex h-[72px] max-w-[1240px] items-center justify-between gap-4 px-5 sm:px-8">
          <Logo />
          <nav className="hidden items-center gap-8 whitespace-nowrap text-[0.98rem] text-ink-2 lg:flex">
            <a href="#how" className="hover:text-ink">How it works</a>
            <a href="#family" className="hover:text-ink">For families</a>
            <a href="#hosts" className="hover:text-ink">For hosts</a>
            <Link to="/status" className="hover:text-ink">Control room</Link>
          </nav>
          <Link to={startHref} className={btnClass("primary", "md", "whitespace-nowrap")}>Check a card</Link>
        </div>
      </header>

      {/* ---------- Hero ---------- */}
      <section className="relative">
        <div className="mx-auto grid max-w-[1240px] items-center gap-12 px-5 pb-20 pt-10 sm:px-8 md:pt-16 lg:grid-cols-[1.08fr_1fr] lg:gap-16 lg:pb-28">
          <div className="animate-rise">
            <div className="mb-7 flex items-center gap-3 text-sm text-ink-2">
              <span className="whitespace-nowrap font-medium text-wine">Card Kholo</span>
              <span className="hidden h-px w-10 shrink-0 bg-line sm:block" />
              <span className="hidden sm:inline">the safe way to open a wedding card</span>
              <span className="sm:hidden">·&nbsp; safe wedding cards</span>
            </div>
            <h1 className="display-xl">
              Every scam says <span className="accent">don't tell</span> your family.
            </h1>
            <p className="mt-5 font-display text-[clamp(1.6rem,3vw,2.2rem)] italic text-wine">We tell them.</p>
            <p className="mt-6 max-w-[34rem] text-[1.12rem] leading-relaxed text-ink-2">
              Forward any wedding invite from WhatsApp. Real cards go to your calendar. Fake ones are stopped before
              you tap, explained out loud in your language, and your family hears about it the same second.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to={startHref} className={btnClass('primary', 'lg')}>Check a card <IArrowRight size={20} /></Link>
              <Link to="/start?role=host" className={btnClass('outline', 'lg')}>I'm sending invites</Link>
            </div>
            <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-ink-3">
              <span>Runs on</span>
              <span className="font-semibold text-ink-2">Sarvam AI</span>
              <span className="font-semibold text-ink-2">Flagsmith</span>
              <span className="font-semibold text-ink-2">NudgeBee</span>
            </div>
          </div>

          <HeroStage />
        </div>
      </section>

      {/* ---------- Three answers ---------- */}
      <section id="how" className="border-y border-line bg-card/60">
        <div className="mx-auto max-w-[1240px] px-5 py-20 sm:px-8 lg:py-28">
          <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr] lg:items-end">
            <h2 className="display-lg">Forward a card. Get <span className="accent">one of three</span> answers.</h2>
            <p className="max-w-[36rem] text-lg text-ink-2 lg:justify-self-end">
              Rules catch the known tricks first, then Sarvam reads the card itself. You never have to open anything to find out.
            </p>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            <AnswerCard kind="SAFE" file="Wedding_Invite_Priya.pdf" text="It's a real card. Every function, mehendi to reception, lands in your calendar with the venue on the map." />
            <AnswerCard kind="CHECK" file="bit.ly/priya-shaadi" text="Something looks off. A short link or an install-to-view message. We tell you exactly what and why." />
            <AnswerCard kind="STOP" file="Shaadi_Card_Priya.pdf.apk" text="It's a trap, not a card. A voice warning in Hindi, Kannada or English, and an alert to your family on Telegram." />
          </div>
          <div className="mt-14 flex flex-col items-center gap-3 text-center">
            <div className="rule-double w-24" />
            <p className="font-display text-[clamp(1.5rem,3vw,2.1rem)] italic text-maroon">Real families send links. Thieves send files.</p>
          </div>
        </div>
      </section>

      {/* ---------- Family ---------- */}
      <section id="family" className="mx-auto grid max-w-[1240px] items-center gap-12 px-5 py-20 sm:px-8 lg:grid-cols-2 lg:gap-20 lg:py-28">
        <div>
          <div className="eyebrow mb-4 text-wine">For families</div>
          <h3 className="display-lg">Your family <span className="accent">knows first.</span></h3>
          <p className="mt-5 max-w-[32rem] text-lg text-ink-2">
            Link your son or daughter once with a QR code. When a fake card reaches you, their phone buzzes. Most scams depend on
            you staying quiet. This one can't.
          </p>
          <Link to="/start?role=child" className={`${btnClass('outline', 'md')} mt-8`}>Get alerts for my parents</Link>
        </div>
        <div className="relative mx-auto w-full max-w-[420px]">
          <div className="absolute -inset-6 -z-10 rounded-[40px] bg-blush/50" />
          <div className="rotate-[-1.5deg] rounded-[28px] bg-night p-5 text-paper shadow-lift">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#6f8196] text-white"><ITelegram size={22} /></span>
              <div className="flex-1">
                <div className="text-sm font-semibold">Card Kholo</div>
                <div className="text-xs text-paper/60">now</div>
              </div>
              <Dot tone="stop" pulse />
            </div>
            <p className="mt-4 text-[1.02rem] leading-relaxed">
              <b>Papa just got a fake wedding card</b> (<span className="font-mono text-[0.9rem] text-gold-2">Shaadi_Card_Priya.pdf.apk</span>).
              It's an app that can read SMS. We warned him not to open it. Call him now.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm font-semibold">
              <span className="rounded-xl bg-white/10 py-2.5 text-center">Called him</span>
              <span className="rounded-xl bg-white/10 py-2.5 text-center">This was a real invite</span>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- Hosts ---------- */}
      <section id="hosts" className="maroon-bg relative overflow-hidden text-paper">
        <Ornament className="pointer-events-none absolute -left-40 -bottom-40 h-[560px] w-[560px] opacity-[.14]" />
        <div className="relative mx-auto grid max-w-[1240px] items-center gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1.1fr_1fr] lg:gap-20 lg:py-28">
          <div>
            <div className="eyebrow mb-4 text-gold-2">For hosts</div>
            <h3 className="display-lg">Hosting? Just <span className="accent-gold">say</span> who to invite.</h3>
            <p className="mt-5 max-w-[32rem] text-lg text-paper/80">
              Speak in Hindi or Kannada. We write the invite in your guest's language and open WhatsApp with a verified link, never a file.
            </p>
            <Link to="/start?role=host" className={`${btnClass('gold', 'lg')} mt-8`}>Start sending invites</Link>
          </div>
          <div className="rounded-[28px] border border-gold/40 bg-white/[.06] p-6 backdrop-blur sm:p-8">
            <div className="flex items-center gap-4">
              <span className="grid h-16 w-16 place-items-center rounded-full bg-marigold text-night">
                <IMic size={28} />
              </span>
              <Waveform />
            </div>
            <p className="mt-6 font-display text-[1.45rem] italic leading-snug text-paper">
              “Sharma ji ko Hindi mein invite bhejo, mehendi aur reception ke liye.”
            </p>
            <div className="mt-6 rounded-2xl bg-paper p-4 text-ink">
              <div className="flex items-center justify-between text-sm">
                <span className="eyebrow text-safe">Verified invite</span>
                <span className="font-mono text-ink-2">cardkholo.app/i/k3P9xQ</span>
              </div>
              <p className="mt-2 text-[0.98rem]" lang="hi">आदरणीय शर्मा जी, अग्रवाल परिवार आपको प्रिया और अर्जुन के विवाह में सादर आमंत्रित करता है।</p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- Ops ---------- */}
      <section className="mx-auto grid max-w-[1240px] items-center gap-12 px-5 py-20 sm:px-8 lg:grid-cols-2 lg:gap-20 lg:py-28">
        <div>
          <div className="eyebrow mb-4 text-wine">Under the hood</div>
          <h3 className="display-lg">New scam today? <span className="accent">New rule</span> in minutes.</h3>
          <p className="mt-5 max-w-[34rem] text-lg text-ink-2">
            Scam rules ship as Flagsmith flags, first to 20% of users. If a rule starts flagging real invites, NudgeBee opens an
            incident and the rule is rolled back after one approval. No redeploy.
          </p>
          <ol className="mt-8 space-y-3 border-l-2 border-line pl-5 text-[0.98rem]">
            <li><span className="font-mono text-ink-3">14:27</span> &nbsp;pack_broad_test on for 20% of users</li>
            <li><span className="font-mono text-ink-3">14:31</span> &nbsp;3 real invites flagged, incident opened</li>
            <li><span className="font-mono text-ink-3">14:32</span> &nbsp;<b className="text-safe">Approved. Rolled back automatically</b></li>
          </ol>
        </div>
        <div className="card overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-line px-6 py-4">
            <span className="font-display text-xl">Scam rule packs</span>
            <span className="flex items-center gap-2 text-sm text-safe"><Dot tone="safe" pulse /> Live</span>
          </div>
          {[
            ['pack_core', '0 false alarms', true],
            ['pack_wedding_2026', '0 false alarms', true],
            ['pack_broad_test', 'Rolled back at 14:32', false],
          ].map(([n, s, on]) => (
            <div key={n as string} className="flex items-center justify-between border-b border-line/70 px-6 py-4 last:border-0">
              <div>
                <div className="font-mono text-[0.95rem]">{n}</div>
                <div className={`text-sm ${on ? 'text-ink-3' : 'text-check'}`}>{s}</div>
              </div>
              <span className={`relative h-7 w-12 rounded-full ${on ? 'bg-safe' : 'bg-line'}`} aria-label={on ? 'On' : 'Off'}>
                <span className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all ${on ? 'left-6' : 'left-1'}`} />
              </span>
            </div>
          ))}
          <Link to="/status" className="flex items-center justify-between bg-paper-2 px-6 py-4 text-[0.98rem] font-semibold text-maroon no-underline hover:bg-blush/40">
            Open the control room <IArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* ---------- Three steps + QR ---------- */}
      <section className="border-t border-line bg-card/60">
        <div className="mx-auto max-w-[1240px] px-5 py-20 sm:px-8 lg:py-28">
          <h2 className="display-lg text-center">Three steps. <span className="accent">No app</span> to install.</h2>
          <div className="mt-14 grid gap-10 md:grid-cols-3 md:gap-8">
            {[
              ['Forward the invite', 'Photo, PDF, link or the file itself, straight from WhatsApp.'],
              ['Rules check it first', 'Hidden apps, fake links and known scam patterns are caught before any AI reads the card.'],
              ['Get dates or a warning', 'In your language, read out loud if you want.'],
            ].map(([h, p], i) => (
              <div key={h} className="text-center md:text-left">
                <div className="mx-auto grid h-14 w-14 place-items-center rounded-full border border-gold font-display text-2xl italic text-wine md:mx-0">{i + 1}</div>
                <h4 className="mt-5 font-display text-[1.6rem] leading-tight">{h}</h4>
                <p className="mt-2 text-ink-2">{p}</p>
              </div>
            ))}
          </div>

          <div className="mt-20 grid items-center gap-8 rounded-[32px] bg-maroon p-8 text-paper sm:p-12 md:grid-cols-[1fr_auto]">
            <div>
              <h3 className="display-md text-paper">Try it with a card you <span className="accent-gold">already have.</span></h3>
              <p className="mt-3 text-paper/75">Scan with your phone camera, then forward any invite.</p>
              <Link to={startHref} className={`${btnClass('gold', 'lg')} mt-7`}>Check a card now</Link>
            </div>
            <div className="justify-self-center rounded-2xl bg-paper p-4 md:justify-self-end">
              <QRCodeSVG value={typeof window !== 'undefined' ? `${window.location.origin}/start` : 'https://cardkholo.app/start'} size={170} fgColor="#22181A" bgColor="#F7F1E7" />
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1240px] flex-col items-start justify-between gap-4 px-5 py-10 text-sm text-ink-3 sm:flex-row sm:items-center sm:px-8">
          <div className="flex items-center gap-3"><Seal size={26} /> Made for Festive Hacks 2026, Bengaluru</div>
          <div>We read your card, then delete it. Nothing from your invite is stored.</div>
        </div>
      </footer>
    </div>
  )
}

/* WhatsApp message → forwarded → two answers: STOP and SAFE */
function HeroStage() {
  return (
    <div className="relative mx-auto w-full max-w-[560px] animate-rise [animation-delay:.12s]">
      <div className="absolute -inset-8 -z-10 rounded-[48px] bg-[radial-gradient(closest-side,rgb(230_214_204/.8),transparent)]" />

      {/* Incoming WhatsApp bubble */}
      <div className="relative z-10 sm:w-[310px]">
        <div className="card rounded-tl-md p-4">
          <div className="flex items-center gap-2 text-xs text-ink-3">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-paper-2 text-ink-2">?</span>
            +91 98290 4xxxx <span className="ml-auto whitespace-nowrap rounded bg-check-soft px-1.5 py-0.5 text-[0.7rem] text-check">Not in contacts</span>
          </div>
          <p className="mt-2 text-[0.95rem]">Namaste ji 🙏 Priya ki shaadi ka card bhej rahe hain, zaroor aayein</p>
          <div className="mt-2 flex items-center gap-3 rounded-xl bg-paper-2 p-2.5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-stop text-[0.7rem] font-bold text-white">APK</span>
            <div className="min-w-0">
              <div className="truncate font-mono text-[0.8rem]">Shaadi_Card_Priya.pdf.apk</div>
              <div className="text-xs text-ink-3">6.2 MB</div>
            </div>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2 pl-4 text-sm font-medium text-wine">
          <span className="h-6 w-px bg-gold" aria-hidden="true" />
          Forward to Card Kholo <IArrowRight size={16} className="rotate-90 sm:rotate-0" />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:-mt-8 sm:gap-4 sm:pl-10">
        {/* STOP phone */}
        <div className="relative rotate-[-2.5deg] rounded-[26px] bg-stop p-4 text-paper shadow-lift sm:mt-10 sm:p-5">
          <div className="flex items-center gap-1.5 text-[0.7rem] text-paper/80"><ITelegram size={13} /> Rohan told on Telegram</div>
          <div className="mt-3 font-mono text-[0.7rem] leading-tight text-paper/85"><FileName name="Shaadi_Card_Priya.pdf.apk" /></div>
          <Stamp kind="STOP" light size="sm" className="mt-3 sm:text-[1.4rem]" />
          <p className="mt-3 text-[0.82rem] leading-snug">This isn't a wedding card. It's an app that can read your bank OTPs.</p>
          <div className="mt-3 hidden items-center gap-2 rounded-xl bg-white/12 p-2 text-[0.75rem] sm:flex" lang="hi">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-paper text-stop"><IPlay size={12} /></span>
            “रुकिए। यह शादी का कार्ड नहीं है।”
          </div>
          <ul className="mt-3 hidden space-y-1 text-[0.72rem] text-paper/85 sm:block">
            <li className="flex gap-1.5"><IX size={13} /> File ends in .apk, not .pdf</li>
            <li className="flex gap-1.5"><IX size={13} /> Sender not in your contacts</li>
          </ul>
          <div className="mt-4 rounded-full bg-paper py-2 text-center text-[0.75rem] font-semibold text-stop">I already opened it</div>
        </div>

        {/* SAFE phone */}
        <div className="relative rotate-[2deg] rounded-[26px] bg-card p-4 shadow-lift ring-1 ring-line sm:mt-24 sm:p-5">
          <div className="font-mono text-[0.7rem] leading-tight text-ink-3"><FileName name="Wedding_Invite_Priya.pdf" /></div>
          <Stamp kind="SAFE" size="sm" className="mt-3 sm:text-[1.4rem]" />
          <p className="mt-3 text-[0.82rem] leading-snug"><span className="font-display italic text-wine">Priya weds Arjun.</span> 4 functions found.</p>
          <div className="mt-2 divide-y divide-line text-[0.75rem]">
            {[['Dec 4', 'Mehendi', '4 PM'], ['Dec 5', 'Sangeet', '7 PM'], ['Dec 7', 'Reception', '8 PM']].map(([d, n, t]) => (
              <div key={n} className="flex items-center gap-2 py-1.5">
                <span className="w-9 shrink-0 font-semibold text-wine">{d}</span>
                <span className="min-w-0 flex-1 truncate"><b>{n}</b> <span className="hidden text-ink-3 sm:inline">{t}</span></span>
                <ICalPlus size={14} className="shrink-0 text-ink-2" />
              </div>
            ))}
          </div>
          <div className="mt-3 rounded-full bg-ink py-2 text-center text-[0.75rem] font-semibold text-paper">Add all to calendar</div>
        </div>
      </div>
    </div>
  )
}

function AnswerCard({ kind, file, text }: { kind: 'SAFE' | 'CHECK' | 'STOP'; file: string; text: string }) {
  const bar = { SAFE: 'bg-safe', CHECK: 'bg-check', STOP: 'bg-stop' }[kind]
  return (
    <div className="card lift relative overflow-hidden p-6 pt-7">
      <span className={`absolute inset-x-0 top-0 h-1.5 ${bar}`} />
      <div className="truncate font-mono text-sm text-ink-3">{file}</div>
      <Stamp kind={kind} size="lg" animate={false} className="mt-5 max-sm:text-[2rem]" />
      <p className="mt-6 text-[1.02rem] text-ink-2">{text}</p>
    </div>
  )
}

function Waveform() {
  return (
    <div className="flex h-12 flex-1 items-center gap-[3px]" aria-hidden="true">
      {Array.from({ length: 34 }).map((_, i) => (
        <span key={i} className="w-[3px] rounded-full bg-gold-2/80" style={{ height: `${18 + Math.abs(Math.sin(i * 0.7) * 70) + (i % 3) * 6}%` }} />
      ))}
    </div>
  )
}
