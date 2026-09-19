import React from 'react';
import clsx from 'clsx';

interface RiskBadgeProps {
  level?: 'Low' | 'Medium' | 'High' | 'Critical' | null;
  score?: number | null;
  status?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, score, status, size = 'md' }) => {
  if (status === 'quarantined') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/50 bg-rose-500/10 px-2.5 py-0.5 text-xs font-semibold text-rose-400 shadow-neon-rose">
        <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
        Quarantined
      </span>
    );
  }

  if (status === 'applied') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/50 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 shadow-neon-emerald">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        🚀 Applied {score !== undefined && score !== null ? `· ${score}/100` : ''}
      </span>
    );
  }

  if (status === 'unscanned') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/40 px-2.5 py-0.5 text-xs font-medium text-slate-400">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
        Unscanned
      </span>
    );
  }

  const scoreText = score !== undefined && score !== null ? ` (${score}/100)` : '';

  switch (level) {
    case 'Critical':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-600 bg-rose-600/20 px-3 py-1 text-xs font-bold text-rose-400 shadow-neon-rose">
          <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping" />
          Critical Scam Threat{scoreText}
        </span>
      );
    case 'High':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/60 bg-rose-500/15 px-2.5 py-0.5 text-xs font-bold text-rose-400 shadow-neon-rose">
          <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
          High Risk{scoreText}
        </span>
      );
    case 'Medium':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/60 bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-300">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
          Medium Risk{scoreText}
        </span>
      );
    case 'Low':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/50 bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-300 shadow-neon-emerald">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Low Risk (Safe){scoreText}
        </span>
      );
  }
};
