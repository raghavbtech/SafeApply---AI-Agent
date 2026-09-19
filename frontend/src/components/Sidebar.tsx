import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  ShieldCheck,
  LayoutDashboard,
  Inbox,
  FileScan,
  ShieldAlert,
  CheckCircle2,
  Briefcase,
  Send,
  User,
  Settings,
  History,
  Activity,
  Cpu,
  Database,
  Lock,
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '../auth/AuthProvider';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();

  const { data: dashboard } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.getDashboard(),
    refetchInterval: 10000,
  });

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
  });

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/inbox', label: 'Mailbox & Scanner', icon: Inbox, count: dashboard?.stats?.inbox },
    { to: '/scan', label: 'Ad-Hoc & EML Scan', icon: FileScan },
    { to: '/quarantine', label: 'Threat Quarantine', icon: ShieldAlert, count: dashboard?.stats?.spam, badgeVariant: 'rose' },
    { to: '/verification', label: 'Ambiguous Verification', icon: CheckCircle2, count: dashboard?.stats?.medium },
    { to: '/job-agent', label: 'Job Application Agent', icon: Briefcase },
    { to: '/applications', label: 'Application Tracker', icon: Send, count: dashboard?.total_applications },
    { to: '/profile', label: 'Candidate Profile', icon: User },
    { to: '/audit', label: 'Security Audit Chain', icon: History },
    { to: '/settings', label: 'Settings & Policy', icon: Settings },
  ];

  return (
    <aside className="fixed left-0 top-0 z-30 flex h-screen w-64 flex-col border-r border-slate-800/80 bg-dark-950/95 backdrop-blur-2xl">
      {/* Brand Header */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-800/80 px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 shadow-neon-cyan">
          <ShieldCheck className="h-6 w-6 text-white" />
        </div>
        <div>
          <span className="font-heading text-lg font-extrabold tracking-tight text-white">
            Safe<span className="text-cyan-400">Apply</span>
          </span>
          <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Autonomous Security
          </span>
        </div>
      </div>

      {/* Main Navigation */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        <div className="px-3 pb-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Agent Navigation
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              clsx(
                'group flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-semibold transition-all duration-200',
                isActive
                  ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-neon-cyan'
                  : 'text-slate-400 hover:bg-dark-850 hover:text-slate-200'
              )
            }
          >
            <div className="flex items-center gap-3">
              <item.icon className="h-4 w-4 shrink-0 transition-colors group-hover:text-cyan-400" />
              <span>{item.label}</span>
            </div>
            {item.count !== undefined && item.count > 0 && (
              <span
                className={clsx(
                  'rounded-full px-2 py-0.5 text-[10px] font-bold',
                  item.badgeVariant === 'rose'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    : 'bg-dark-800 text-slate-300'
                )}
              >
                {item.count}
              </span>
            )}
          </NavLink>
        ))}

        {/* Active Candidate Card */}
        <div className="mt-6 rounded-xl border border-slate-800 bg-dark-900/60 p-3.5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Active Candidate</span>
            <span className={`h-2 w-2 rounded-full ${profile?.full_name ? 'bg-emerald-500 shadow-neon-emerald' : 'bg-slate-500'}`} />
          </div>
          <div className="mt-2 text-xs font-bold text-white truncate">
            {profile?.full_name || 'Anonymous Visitor'}
          </div>
          <div className="text-[11px] text-slate-400 truncate">
            {profile?.education || (profile?.full_name ? 'Candidate' : 'Profile not set')}
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {profile?.skills && profile.skills.length > 0 ? (
              profile.skills.slice(0, 3).map((s) => (
                <span key={s} className="rounded bg-cyan-950/60 border border-cyan-800/40 px-1.5 py-0.5 text-[9px] font-medium text-cyan-300">
                  {s}
                </span>
              ))
            ) : (
              <span className="text-[10px] text-slate-500 italic">No skills added yet</span>
            )}
          </div>
        </div>

        {/* System Capabilities & Telemetry */}
        <div className="mt-4 rounded-xl border border-slate-800/80 bg-dark-900/40 p-3 space-y-2 text-[11px]">
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5"><Cpu className="h-3.5 w-3.5 text-cyan-400" /> GenAI Layer</span>
            <span className="text-[10px] font-semibold text-emerald-400">Active</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5"><Activity className="h-3.5 w-3.5 text-violet-400" /> EMSCAD ML</span>
            <span className="text-[10px] font-semibold text-emerald-400">Joblib v1</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5"><Database className="h-3.5 w-3.5 text-amber-400" /> Mail Store</span>
            <span className="text-[10px] text-slate-300 truncate max-w-[90px]">
              {dashboard?.storage_backend?.split(' ')[0] || 'Cosmos/Local'}
            </span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5"><Lock className="h-3.5 w-3.5 text-pink-400" /> Audit Chain</span>
            <span className="text-[10px] font-semibold text-emerald-400">
              {dashboard?.audit_chain?.valid ? 'Verified' : 'Checking'}
            </span>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="border-t border-slate-800/80 p-4">
        <p className="text-[10px] text-slate-400 leading-relaxed">
          <b>Responsible AI:</b> Human-in-the-loop control required before quarantining or sending applications.
        </p>
      </div>
    </aside>
  );
};
