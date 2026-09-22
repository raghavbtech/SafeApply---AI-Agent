import React, { useState } from 'react';
import { RefreshCw, User, Trash2, ShieldCheck, AlertTriangle } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useSession } from '../auth/AuthProvider';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { CandidateProfileSchema } from '../api/contracts';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const navigate = useNavigate();
  const { session, purgeData } = useSession();
  const queryClient = useQueryClient();
  const [showPurgeConfirm, setShowPurgeConfirm] = useState(false);

  const { data: profile } = useQuery<CandidateProfileSchema>({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
  });

  const syncMutation = useMutation({
    mutationFn: () => api.syncMailbox(15),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['audit'] });
    },
  });

  const handlePurge = async () => {
    setShowPurgeConfirm(false);
    await purgeData();
    queryClient.clear();
  };

  const candidateName = profile?.full_name?.trim();
  const sessionIdSnippet = session?.session_id ? `${session.session_id.slice(0, 10)}...` : 'Initializing';
  const mobileLinks = [
    { to: '/dashboard', label: 'Home' },
    { to: '/scan', label: 'Scan' },
    { to: '/inbox', label: 'Mailbox' },
    { to: '/profile', label: 'Profile' },
  ];

  return (
    <header className="app-header-height sticky top-0 z-20 flex w-full items-center justify-between gap-3 border-b border-slate-800/80 bg-dark-950/80 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
      <div>
        <h1 className="font-heading text-base font-bold tracking-tight text-white sm:text-lg">{title}</h1>
        {subtitle && <p className="hidden text-xs text-slate-400 sm:block">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Quick Sync Button */}
        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
          className="flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 transition hover:bg-cyan-500/20 disabled:opacity-50 shadow-neon-cyan"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">{syncMutation.isPending ? 'Syncing...' : 'Force Sync'}</span>
        </button>

        {/* Candidate Profile / Anonymous Session Pill */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <button
            type="button"
            onClick={() => navigate('/profile')}
            title="View or Edit Candidate Profile"
            className="flex items-center gap-2.5 rounded-xl border border-cyan-500/20 bg-dark-900/90 px-3 py-1.5 transition hover:border-cyan-500/50 hover:bg-dark-800 text-left"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-500 text-white font-bold text-xs shadow-glow-cyan shrink-0">
              {candidateName ? (
                candidateName.charAt(0).toUpperCase()
              ) : (
                <ShieldCheck className="h-4 w-4 text-cyan-300" />
              )}
            </div>
            <div className="hidden text-left sm:block">
              <span className="block text-xs font-semibold text-white tracking-tight truncate max-w-[110px] sm:max-w-[180px]">
                {candidateName || sessionIdSnippet}
              </span>
              <span className="flex items-center gap-1 text-[10px] text-cyan-400 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="truncate max-w-[80px] sm:max-w-none">{candidateName ? 'Candidate' : 'Anonymous'}</span>
              </span>
            </div>
          </button>

          <button
            onClick={() => setShowPurgeConfirm(true)}
            title="Delete My Data & Reset Session"
            className="ml-1 rounded-lg p-1.5 text-slate-400 hover:bg-dark-800 hover:text-rose-400 transition"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Purge Confirmation Modal */}
      {showPurgeConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
          <div className="w-full max-w-md rounded-2xl border border-rose-500/30 bg-dark-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertTriangle className="h-6 w-6 shrink-0" />
              <h3 className="font-heading text-base font-bold text-white">Permanently Delete My Data?</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              This will immediately delete your candidate profile, uploaded resume file, cached recruitment emails, applications, and cryptographic audit log from this anonymous session.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowPurgeConfirm(false)}
                className="rounded-lg px-4 py-2 text-xs font-medium text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePurge}
                className="rounded-lg bg-rose-500 hover:bg-rose-600 px-4 py-2 text-xs font-semibold text-white transition"
              >
                Yes, Delete All My Data
              </button>
            </div>
          </div>
        </div>
      )}
      <nav className="absolute left-0 right-0 top-full flex gap-1 overflow-x-auto border-b border-slate-800/80 bg-dark-950/95 px-3 py-2 backdrop-blur-xl lg:hidden">
        {mobileLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-1.5 text-[11px] font-semibold ${isActive ? 'bg-cyan-400/10 text-cyan-200' : 'text-slate-500'}`}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
};
export default Header;
