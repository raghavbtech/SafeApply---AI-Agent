import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { UserPreferencesSchema, MailboxConnectionStatus } from '../api/contracts';
import { Loading } from '../components/Loading';
import { StatusBanner } from '../components/StatusBanner';
import {
  Sliders,
  Mail,
  ShieldAlert,
  Send,
  RefreshCw,
  Server,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Info,
  Save,
  SlidersHorizontal
} from 'lucide-react';

export const Settings: React.FC = () => {
  const queryClient = useQueryClient();

  const [prefs, setPrefs] = useState<UserPreferencesSchema>({
    auto_quarantine_enabled: false,
    auto_quarantine_threshold: 65,
    auto_apply_enabled: false,
    auto_apply_max_risk_score: 45,
    enable_real_smtp_dispatch: false,
  });

  const [syncBatchSize, setSyncBatchSize] = useState<number>(15);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  // Fetch Mailbox Status
  const { data: mailboxStatus, isLoading: isMailboxLoading } = useQuery<MailboxConnectionStatus>({
    queryKey: ['mailbox-status'],
    queryFn: () => api.getMailboxStatus(),
  });

  // Fetch Preferences
  const { data: userPrefs, isLoading: isPrefsLoading } = useQuery<UserPreferencesSchema>({
    queryKey: ['preferences'],
    queryFn: () => api.getPreferences(),
  });

  useEffect(() => {
    if (userPrefs) {
      setPrefs(userPrefs);
    }
  }, [userPrefs]);

  // Save Preferences Mutation
  const savePrefsMutation = useMutation({
    mutationFn: (updated: UserPreferencesSchema) => api.updatePreferences(updated),
    onSuccess: (data) => {
      setPrefs(data);
      setBannerMsg({
        type: 'success',
        text: 'Safety governance and automation policies updated successfully.'
      });
      queryClient.invalidateQueries({ queryKey: ['preferences'] });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Failed to save preferences: ${err.message || 'Unknown error'}`
      });
    }
  });

  // Manual Sync Mutation
  const syncMutation = useMutation({
    mutationFn: (count: number) => api.syncMailbox(count),
    onSuccess: (res) => {
      setBannerMsg({
        type: 'success',
        text: `Mailbox sync completed! Inspected ${res.inspected} messages, found ${res.recruitment} recruitment opportunities (${res.new_stored} new).`
      });
      queryClient.invalidateQueries({ queryKey: ['mailbox-status'] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Sync failed: ${err.message || 'Unknown error'}`
      });
    }
  });

  if (isMailboxLoading || isPrefsLoading) {
    return <Loading message="Loading system settings and mailbox configuration..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Sliders className="w-6 h-6 text-neon-cyan" />
            System Settings & Automation Governance
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure remote IMAP sync parameters, guardrail thresholds, and human-in-the-loop enforcement policies.
          </p>
        </div>
      </div>

      {bannerMsg && (
        <StatusBanner 
          type={bannerMsg.type} 
          message={bannerMsg.text} 
          onDismiss={() => setBannerMsg(null)} 
        />
      )}

      {/* Safety Defaults Banner */}
      <div className="p-4 rounded-xl bg-neon-cyan/5 border border-neon-cyan/20 flex items-start gap-3 text-xs text-slate-300">
        <Info className="w-4 h-4 text-neon-cyan shrink-0 mt-0.5" />
        <div>
          <strong className="text-neon-cyan font-medium">Safe Defaults Enforced:</strong>{' '}
          By default, SafeApply keeps auto-quarantine, auto-apply, and live SMTP dispatch disabled. This guarantees all actions require human confirmation until you intentionally choose to enable autonomous handling.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Mailbox Sync & Connection */}
        <div className="space-y-5">
          <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
            <div className="border-b border-border-subtle pb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <Mail className="w-4 h-4 text-neon-cyan" />
                Remote Mailbox Connection
              </h2>
              {mailboxStatus?.is_connected ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-2xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <CheckCircle2 className="w-3 h-3" />
                  Connected
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-2xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  <AlertTriangle className="w-3 h-3" />
                  Local Mock / Sandbox
                </span>
              )}
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-border-subtle/40">
                <span className="text-slate-400">Provider</span>
                <span className="text-white font-medium">{mailboxStatus?.provider || 'Gmail / IMAP'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border-subtle/40">
                <span className="text-slate-400">Account Identity</span>
                <span className="text-white font-mono">{mailboxStatus?.username || 'Configured via Environment'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border-subtle/40">
                <span className="text-slate-400">IMAP Endpoint</span>
                <span className="text-white font-mono">
                  {mailboxStatus?.imap_server || 'imap.gmail.com'}:{mailboxStatus?.imap_port || 993}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border-subtle/40">
                <span className="text-slate-400">Cached Emails in Vault</span>
                <span className="text-white font-mono">{mailboxStatus?.stored_count ?? 0}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Last Successful Sync</span>
                <span className="text-slate-300 font-mono">
                  {mailboxStatus?.last_sync ? new Date(mailboxStatus.last_sync).toLocaleString() : 'Never'}
                </span>
              </div>
            </div>

            {/* Sync Controls */}
            <div className="pt-3 border-t border-border-subtle space-y-3">
              <label className="text-2xs font-semibold uppercase tracking-wider text-slate-400 block">
                Trigger Manual Mailbox Synchronization
              </label>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 bg-surface-raised border border-border-subtle rounded-xl px-3 py-1.5 text-xs">
                  <span className="text-slate-400 text-2xs">Fetch:</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={syncBatchSize}
                    onChange={(e) => setSyncBatchSize(parseInt(e.target.value) || 15)}
                    className="w-12 bg-transparent text-white text-center font-mono focus:outline-none"
                  />
                  <span className="text-slate-500 text-2xs">messages</span>
                </div>

                <button
                  onClick={() => syncMutation.mutate(syncBatchSize)}
                  disabled={syncMutation.isPending}
                  className="flex-1 py-2.5 px-4 rounded-xl bg-surface-raised border border-border-subtle hover:bg-slate-700 text-white font-medium text-xs transition-colors flex items-center justify-center gap-2 shadow-sm"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? 'animate-spin text-neon-cyan' : ''}`} />
                  {syncMutation.isPending ? 'Synchronizing Mailbox...' : 'Sync Mailbox Now'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Automation Policies & Safety Thresholds */}
        <div className="space-y-5">
          <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-5">
            <div className="border-b border-border-subtle pb-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-neon-violet" />
                Autonomous Policies & Guardrails
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Fine-tune safety boundaries for automated mailbox actions and applications.
              </p>
            </div>

            {/* Policy 1: Auto Quarantine */}
            <div className="p-4 rounded-xl bg-surface-raised/40 border border-border-subtle space-y-3">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-neon-coral" />
                    Automated Threat Quarantine
                  </div>
                  <p className="text-2xs text-slate-400">
                    Automatically isolate high-risk phishing and scam emails to Spam.
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={prefs.auto_quarantine_enabled}
                    onChange={(e) => setPrefs({ ...prefs, auto_quarantine_enabled: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-surface-raised peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-neon-coral"></div>
                </label>
              </div>

              {prefs.auto_quarantine_enabled && (
                <div className="space-y-1.5 pt-2 border-t border-border-subtle">
                  <div className="flex justify-between text-2xs">
                    <span className="text-slate-400">Quarantine Risk Threshold:</span>
                    <span className="text-neon-coral font-bold font-mono">≥ {prefs.auto_quarantine_threshold}/100</span>
                  </div>
                  <input
                    type="range"
                    min={40}
                    max={95}
                    value={prefs.auto_quarantine_threshold}
                    onChange={(e) => setPrefs({ ...prefs, auto_quarantine_threshold: parseInt(e.target.value) })}
                    className="w-full accent-neon-coral h-1.5 bg-surface-raised rounded-lg"
                  />
                </div>
              )}
            </div>

            {/* Policy 2: Auto Apply */}
            <div className="p-4 rounded-xl bg-surface-raised/40 border border-border-subtle space-y-3">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Send className="w-3.5 h-3.5 text-neon-cyan" />
                    Autonomous Job Application Submissions
                  </div>
                  <p className="text-2xs text-slate-400">
                    Allow agent to auto-submit applications for verified low-risk jobs.
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={prefs.auto_apply_enabled}
                    onChange={(e) => setPrefs({ ...prefs, auto_apply_enabled: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-surface-raised peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-neon-cyan"></div>
                </label>
              </div>

              {prefs.auto_apply_enabled && (
                <div className="space-y-1.5 pt-2 border-t border-border-subtle">
                  <div className="flex justify-between text-2xs">
                    <span className="text-slate-400">Maximum Allowed Risk Score for Auto-Apply:</span>
                    <span className="text-neon-cyan font-bold font-mono">≤ {prefs.auto_apply_max_risk_score}/100</span>
                  </div>
                  <input
                    type="range"
                    min={10}
                    max={60}
                    value={prefs.auto_apply_max_risk_score}
                    onChange={(e) => setPrefs({ ...prefs, auto_apply_max_risk_score: parseInt(e.target.value) })}
                    className="w-full accent-neon-cyan h-1.5 bg-surface-raised rounded-lg"
                  />
                </div>
              )}
            </div>

            {/* Policy 3: Live SMTP Dispatch */}
            <div className="p-4 rounded-xl bg-surface-raised/40 border border-border-subtle space-y-2">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Server className="w-3.5 h-3.5 text-neon-amber" />
                    Live SMTP Outbound Dispatch
                  </div>
                  <p className="text-2xs text-slate-400">
                    Enable real outbound emails to recruiters via SMTP instead of sandbox records.
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={prefs.enable_real_smtp_dispatch}
                    onChange={(e) => setPrefs({ ...prefs, enable_real_smtp_dispatch: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-surface-raised peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-neon-amber"></div>
                </label>
              </div>

              {prefs.enable_real_smtp_dispatch && (
                <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-2xs text-amber-300">
                  ⚠️ Live SMTP enabled: SafeApply will transmit genuine outbound emails when you approve submissions.
                </div>
              )}
            </div>

            {/* Save Button */}
            <button
              onClick={() => savePrefsMutation.mutate(prefs)}
              disabled={savePrefsMutation.isPending}
              className="w-full py-3 px-4 rounded-xl bg-neon-cyan hover:bg-neon-cyan/90 text-black font-semibold text-xs tracking-wide transition-all shadow-glow-cyan flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              {savePrefsMutation.isPending ? 'Saving Preferences...' : 'Save Automation Policies'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
export default Settings;
