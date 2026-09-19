import React from 'react';
import { LucideIcon } from 'lucide-react';
import clsx from 'clsx';

interface ScoreCardProps {
  label: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  variant?: 'cyan' | 'violet' | 'emerald' | 'amber' | 'rose' | 'default';
  onClick?: () => void;
}

export const ScoreCard: React.FC<ScoreCardProps> = ({
  label,
  value,
  description,
  icon: Icon,
  variant = 'cyan',
  onClick,
}) => {
  const variantStyles = {
    cyan: 'border-cyan-500/20 hover:border-cyan-500/50 text-cyan-400 group-hover:shadow-neon-cyan',
    violet: 'border-violet-500/20 hover:border-violet-500/50 text-violet-400 group-hover:shadow-neon-violet',
    emerald: 'border-emerald-500/20 hover:border-emerald-500/50 text-emerald-400 group-hover:shadow-neon-emerald',
    amber: 'border-amber-500/20 hover:border-amber-500/50 text-amber-400',
    rose: 'border-rose-500/20 hover:border-rose-500/50 text-rose-400 group-hover:shadow-neon-rose',
    default: 'border-slate-800 text-slate-400',
  };

  const iconGlow = {
    cyan: 'bg-cyan-500/10 text-cyan-400',
    violet: 'bg-violet-500/10 text-violet-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    amber: 'bg-amber-500/10 text-amber-400',
    rose: 'bg-rose-500/10 text-rose-400',
    default: 'bg-slate-800 text-slate-400',
  };

  return (
    <div
      onClick={onClick}
      className={clsx(
        'group relative overflow-hidden rounded-xl border bg-dark-900/80 p-5 backdrop-blur-xl transition-all duration-300',
        onClick && 'cursor-pointer hover:-translate-y-1',
        variantStyles[variant]
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</span>
        <div className={clsx('flex h-10 w-10 items-center justify-center rounded-lg', iconGlow[variant])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-4 flex items-baseline gap-2">
        <span className="font-heading text-3xl font-extrabold tracking-tight text-white">{value}</span>
      </div>
      {description && <p className="mt-1 text-xs text-slate-500">{description}</p>}
    </div>
  );
};
