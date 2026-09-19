import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Inbox,
  ShieldAlert,
  CheckCircle2,
  Send,
  AlertTriangle,
  Scan,
  ArrowUpRight,
  Shield,
  Activity,
  Layers,
  FileScan,
  UserCheck,
  Briefcase,
  ExternalLink,
  Lock,
} from 'lucide-react';
import { api } from '../api/client';
import { ScoreCard } from '../components/ScoreCard';
import { StatusBanner } from '../components/StatusBanner';
import { RiskBadge } from '../components/RiskBadge';
import { Loading } from '../components/Loading';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.getDashboard(),
    refetchInterval: 10000,
  });

  const { data: recentEmails } = useQuery({
    queryKey: ['emails', 'recent'],
    queryFn: () => api.listEmails({ limit: 6, folder: 'inbox' }),
    refetchInterval: 10000,
  });

  const { data: preferences } = useQuery({
    queryKey: ['preferences'],
    queryFn: () => api.getPreferences(),
  });

  const batchScanMutation = useMutation({
    mutationFn: () => api.batchScan(20),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  if (dashLoading) return <Loading label="Connecting to SafeApply Security Fabric..." />;

  const stats = dashboard?.stats || {
    total: 0,
    inbox: 0,
    spam: 0,
    unscanned: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    applied: 0,
    ignored: 0,
  };

  return (
    <div className="space-y-8">
      {/* Live Polling & Policy Banner */}
      <StatusBanner
        autoSyncActive={dashboard?.connection?.is_connected ?? true}
        quarantineEnabled={preferences?.auto_quarantine_enabled ?? false}
      />

      {/* Top Action Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-xl font-extrabold text-white">Recruitment Security Overview</h2>
          <p className="text-xs text-slate-400">
            Automated multi-engine scam detection and candidate application workflow.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => batchScanMutation.mutate()}
            disabled={batchScanMutation.isPending}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-neon-cyan transition hover:opacity-95 disabled:opacity-50"
          >
            <Scan className={`h-4 w-4 ${batchScanMutation.isPending ? 'animate-spin' : ''}`} />
            <span>{batchScanMutation.isPending ? 'Scanning Inbox...' : 'Scan All Unscanned'}</span>
          </button>
        </div>
      </div>

      {/* Candidate Action Shortcuts (4 Primary Shortcuts) */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <button
          onClick={() => navigate('/scan')}
          className="group flex flex-col justify-between rounded-2xl border border-cyan-500/20 bg-dark-900/60 p-5 text-left backdrop-blur-xl transition-all duration-200 hover:border-cyan-500/50 hover:bg-dark-850/80 hover:shadow-neon-cyan"
        >
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              <FileScan className="h-5 w-5" />
            </div>
            <ArrowUpRight className="h-4 w-4 text-slate-500 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-cyan-400" />
          </div>
          <div className="mt-4">
            <h3 className="font-heading text-sm font-bold text-white group-hover:text-cyan-300">Scan Job Offer</h3>
            <p className="mt-1 text-xs text-slate-400">Paste suspicious offer text or upload an .EML message.</p>
          </div>
        </button>

        <button
          onClick={() => navigate('/inbox')}
          className="group flex flex-col justify-between rounded-2xl border border-violet-500/20 bg-dark-900/60 p-5 text-left backdrop-blur-xl transition-all duration-200 hover:border-violet-500/50 hover:bg-dark-850/80 hover:shadow-neon-violet"
        >
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/30">
              <Inbox className="h-5 w-5" />
            </div>
            <ArrowUpRight className="h-4 w-4 text-slate-500 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-violet-400" />
          </div>
          <div className="mt-4">
            <h3 className="font-heading text-sm font-bold text-white group-hover:text-violet-300">My Mailbox</h3>
            <p className="mt-1 text-xs text-slate-400">Review scanned emails, quarantined threats & verification.</p>
          </div>
        </button>

        <button
          onClick={() => navigate('/applications')}
          className="group flex flex-col justify-between rounded-2xl border border-emerald-500/20 bg-dark-900/60 p-5 text-left backdrop-blur-xl transition-all duration-200 hover:border-emerald-500/50 hover:bg-dark-850/80"
        >
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <Briefcase className="h-5 w-5" />
            </div>
            <ArrowUpRight className="h-4 w-4 text-slate-500 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-emerald-400" />
          </div>
          <div className="mt-4">
            <h3 className="font-heading text-sm font-bold text-white group-hover:text-emerald-300">Job Applications</h3>
            <p className="mt-1 text-xs text-slate-400">Match skills, generate tailored drafts & track submissions.</p>
          </div>
        </button>

        <button
          onClick={() => navigate('/profile')}
          className="group flex flex-col justify-between rounded-2xl border border-amber-500/20 bg-dark-900/60 p-5 text-left backdrop-blur-xl transition-all duration-200 hover:border-amber-500/50 hover:bg-dark-850/80"
        >
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30">
              <UserCheck className="h-5 w-5" />
            </div>
            <ArrowUpRight className="h-4 w-4 text-slate-500 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-amber-400" />
          </div>
          <div className="mt-4">
            <h3 className="font-heading text-sm font-bold text-white group-hover:text-amber-300">My Profile</h3>
            <p className="mt-1 text-xs text-slate-400">Update candidate details, education, skills, and resume.</p>
          </div>
        </button>
      </div>

      {/* Advisory Risk Distribution Grid */}
      <div className="space-y-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Advisory Risk Distribution</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <ScoreCard
            label="Total Inspected"
            value={stats.total}
            icon={Layers}
            variant="default"
            description="Messages analyzed"
            onClick={() => navigate('/inbox')}
          />
          <ScoreCard
            label="Active Inbox"
            value={stats.inbox}
            icon={Inbox}
            variant="cyan"
            description="Active opportunities"
            onClick={() => navigate('/inbox')}
          />
          <ScoreCard
            label="Quarantined Threats"
            value={stats.spam}
            icon={ShieldAlert}
            variant="rose"
            description="Scams & phishing"
            onClick={() => navigate('/inbox?tab=quarantine')}
          />
          <ScoreCard
            label="Needs Check"
            value={stats.medium}
            icon={AlertTriangle}
            variant="amber"
            description="Ambiguous offers"
            onClick={() => navigate('/inbox')}
          />
          <ScoreCard
            label="Legitimate"
            value={stats.low}
            icon={CheckCircle2}
            variant="emerald"
            description="Low risk verified"
            onClick={() => navigate('/inbox')}
          />
          <ScoreCard
            label="Applications Prepared"
            value={stats.applied}
            icon={Send}
            variant="violet"
            description="Dispatched packages"
            onClick={() => navigate('/applications?tab=history')}
          />
        </div>
      </div>

      {/* Two Column Section: Recent Messages & Session Protection */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Column: Recent Incoming Recruitment Messages */}
        <div className="lg:col-span-8 rounded-2xl border border-slate-800/80 bg-dark-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <h3 className="font-heading text-base font-bold text-white">Recent Recruitment Messages</h3>
              <p className="text-xs text-slate-400">Incoming offers filtered and scored by SafeApply</p>
            </div>
            <button
              onClick={() => navigate('/inbox')}
              className="flex items-center gap-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition"
            >
              View in My Mailbox <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="mt-4 divide-y divide-slate-800/60">
            {recentEmails?.items?.length ? (
              recentEmails.items.map((email) => (
                <div
                  key={email.id}
                  onClick={() => navigate(`/inbox?selected=${email.id}`)}
                  className="flex items-center justify-between py-3.5 transition hover:bg-dark-850/60 px-3 rounded-xl cursor-pointer"
                >
                  <div className="min-w-0 flex-1 pr-4">
                    <div className="flex items-center gap-2">
                      <span className="font-heading text-xs font-bold text-white truncate max-w-sm">
                        {email.subject}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[11px] text-slate-400 truncate">
                      <b>{email.company_name}</b> · {email.sender_name || email.sender} · {email.date}
                    </p>
                  </div>

                  <div className="shrink-0 flex items-center gap-3">
                    <RiskBadge level={email.risk_level} score={email.risk_score} status={email.status} />
                  </div>
                </div>
              ))
            ) : (
              <div className="py-12 text-center text-xs text-slate-500">
                No recruitment emails in inbox. Sync your mailbox or run a manual scan to inspect offers.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Candidate Session & Mailbox Summary */}
        <div className="lg:col-span-4 space-y-6">
          {/* Candidate Privacy & Session Status */}
          <div className="rounded-2xl border border-slate-800/80 bg-dark-900/60 p-6 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Candidate Privacy</span>
              <Lock className="h-4 w-4 text-cyan-400" />
            </div>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <span className="font-heading text-sm font-bold text-white">Private Anonymous Session</span>
                <p className="text-[11px] text-slate-400">
                  No login required. Data partitioned to your secure browser session.
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/settings')}
              className="mt-4 w-full rounded-lg border border-slate-700 bg-dark-850 py-2 text-xs font-semibold text-slate-300 hover:bg-dark-800 transition"
            >
              Privacy & Data Controls
            </button>
          </div>

          {/* Mailbox Connection Summary */}
          <div className="rounded-2xl border border-slate-800/80 bg-dark-900/60 p-6 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Mailbox Status</span>
              <Activity className="h-4 w-4 text-violet-400" />
            </div>
            <div className="mt-3">
              <span className="block text-sm font-bold text-white">
                {dashboard?.connection?.provider || 'IMAP Provider'}
              </span>
              <span className="text-xs text-slate-400 truncate block">
                {dashboard?.connection?.username || 'Local Sandbox / Demo Mailbox'}
              </span>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800 flex justify-between items-center text-xs">
              <span className="text-slate-400">Connection State:</span>
              <span className={`font-semibold ${dashboard?.connection?.is_connected ? 'text-emerald-400' : 'text-amber-400'}`}>
                {dashboard?.connection?.is_connected ? 'Connected' : 'Sandbox Mode'}
              </span>
            </div>
            <button
              onClick={() => navigate('/settings')}
              className="mt-3 w-full rounded-lg border border-slate-700 bg-dark-850 py-2 text-xs font-semibold text-slate-300 hover:bg-dark-800 transition"
            >
              Manage Connection & Policies
            </button>
          </div>

          {/* Recruitment Safety Best Practices */}
          <div className="rounded-2xl border border-slate-800/80 bg-dark-900/60 p-6 backdrop-blur-xl space-y-3">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-cyan-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-white">Candidate Safety Guidelines</h4>
            </div>
            <ul className="space-y-2 text-[11px] text-slate-400">
              <li className="flex items-start gap-1.5">
                <span className="text-rose-400 font-bold">✕</span>
                <span>Never pay any registration, interview, or equipment fees.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-emerald-400 font-bold">✓</span>
                <span>Verify recruiter domains against legitimate corporate careers sites.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-amber-400 font-bold">!</span>
                <span>Treat unsolicited offers via WhatsApp or Telegram with skepticism.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
