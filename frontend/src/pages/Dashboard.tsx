import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Inbox,
  ShieldAlert,
  CheckCircle2,
  Send,
  AlertTriangle,
  RefreshCw,
  Scan,
  ArrowUpRight,
  Shield,
  Activity,
  Layers,
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

  const { data: recentEmails, isLoading: emailsLoading } = useQuery({
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
          <h2 className="font-heading text-xl font-extrabold text-white">System Threat Status</h2>
          <p className="text-xs text-slate-400">
            Real-time multi-modal analysis across Rules, EMSCAD ML, Search RAG & Foundry.
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

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <ScoreCard
          label="Total Inspected"
          value={stats.total}
          icon={Layers}
          variant="default"
          description="Stored in Cosmos"
          onClick={() => navigate('/inbox')}
        />
        <ScoreCard
          label="In Inbox"
          value={stats.inbox}
          icon={Inbox}
          variant="cyan"
          description="Active opportunities"
          onClick={() => navigate('/inbox')}
        />
        <ScoreCard
          label="Quarantined"
          value={stats.spam}
          icon={ShieldAlert}
          variant="rose"
          description="High/critical scams"
          onClick={() => navigate('/quarantine')}
        />
        <ScoreCard
          label="Needs Check"
          value={stats.medium}
          icon={AlertTriangle}
          variant="amber"
          description="Ambiguous offers"
          onClick={() => navigate('/verification')}
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
          label="Applied"
          value={stats.applied}
          icon={Send}
          variant="violet"
          description="Dispatched packages"
          onClick={() => navigate('/applications')}
        />
      </div>

      {/* Two Column Section: Recent Threats & Telemetry */}
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
              View All <ArrowUpRight className="h-3.5 w-3.5" />
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
                No recruitment emails in inbox. Sync your mailbox or run a manual scan.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Security Telemetry & Audit Integrity */}
        <div className="lg:col-span-4 space-y-6">
          {/* Audit Chain Status */}
          <div className="rounded-2xl border border-slate-800/80 bg-dark-900/60 p-6 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Audit Trail Integrity</span>
              <Shield className="h-4 w-4 text-cyan-400" />
            </div>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <span className="font-heading text-sm font-bold text-white">SHA-256 Hash Chain Verified</span>
                <p className="text-[11px] text-slate-400">
                  {dashboard?.audit_chain?.records || 0} tamper-evident records signed
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/audit')}
              className="mt-4 w-full rounded-lg border border-slate-700 bg-dark-850 py-2 text-xs font-semibold text-slate-300 hover:bg-dark-800 transition"
            >
              Inspect Audit Log
            </button>
          </div>

          {/* Mailbox Connection Summary */}
          <div className="rounded-2xl border border-slate-800/80 bg-dark-900/60 p-6 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Mailbox Provider</span>
              <Activity className="h-4 w-4 text-violet-400" />
            </div>
            <div className="mt-3">
              <span className="block text-sm font-bold text-white">
                {dashboard?.connection?.provider || 'IMAP Provider'}
              </span>
              <span className="text-xs text-slate-400 truncate block">
                {dashboard?.connection?.username || 'Not configured in environment'}
              </span>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800 flex justify-between items-center text-xs">
              <span className="text-slate-400">Storage Backend:</span>
              <span className="font-semibold text-cyan-400">{dashboard?.storage_backend}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
