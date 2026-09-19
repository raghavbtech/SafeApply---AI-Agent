import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, Cpu, Sparkles, ArrowRight, Lock, Mail, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';

export const Landing: React.FC = () => {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('demo@safeapply.local');
  const [password, setPassword] = useState('SafeApplyDemo2026!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

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

        {user ? (
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-xs font-bold text-white shadow-neon-cyan hover:opacity-95 transition"
          >
            Go to Command Hub <ArrowRight className="h-4 w-4" />
          </button>
        ) : (
          <span className="text-xs font-semibold text-slate-400">Autonomous Recruitment Security</span>
        )}
      </header>

      {/* Hero Section */}
      <main className="relative z-10 mx-auto max-w-6xl px-8 py-16">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3.5 py-1 text-xs font-semibold text-cyan-300 shadow-neon-cyan">
              <Sparkles className="h-3.5 w-3.5" /> 4-Pillar Autonomous Security Engine
            </div>

            <h1 className="mt-6 font-heading text-4xl font-extrabold leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
              Defend your career from <span className="gradient-text-cyan">recruitment scams</span>.
            </h1>

            <p className="mt-4 text-base text-slate-400 leading-relaxed max-w-xl">
              SafeApply autonomously monitors your recruitment mailbox, intercepts fraudulent upfront fee requests and impersonation, and accelerates applications to legitimate opportunities.
            </p>

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

          {/* Quick Demo Sign In Card */}
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-slate-800 bg-dark-900/90 p-8 shadow-2xl backdrop-blur-2xl">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <Lock className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-white">Candidate Sign In</h3>
                  <p className="text-xs text-slate-400">Access your security dashboard</p>
                </div>
              </div>

              {error && (
                <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                  {error}
                </div>
              )}

              <form onSubmit={handleLogin} className="mt-6 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="mt-1.5 w-full rounded-xl border border-slate-700 bg-dark-850 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="mt-1.5 w-full rounded-xl border border-slate-700 bg-dark-850 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 py-3 text-xs font-bold text-white shadow-neon-cyan transition hover:opacity-95 disabled:opacity-50"
                >
                  {loading ? 'Authenticating...' : 'Enter SafeApply Agent'}
                </button>

                <p className="text-center text-[11px] text-slate-500">
                  Pre-filled with local development demo credentials.
                </p>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
