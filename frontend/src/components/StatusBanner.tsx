import React from 'react';
import { Activity, ShieldAlert, CheckCircle2, AlertTriangle, XCircle, X } from 'lucide-react';

export interface StatusBannerProps {
  autoSyncActive?: boolean;
  quarantineEnabled?: boolean;
  type?: 'success' | 'error' | 'warning' | 'info';
  message?: string;
  onDismiss?: () => void;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({
  autoSyncActive = true,
  quarantineEnabled = false,
  type,
  message,
  onDismiss,
}) => {
  // If rendering a notification/alert message
  if (message) {
    const styles = {
      success: {
        border: 'border-emerald-500/30',
        bg: 'bg-emerald-500/10',
        text: 'text-emerald-300',
        icon: CheckCircle2,
      },
      error: {
        border: 'border-rose-500/30',
        bg: 'bg-rose-500/10',
        text: 'text-rose-300',
        icon: XCircle,
      },
      warning: {
        border: 'border-amber-500/30',
        bg: 'bg-amber-500/10',
        text: 'text-amber-300',
        icon: AlertTriangle,
      },
      info: {
        border: 'border-cyan-500/30',
        bg: 'bg-cyan-500/10',
        text: 'text-cyan-300',
        icon: Activity,
      },
    }[type || 'info'];

    const Icon = styles.icon;

    return (
      <div className={`flex items-center justify-between gap-3 p-3.5 rounded-xl border ${styles.border} ${styles.bg} ${styles.text} text-xs animate-fadeIn`}>
        <div className="flex items-center gap-2.5">
          <Icon className="w-4 h-4 shrink-0" />
          <span>{message}</span>
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="p-1 hover:opacity-80 transition-opacity"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    );
  }

  // Otherwise render default system policy status banner
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-2.5 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-neon-emerald"></span>
        </span>
        <span className="text-xs font-semibold text-emerald-400">Continuous Auto-Sync Active</span>
        <span className="hidden text-xs text-slate-400 sm:inline">
          Background poller checking mailbox automatically · Real-time threat detection
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-400">Policy:</span>
        {quarantineEnabled ? (
          <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-2 py-0.5 font-medium text-rose-300">
            <ShieldAlert className="h-3 w-3" /> Auto-Quarantine ON
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 font-medium text-slate-300">
            <CheckCircle2 className="h-3 w-3 text-cyan-400" /> Human Approval Required
          </span>
        )}
      </div>
    </div>
  );
};
export default StatusBanner;
