import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = Inbox,
  action,
}) => {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 bg-dark-900/40 p-12 text-center backdrop-blur-sm">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-800 bg-dark-850 text-slate-400 shadow-inner">
        <Icon className="h-8 w-8 text-slate-500" />
      </div>
      <h3 className="mt-4 font-heading text-lg font-bold text-white">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-400">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-6 rounded-lg bg-cyan-500/10 px-4 py-2 text-xs font-semibold text-cyan-400 border border-cyan-500/30 transition hover:bg-cyan-500/20 shadow-neon-cyan"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};
