import React from 'react';
import { RefreshCw, Bell, User, LogOut } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();

  const syncMutation = useMutation({
    mutationFn: () => api.syncMailbox(15),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['audit'] });
    },
  });

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

        {/* User Pill */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-slate-300">
            <User className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="hidden text-left sm:block">
            <span className="block text-xs font-semibold text-white">
              {user?.full_name || user?.email || 'Candidate'}
            </span>
            <span className="block text-[10px] text-slate-400">Authenticated</span>
          </div>

          <button
            onClick={logout}
            title="Sign out"
            className="ml-2 rounded-lg p-1.5 text-slate-400 hover:bg-dark-800 hover:text-rose-400 transition"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
