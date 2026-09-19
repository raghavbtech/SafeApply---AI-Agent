import React, { useState } from 'react';
import { RefreshCw, User, Trash2, ShieldCheck, AlertTriangle } from 'lucide-react';
import { useSession } from '../auth/AuthProvider';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const { session, purgeData } = useSession();
  const queryClient = useQueryClient();
  const [showPurgeConfirm, setShowPurgeConfirm] = useState(false);

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

  const sessionIdSnippet = session?.session_id ? `${session.session_id.slice(0, 10)}...` : 'Initializing';

  return (
    <header className="sticky top-0 z-20 flex h-16 w-full items-center justify-between border-b border-slate-800/80 bg-dark-950/80 px-8 backdrop-blur-xl">
      <div>
        <h1 className="font-heading text-lg font-bold text-white tracking-tight">{title}</h1>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Quick Sync Button */}
        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
          className="flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 transition hover:bg-cyan-500/20 disabled:opacity-50 shadow-neon-cyan"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
          <span>{syncMutation.isPending ? 'Syncing...' : 'Force Sync'}</span>
        </button>

        {/* Anonymous Session Pill */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-slate-300">
            <ShieldCheck className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="hidden text-left sm:block">
            <span className="block text-xs font-semibold text-white font-mono">
              {sessionIdSnippet}
            </span>
            <span className="block text-[10px] text-emerald-400">Anonymous Session</span>
          </div>

          <button
            onClick={() => setShowPurgeConfirm(true)}
            title="Delete My Data & Reset Session"
            className="ml-2 rounded-lg p-1.5 text-slate-400 hover:bg-dark-800 hover:text-rose-400 transition"
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
    </header>
  );
};
export default Header;
