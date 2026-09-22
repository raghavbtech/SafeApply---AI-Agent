import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Check,
  ChevronRight,
  Cpu,
  FileScan,
  Fingerprint,
  Inbox,
  Lock,
  Mail,
  Pause,
  Play,
  ScanLine,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  UserCheck,
} from 'lucide-react';
import { useSession } from '../auth/AuthProvider';

const features = [
  { icon: ShieldAlert, color: 'cyan', title: 'Job offer risk analysis', description: 'Spot urgency, payment requests, suspicious domains, and hidden recruitment signals before they cost you.' },
  { icon: Cpu, color: 'violet', title: 'Grounded AI detection', description: 'Rules, EMSCAD signals, retrieval, and explainable AI work together to surface evidence, not guesses.' },
  { icon: Inbox, color: 'blue', title: 'Mailbox threat review', description: 'Connect your mailbox when ready and keep suspicious recruiter messages in a controlled review loop.' },
  { icon: Lock, color: 'emerald', title: 'Private profile workspace', description: 'Your anonymous session keeps profile details, resumes, and scan history partitioned from other visitors.' },
  { icon: UserCheck, color: 'amber', title: 'Human-led applications', description: 'Match skills and draft applications while you keep the final say before anything is sent.' },
  { icon: Fingerprint, color: 'pink', title: 'No-account privacy', description: 'Start instantly without passwords or signup. Delete your session data whenever you choose.' },
];

const steps = [
  { number: '01', icon: UploadCloud, title: 'Bring the signal', description: 'Paste an offer, import an email, or connect your mailbox when you want a wider view.' },
  { number: '02', icon: ScanLine, title: 'See the evidence', description: 'SafeApply evaluates risk across multiple detection layers and explains the signals it found.' },
  { number: '03', icon: UserCheck, title: 'Choose the next move', description: 'Review the result, secure the message, or prepare a tailored application with control intact.' },
];

const accentClasses: Record<string, string> = {
  cyan: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-300 group-hover:border-cyan-300/50 group-hover:shadow-[0_0_30px_-12px_rgba(34,211,238,.8)]',
  violet: 'border-violet-400/20 bg-violet-400/10 text-violet-300 group-hover:border-violet-300/50 group-hover:shadow-[0_0_30px_-12px_rgba(167,139,250,.8)]',
  blue: 'border-blue-400/20 bg-blue-400/10 text-blue-300 group-hover:border-blue-300/50 group-hover:shadow-[0_0_30px_-12px_rgba(96,165,250,.8)]',
  emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300 group-hover:border-emerald-300/50 group-hover:shadow-[0_0_30px_-12px_rgba(52,211,153,.8)]',
  amber: 'border-amber-400/20 bg-amber-400/10 text-amber-300 group-hover:border-amber-300/50 group-hover:shadow-[0_0_30px_-12px_rgba(251,191,36,.8)]',
  pink: 'border-pink-400/20 bg-pink-400/10 text-pink-300 group-hover:border-pink-300/50 group-hover:shadow-[0_0_30px_-12px_rgba(244,114,182,.8)]',
};

type DemoScenario = {
  title: string;
  company: string;
  offer: string;
  score: number;
  assessment: string;
  assessmentColor: string;
  indicators: string[];
};

const demoScenarios: DemoScenario[] = [
  {
    title: 'Junior Software Developer',
    company: 'Example Software Solutions',
    offer: 'We would like to invite you to an interview for the Junior Software Developer position. Please reply with your availability.',
    score: 8,
    assessment: 'Low Risk',
    assessmentColor: 'emerald',
    indicators: ['No direct warning indicators identified in the example text.'],
  },
  {
    title: 'Software Developer Intern',
    company: 'Example Hiring Network',
    offer: 'We would like to continue your application. Please confirm your details through our external chat channel before scheduling the next step.',
    score: 38,
    assessment: 'Medium Risk',
    assessmentColor: 'amber',
    indicators: ['Limited employer detail in the example text', 'Request to move the conversation to an external channel'],
  },
  {
    title: 'Remote Software Developer',
    company: 'Example Recruitment Group',
    offer: 'Your selection is confirmed without an interview. Pay a refundable registration fee of ₹4,500 within 30 minutes to secure your position.',
    score: 92,
    assessment: 'High Risk',
    assessmentColor: 'rose',
    indicators: ['Upfront payment request', 'Artificial urgency', 'Selection promised without an interview'],
  },
];

const DEMO_CYCLE_MS = 10000;

const IllustrativeRiskDemo: React.FC = () => {
  const [scenarioIndex, setScenarioIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [userPaused, setUserPaused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const scenario = demoScenarios[scenarioIndex];
  const isPaused = userPaused || hovered || hidden || reducedMotion;

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotionPreference = () => setReducedMotion(mediaQuery.matches);
    updateMotionPreference();
    mediaQuery.addEventListener('change', updateMotionPreference);
    const updateVisibility = () => setHidden(document.hidden);
    document.addEventListener('visibilitychange', updateVisibility);
    return () => {
      mediaQuery.removeEventListener('change', updateMotionPreference);
      document.removeEventListener('visibilitychange', updateVisibility);
    };
  }, []);

  useEffect(() => {
    if (isPaused) return undefined;
    const timer = window.setInterval(() => {
      setElapsed((current) => {
        const next = current + 100;
        if (next >= DEMO_CYCLE_MS) {
          setScenarioIndex((index) => (index + 1) % demoScenarios.length);
          return 0;
        }
        return next;
      });
    }, 100);
    return () => window.clearInterval(timer);
  }, [isPaused]);

  const stage = elapsed < 2500 ? 'input' : elapsed < 5000 ? 'analyzing' : elapsed < 7200 ? 'score' : 'evidence';
  const displayStage = reducedMotion ? 'evidence' : stage;
  const typedOffer = useMemo(() => {
    if (displayStage !== 'input') return scenario.offer;
    return scenario.offer.slice(0, Math.min(scenario.offer.length, Math.floor((elapsed / 2500) * scenario.offer.length)));
  }, [displayStage, elapsed, scenario.offer]);
  const scoreProgress = reducedMotion ? 1 : displayStage === 'score' ? Math.min(1, (elapsed - 5000) / 2200) : displayStage === 'evidence' ? 1 : 0;
  const visibleScore = Math.round(scenario.score * scoreProgress);
  const visibleIndicators = displayStage === 'evidence' ? scenario.indicators.slice(0, reducedMotion ? scenario.indicators.length : Math.max(1, Math.ceil((elapsed - 7200) / 500))) : [];
  const isLowRisk = scenario.assessmentColor === 'emerald';
  const isHighRisk = scenario.assessmentColor === 'rose';
  const accentGlow = isHighRisk ? 'bg-rose-400/10' : isLowRisk ? 'bg-cyan-400/10' : 'bg-amber-400/10';
  const resultBorder = isHighRisk ? 'border-rose-300/30 bg-rose-300/[.06]' : isLowRisk ? 'border-emerald-300/30 bg-emerald-300/[.06]' : 'border-amber-300/30 bg-amber-300/[.06]';
  const resultText = isHighRisk ? 'text-rose-300' : isLowRisk ? 'text-emerald-300' : 'text-amber-300';
  const resultBadge = isHighRisk ? 'border-rose-300/30 bg-rose-300/10 text-rose-200' : isLowRisk ? 'border-emerald-300/30 bg-emerald-300/10 text-emerald-200' : 'border-amber-300/30 bg-amber-300/10 text-amber-200';
  const indicatorDot = isHighRisk ? 'bg-rose-300' : 'bg-amber-300';

  return (
    <div
      className="relative mx-auto w-full max-w-[570px]"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
    >
      <div className={`absolute -inset-8 rounded-[3rem] blur-3xl transition-colors duration-700 ${accentGlow}`} />
      <div className="relative rounded-[1.75rem] border border-white/10 bg-slate-950/80 p-3 shadow-2xl backdrop-blur-2xl">
        <div className="rounded-[1.25rem] border border-white/10 bg-[#0b1220] p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-300/10 text-cyan-300"><ShieldCheck className="h-4 w-4" /></span><div><p className="text-[11px] font-bold text-white">Job Offer Analysis</p><p className="text-[9px] uppercase tracking-[.15em] text-slate-500">Illustrative Demo</p></div></div>
            <button type="button" onClick={(event) => { setUserPaused((paused) => !paused); event.currentTarget.blur(); }} aria-label={userPaused ? 'Play illustrative demo' : 'Pause illustrative demo'} className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[.04] px-2.5 py-1.5 text-[10px] font-semibold text-slate-300 hover:border-cyan-300/40 hover:text-cyan-200">
              {userPaused ? <Play className="h-3 w-3" /> : <Pause className="h-3 w-3" />} {userPaused ? 'Play' : 'Pause'}
            </button>
          </div>

          <div className="mt-4 rounded-xl border border-white/10 bg-white/[.03] p-3.5">
            <div className="flex items-start justify-between gap-3"><div><p className="text-[9px] uppercase tracking-wider text-slate-500">Fictional company</p><p className="mt-1 text-[11px] font-bold text-white">{scenario.company}</p></div><span className="rounded-md border border-violet-300/20 bg-violet-300/10 px-2 py-1 text-[9px] font-semibold text-violet-200">Example only</span></div>
            <p className="mt-3 text-xs font-semibold text-cyan-100">{scenario.title}</p>
            <div className="mt-2 min-h-[54px] text-[10px] leading-5 text-slate-400">{typedOffer}<span className={`ml-0.5 inline-block h-3 w-px align-middle bg-cyan-300 ${stage === 'input' ? 'animate-pulse' : 'opacity-0'}`} /></div>
          </div>

          {displayStage === 'input' || displayStage === 'analyzing' ? (
            <div className="mt-3 rounded-xl border border-cyan-300/15 bg-cyan-300/[.04] p-3.5">
              <div className="flex items-center justify-between text-[10px] font-semibold text-cyan-200"><span>{displayStage === 'input' ? 'Ready for an illustrative pass' : 'Checking recruitment signals...'}</span><span>{displayStage === 'input' ? 'DEMO' : `${Math.round(Math.min(100, ((elapsed - 2500) / 2500) * 100))}%`}</span></div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-cyan-300 shadow-[0_0_14px_rgba(103,232,249,.9)] transition-all duration-200" style={{ width: displayStage === 'input' ? '8%' : `${Math.max(8, ((elapsed - 2500) / 2500) * 100)}%` }} /></div>
              <p className="mt-2 text-[10px] text-slate-500">{displayStage === 'input' ? 'Analyze Offer' : elapsed < 3500 ? 'Reviewing offer language...' : 'Preparing risk assessment...'}</p>
            </div>
          ) : (
            <div className={`mt-3 rounded-xl border p-4 transition-colors duration-700 ${resultBorder}`}>
              <div className="flex items-center justify-between gap-4"><div><p className="text-[9px] uppercase tracking-wider text-slate-500">Illustrative risk score</p><p className={`mt-1 font-heading text-4xl font-extrabold ${resultText}`}>{String(visibleScore).padStart(2, '0')}<span className="text-sm text-slate-500">/100</span></p></div><span className={`rounded-full border px-3 py-1.5 text-[10px] font-bold ${resultBadge}`}>{scenario.assessment}</span></div>
              <div className="mt-3 border-t border-white/10 pt-3"><p className="text-[10px] leading-5 text-slate-300">{isLowRisk ? scenario.indicators[0] : 'Observed indicators in this fictional example:'}</p>{!isLowRisk && <div className="mt-2 space-y-1.5">{visibleIndicators.map((indicator) => <p key={indicator} className="flex items-center gap-2 text-[10px] text-slate-300"><span className={`h-1.5 w-1.5 rounded-full ${indicatorDot}`} /> {indicator}</p>)}</div>}</div>
            </div>
          )}
          <p className="mt-3 text-center text-[9px] italic text-slate-600">Fictional content for demonstration only — not a live scan or ML result.</p>
        </div>
      </div>
      <div className="absolute -bottom-7 -left-5 hidden w-44 rounded-xl border border-violet-300/25 bg-[#10162a]/90 p-3 shadow-xl backdrop-blur-xl sm:block"><div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-violet-300 shadow-[0_0_12px_rgba(196,181,253,.9)]" /><span className="text-[9px] font-bold uppercase tracking-wider text-violet-200">Example signal mesh</span></div><div className="mt-3 flex items-end gap-1"><span className="h-3 w-3 rounded-t bg-violet-400/40" /><span className="h-5 w-3 rounded-t bg-violet-400/60" /><span className="h-8 w-3 rounded-t bg-violet-300" /><span className="h-6 w-3 rounded-t bg-cyan-300/70" /><span className="h-10 w-3 rounded-t bg-cyan-300" /></div></div>
    </div>
  );
};

export const Landing: React.FC = () => {
  const { session, purgeData } = useSession();
  const navigate = useNavigate();

  return (
    <div className="landing-page min-h-screen overflow-hidden bg-dark-950 text-white selection:bg-cyan-400/20 selection:text-cyan-200">
      <div className="landing-grid pointer-events-none fixed inset-0 opacity-40" />
      <div className="landing-orb landing-orb-cyan pointer-events-none fixed -left-48 top-24 h-[34rem] w-[34rem]" />
      <div className="landing-orb landing-orb-violet pointer-events-none fixed -right-56 top-[28rem] h-[38rem] w-[38rem]" />

      <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
        <button type="button" onClick={() => navigate('/')} className="flex items-center gap-3 text-left">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/30 bg-cyan-300/10 shadow-neon-cyan">
            <ShieldCheck className="h-5 w-5 text-cyan-300" />
          </span>
          <span className="font-heading text-lg font-extrabold tracking-tight">Safe<span className="text-cyan-300">Apply</span></span>
        </button>
        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-slate-500 sm:flex"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" /> Private session active</span>
          <button type="button" onClick={() => navigate('/dashboard')} className="group flex items-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-2.5 text-xs font-bold text-cyan-100 transition hover:border-cyan-200/60 hover:bg-cyan-300/20 hover:shadow-neon-cyan">
            Open SafeApply <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
        <section className="grid min-h-[640px] items-center gap-14 py-14 lg:grid-cols-[1fr_.9fr] lg:gap-16 lg:py-20">
          <div className="landing-reveal">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.16em] text-cyan-200">
              <Sparkles className="h-3.5 w-3.5" /> Recruitment security, rethought
            </div>
            <h1 className="max-w-3xl font-heading text-4xl font-extrabold leading-[1.04] tracking-tight text-white sm:text-6xl lg:text-7xl">
              Secure every job opportunity <span className="gradient-text-cyan">before you apply.</span>
            </h1>
            <p className="mt-7 max-w-xl text-base leading-8 text-slate-400 sm:text-lg">
              SafeApply helps candidates detect scam offers, understand the evidence, protect their mailbox, and prepare applications without handing over control.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <button type="button" onClick={() => navigate('/scan')} className="group flex items-center gap-2 rounded-xl bg-cyan-300 px-5 py-3.5 text-xs font-extrabold text-slate-950 shadow-[0_0_32px_-8px_rgba(103,232,249,.9)] transition hover:bg-cyan-200 hover:shadow-[0_0_42px_-8px_rgba(103,232,249,1)]">
                Start scanning <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </button>
              <button type="button" onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })} className="flex items-center gap-2 rounded-xl border border-slate-700/80 bg-white/[.03] px-5 py-3.5 text-xs font-semibold text-slate-200 transition hover:border-violet-300/50 hover:bg-violet-300/10">
                View features <ChevronRight className="h-4 w-4 text-violet-300" />
              </button>
            </div>
            <div className="mt-9 flex flex-wrap gap-x-6 gap-y-2 text-[11px] text-slate-500">
              {['No signup', 'Human confirmation', 'Private resume storage'].map((item) => <span key={item} className="flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-emerald-400" /> {item}</span>)}
            </div>
          </div>

          <IllustrativeRiskDemo />
        </section>

        <div className="signal-rail relative mx-auto -mt-4 mb-8 max-w-5xl overflow-hidden rounded-[1.5rem] border border-cyan-300/15 bg-gradient-to-br from-cyan-300/[.08] via-white/[.025] to-violet-300/[.06] px-4 py-5 shadow-[0_20px_60px_-35px_rgba(34,211,238,.55)] backdrop-blur-xl sm:mb-12 sm:px-7 sm:py-7">
          <div className="pointer-events-none absolute -right-20 -top-24 h-52 w-52 rounded-full bg-violet-400/10 blur-3xl" />
          <div className="relative mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div><div className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_12px_rgba(103,232,249,.9)]" /><p className="text-[10px] font-bold uppercase tracking-[.2em] text-cyan-200">The SafeApply signal path</p></div><p className="mt-2 max-w-md text-xs leading-5 text-slate-400">Four focused layers turn a questionable message into a clearer decision.</p></div>
            <span className="w-fit rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-[9px] font-bold uppercase tracking-[.16em] text-slate-400"><span className="signal-pulse mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-cyan-300 align-middle" /> Illustrative flow</span>
          </div>
          <div className="relative grid grid-cols-1 gap-2.5 sm:grid-cols-4 sm:gap-3">
            {[
              ['01', 'Offer signal', 'Paste or import the message', 'cyan'],
              ['02', 'Language review', 'Spot pressure and patterns', 'violet'],
              ['03', 'Evidence layer', 'See what shaped the result', 'blue'],
              ['04', 'Clear next step', 'Decide with control intact', 'emerald'],
            ].map(([number, label, description, color]) => (
              <div key={number} className="group relative rounded-xl border border-white/[.08] bg-slate-950/55 p-3.5 backdrop-blur-xl transition duration-300 hover:-translate-y-0.5 hover:border-cyan-300/35 hover:bg-slate-900/80 sm:min-h-[126px]">
                <div className="flex items-center justify-between"><span className={`flex h-8 w-8 items-center justify-center rounded-full border text-[10px] font-bold shadow-lg ${color === 'cyan' ? 'border-cyan-300/50 bg-cyan-300/15 text-cyan-100 shadow-cyan-300/10' : color === 'violet' ? 'border-violet-300/50 bg-violet-300/15 text-violet-100 shadow-violet-300/10' : color === 'blue' ? 'border-blue-300/50 bg-blue-300/15 text-blue-100 shadow-blue-300/10' : 'border-emerald-300/50 bg-emerald-300/15 text-emerald-100 shadow-emerald-300/10'}`}>{number}</span><span className="text-[9px] font-bold uppercase tracking-wider text-slate-600">Layer {number}</span></div>
                <span className="mt-3 block text-[10px] font-bold uppercase tracking-[.12em] text-slate-200 group-hover:text-white">{label}</span><span className="mt-1 block text-[10px] leading-4 text-slate-500">{description}</span>
                <span className={`mt-3 block h-1 overflow-hidden rounded-full ${color === 'cyan' ? 'bg-cyan-300/15' : color === 'violet' ? 'bg-violet-300/15' : color === 'blue' ? 'bg-blue-300/15' : 'bg-emerald-300/15'}`}><span className={`signal-bar block h-full rounded-full ${color === 'cyan' ? 'w-1/3 bg-cyan-300' : color === 'violet' ? 'w-1/2 bg-violet-300' : color === 'blue' ? 'w-2/3 bg-blue-300' : 'w-full bg-emerald-300'}`} /></span>
                {number !== '04' && <span className="pointer-events-none absolute -right-[13px] top-1/2 z-20 hidden h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full border border-cyan-300/35 bg-[#0b1220] text-cyan-200 shadow-[0_0_16px_-5px_rgba(103,232,249,.9)] sm:flex"><ChevronRight className="h-3.5 w-3.5" /></span>}
              </div>
            ))}
          </div>
        </div>

        <section id="features" className="scroll-mt-8 py-20">
          <div className="max-w-2xl"><p className="text-[10px] font-bold uppercase tracking-[.2em] text-cyan-300">One calm layer of defense</p><h2 className="mt-3 font-heading text-3xl font-extrabold tracking-tight text-white sm:text-4xl">The signal is yours to inspect.</h2><p className="mt-4 text-sm leading-7 text-slate-400">A focused workspace for the moments when a job offer feels almost right, but something is off.</p></div>
          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{features.map(({ icon: Icon, color, title, description }) => <article key={title} className="group rounded-2xl border border-white/[.08] bg-white/[.025] p-5 backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:bg-white/[.05]"><div className={`flex h-10 w-10 items-center justify-center rounded-xl border transition duration-300 ${accentClasses[color]}`}><Icon className="h-5 w-5" /></div><h3 className="mt-5 text-sm font-bold text-white">{title}</h3><p className="mt-2 text-xs leading-6 text-slate-400">{description}</p></article>)}</div>
        </section>

        <section className="grid gap-12 border-y border-white/[.08] py-20 lg:grid-cols-[.75fr_1.25fr] lg:items-center">
          <div><p className="text-[10px] font-bold uppercase tracking-[.2em] text-violet-300">A simple operating rhythm</p><h2 className="mt-3 font-heading text-3xl font-extrabold tracking-tight text-white sm:text-4xl">From uncertainty to a clear next step.</h2><p className="mt-4 max-w-md text-sm leading-7 text-slate-400">SafeApply keeps the analysis deep and the experience human-sized.</p></div>
          <div className="space-y-3">{steps.map(({ number, icon: Icon, title, description }) => <div key={number} className="group flex gap-4 rounded-2xl border border-white/[.08] bg-white/[.025] p-4 transition hover:border-cyan-300/30 hover:bg-cyan-300/[.04]"><span className="font-mono text-xs text-cyan-300/70">{number}</span><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-300/10 text-violet-200"><Icon className="h-4 w-4" /></span><div><h3 className="text-sm font-bold text-white">{title}</h3><p className="mt-1 text-xs leading-5 text-slate-400">{description}</p></div></div>)}</div>
        </section>

        <section className="grid gap-6 py-20 lg:grid-cols-[1fr_.8fr]">
          <div className="rounded-3xl border border-emerald-300/20 bg-emerald-300/[.04] p-7 sm:p-9"><div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-300/10 text-emerald-300"><ShieldCheck className="h-5 w-5" /></span><p className="text-[10px] font-bold uppercase tracking-[.2em] text-emerald-300">Responsible by design</p></div><h2 className="mt-6 max-w-xl font-heading text-2xl font-extrabold text-white sm:text-3xl">Advice, evidence, and control stay together.</h2><p className="mt-4 max-w-xl text-sm leading-7 text-slate-300">SafeApply is an advisory security tool. It highlights patterns and evidence, but it does not make final legal judgments or send applications without your confirmation.</p><div className="mt-6 grid gap-3 text-xs text-slate-300 sm:grid-cols-2">{['Human confirmation before action', 'Private anonymous sessions', 'No public resume URLs', 'Delete your data anytime'].map((item) => <span key={item} className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-emerald-300" /> {item}</span>)}</div></div>
          <div className="rounded-3xl border border-white/[.08] bg-white/[.025] p-7 sm:p-9"><p className="text-[10px] font-bold uppercase tracking-[.2em] text-cyan-300">Your workspace</p><h3 className="mt-4 font-heading text-2xl font-extrabold text-white">Start with the offer in front of you.</h3><p className="mt-3 text-sm leading-7 text-slate-400">No setup ceremony. Scan a message now, then add a profile or mailbox when it helps.</p><button type="button" onClick={() => navigate('/scan')} className="mt-7 flex items-center gap-2 text-xs font-bold text-cyan-200 transition hover:text-white">Open the scanner <ArrowRight className="h-4 w-4" /></button></div>
        </section>

        <section className="relative overflow-hidden rounded-3xl border border-cyan-300/20 bg-gradient-to-br from-cyan-300/[.12] via-blue-400/[.06] to-violet-400/[.1] px-6 py-12 text-center sm:px-10"><div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(103,232,249,.16),transparent_55%)]" /><div className="relative"><p className="text-[10px] font-bold uppercase tracking-[.2em] text-cyan-200">Ready when you are</p><h2 className="mx-auto mt-3 max-w-2xl font-heading text-3xl font-extrabold text-white sm:text-4xl">Make the next application a safer one.</h2><button type="button" onClick={() => navigate('/dashboard')} className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3.5 text-xs font-extrabold text-slate-950 transition hover:bg-cyan-100">Enter SafeApply <ArrowRight className="h-4 w-4" /></button></div></section>

        <footer className="flex flex-col gap-3 py-8 text-[10px] text-slate-600 sm:flex-row sm:items-center sm:justify-between"><span>SafeApply / recruitment security for candidates</span><span>{session ? 'Anonymous session protected' : 'No account required to begin'}</span>{session && <button type="button" onClick={async () => { if (window.confirm('Delete all your session data and uploaded files?')) await purgeData(); }} className="text-left text-slate-500 transition hover:text-rose-300">Reset session data</button>}</footer>
      </main>
    </div>
  );
};

export default Landing;
