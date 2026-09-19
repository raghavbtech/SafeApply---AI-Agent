import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  Cpu,
  Sparkles,
  ArrowRight,
  FileScan,
  UserCheck,
  Mail,
  Trash2,
  Lock,
  ExternalLink,
  Info
} from 'lucide-react';
import { useSession } from '../auth/AuthProvider';

export const Landing: React.FC = () => {
  const { session, purgeData } = useSession();
  const navigate = useNavigate();

  return (
    <div className="relative min-h-screen overflow-hidden bg-dark-950 text-white selection:bg-cyan-500/20 selection:text-cyan-400">
      {/* Background Glow Orbs */}
      <div className="pointer-events-none absolute -left-40 -top-40 h-96 w-96 rounded-full bg-cyan-500/15 blur-[120px]" />
      <div className="pointer-events-none absolute -right-40 top-1/3 h-96 w-96 rounded-full bg-violet-600/15 blur-[140px]" />

      {/* Navigation */}
      <header className="relative z-10 flex h-20 items-center justify-between border-b border-slate-800/80 px-8 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 shadow-neon-cyan">
            <ShieldCheck className="h-6 w-6 text-white" />
          </div>
          <span className="font-heading text-xl font-extrabold tracking-tight">
            Safe<span className="text-cyan-400">Apply</span>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-xs font-bold text-white shadow-neon-cyan hover:opacity-95 transition"
          >
            Launch Command Hub <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 mx-auto max-w-6xl px-8 py-16">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3.5 py-1 text-xs font-semibold text-cyan-300 shadow-neon-cyan">
              <Sparkles className="h-3.5 w-3.5" /> 100% Public & Account-Free Recruitment Defense
            </div>

            <h1 className="mt-6 font-heading text-4xl font-extrabold leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
              Defend your career from <span className="gradient-text-cyan">recruitment scams</span>.
            </h1>

            <p className="mt-4 text-base text-slate-400 leading-relaxed max-w-xl">
              SafeApply uses multi-engine AI and threat intelligence to analyze suspicious recruitment solicitations, verify company domains, and prepare verified job applications. No sign-up, no password, and no accounts required.
            </p>

            {/* Direct Action Hub */}
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center gap-2 rounded-xl bg-neon-cyan px-5 py-3 text-xs font-bold text-black shadow-glow-cyan hover:opacity-95 transition"
              >
                Get Started (Dashboard) <ArrowRight className="h-4 w-4" />
              </button>

              <button
                onClick={() => navigate('/scan')}
                className="flex items-center gap-2 rounded-xl border border-slate-700 bg-surface-raised px-4 py-3 text-xs font-semibold text-white hover:border-neon-cyan transition"
              >
                <FileScan className="h-4 w-4 text-neon-cyan" />
                Analyze Job Offer
              </button>

              <button
                onClick={() => navigate('/profile')}
                className="flex items-center gap-2 rounded-xl border border-slate-700 bg-surface-raised px-4 py-3 text-xs font-semibold text-white hover:border-neon-violet transition"
              >
                <UserCheck className="h-4 w-4 text-neon-violet" />
                Upload Resume
              </button>

              <button
                onClick={() => navigate('/settings')}
                className="flex items-center gap-2 rounded-xl border border-slate-700 bg-surface-raised px-4 py-3 text-xs font-semibold text-white hover:border-neon-amber transition"
              >
                <Mail className="h-4 w-4 text-neon-amber" />
                Connect Mailbox
              </button>
            </div>

            {/* Feature Highlights */}
            <div className="mt-8 grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-800 bg-dark-900/60 p-4 backdrop-blur-sm">
                <ShieldAlert className="h-5 w-5 text-rose-400" />
                <h4 className="mt-2 text-xs font-bold text-white">4-Pillar Fraud Defense</h4>
                <p className="mt-1 text-[11px] text-slate-400">Rules + EMSCAD ML + Azure Search RAG + Azure AI Foundry.</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-dark-900/60 p-4 backdrop-blur-sm">
                <Cpu className="h-5 w-5 text-cyan-400" />
                <h4 className="mt-2 text-xs font-bold text-white">Autonomous Job Agent</h4>
                <p className="mt-1 text-[11px] text-slate-400">Skill overlap matching, tailored cover letters, and verified dispatch.</p>
              </div>
            </div>
          </div>

          {/* Privacy & Anonymous Session Guarantee Card */}
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-slate-800 bg-dark-900/90 p-8 shadow-2xl backdrop-blur-2xl space-y-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-white">Zero Account Architecture</h3>
                  <p className="text-xs text-slate-400">Private, isolated, and cryptographically secured</p>
                </div>
              </div>

              <div className="space-y-3 text-xs text-slate-300">
                <div className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Automatic Anonymous Session:</strong> Every visitor receives a private cryptographic session via an HTTP-only cookie. No tracking across sessions.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Data Isolation:</strong> Your candidate profile, uploaded resume, and scanned emails are strictly partitioned. Other visitors can never access your data.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Private Storage:</strong> Uploaded resumes are stored in private secure folders with validated MIME types and 10MB limits, never exposed publicly.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>No Shared Mailbox:</strong> SafeApply never uses shared mailbox credentials. You maintain full control to connect or disconnect your mailbox.</span>
                </div>
              </div>

              {/* Instant Purge / Reset */}
              <div className="p-4 rounded-xl bg-surface-raised border border-border-subtle space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white flex items-center gap-1.5">
                    <Trash2 className="w-3.5 h-3.5 text-neon-coral" />
                    Complete Data Erasure
                  </span>
                  {session && (
                    <span className="font-mono text-2xs text-slate-500">
                      ID: {session.session_id.slice(0, 12)}...
                    </span>
                  )}
                </div>
                <p className="text-2xs text-slate-400">
                  You can permanently delete all your stored profile data, resumes, and scan logs at any time with one click.
                </p>
                <button
                  type="button"
                  onClick={async () => {
                    if (window.confirm('Delete all your session data, uploaded resume, and scan records?')) {
                      await purgeData();
                      alert('All session data and uploaded files have been permanently erased.');
                    }
                  }}
                  className="w-full py-2 px-3 rounded-lg bg-neon-coral/10 hover:bg-neon-coral/20 border border-neon-coral/30 text-neon-coral font-medium text-xs transition"
                >
                  Delete My Data & Reset Session
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
export default Landing;
