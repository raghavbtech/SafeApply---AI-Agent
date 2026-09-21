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
  SlidersHorizontal,
  Trash2,
  AlertCircle,
  X,
  ExternalLink,
  KeyRound,
  ChevronDown,
} from 'lucide-react';

const ExternalGuideLink: React.FC<{ href: string; label: string }> = ({ href, label }) => (
  <a
    href={href}
    target="_blank"
    rel="noreferrer"
    className="inline-flex items-center gap-1.5 text-neon-cyan hover:text-white underline underline-offset-2"
  >
    {label}<ExternalLink className="w-3 h-3" />
  </a>
);

const GuideStep: React.FC<{ number: string; title: string; children: React.ReactNode }> = ({ number, title, children }) => (
  <section className="space-y-1.5">
    <h3 className="flex items-center gap-2 font-semibold text-white">
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-neon-cyan text-[10px] font-bold text-black">{number}</span>
      {title}
    </h3>
    <div className="pl-7 space-y-1.5 text-slate-400">{children}</div>
  </section>
);

const Faq: React.FC<{ question: string; children: React.ReactNode }> = ({ question, children }) => (
  <details className="border-b border-border-subtle/60 pb-2 last:border-0 last:pb-0">
    <summary className="cursor-pointer font-medium text-slate-200">Q: {question}</summary>
    <p className="mt-1.5 text-slate-400">A: {children}</p>
  </details>
);

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
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [connEmail, setConnEmail] = useState('');
  const [connPass, setConnPass] = useState('');
  const [connServer, setConnServer] = useState('imap.gmail.com');

  const connectMailboxMutation = useMutation({
    mutationFn: () => api.connectMailbox({
      provider: 'Gmail',
      username: connEmail.trim(),
      password_or_app_token: connPass.replace(/\s+/g, ''),
      imap_server: connServer.trim() || 'imap.gmail.com',
      imap_port: 993,
    }),
    onSuccess: () => {
      setConnPass('');
      setShowConnectForm(false);
      queryClient.invalidateQueries({ queryKey: ['mailbox-status'] });
      setBannerMsg({ type: 'success', text: 'Gmail Connected. Your mailbox credentials are protected for this session.' });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Gmail connection failed: ${err.message || 'Check your email and App Password, then try again.'}`,
      });
    },
  });

  // Purge Session Data Mutation
  const purgeMutation = useMutation({
    mutationFn: () => api.purgeSessionData(),
    onSuccess: () => {
      queryClient.clear();
      setBannerMsg({ type: 'success', text: 'All candidate data and session records have been deleted.' });
      setShowDeleteModal(false);
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 1500);
    },
    onError: (err: any) => {
      setBannerMsg({ type: 'error', text: `Failed to delete session data: ${err.message || 'Unknown error'}` });
    },
  });

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
      if (res.ok === false || res.error) {
        setBannerMsg({
          type: 'warning',
          text: `Mailbox sync warning: ${res.error || 'Unable to complete mailbox sync.'}`
        });
      } else {
        setBannerMsg({
          type: 'success',
          text: `Mailbox sync completed! Inspected ${res.inspected || 0} messages, found ${res.recruitment || 0} recruitment opportunities (${res.new_stored || 0} new).`
        });
      }
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

            <details className="group rounded-xl border border-cyan-500/20 bg-cyan-500/5 overflow-hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-cyan-200">
                <span className="flex items-center gap-2"><KeyRound className="w-4 h-4 text-neon-cyan" />How to Connect Your Gmail Account</span>
                <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
              </summary>
              <div className="border-t border-cyan-500/20 px-4 py-4 text-xs text-slate-300 space-y-4">
                <p className="text-slate-300">SafeApply uses Gmail IMAP. For this connection method, use a Google App Password, not your normal Google Account password.</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  <GuideStep number="1" title="Enable Google 2-Step Verification">
                    <p>Open Google Security Settings, sign in, find <strong>2-Step Verification</strong>, and follow Google's instructions. If it is already enabled, continue.</p>
                    <ExternalGuideLink href="https://myaccount.google.com/security" label="Open Google Security Settings" />
                  </GuideStep>
                  <GuideStep number="2" title="Open Google App Passwords">
                    <p>Open App Passwords and sign in again if asked. This option is available only to eligible accounts. Advanced Protection, administrator policies, or other security settings may prevent App Password creation. Do not disable security protections.</p>
                    <ExternalGuideLink href="https://myaccount.google.com/apppasswords" label="Open Google App Passwords" />
                  </GuideStep>
                  <GuideStep number="3" title="Generate a SafeApply App Password">
                    <p>Enter <strong>SafeApply</strong> as the app name, select <strong>Create</strong>, and copy the generated 16-character password. Google generally shows it only once. If it is lost, generate a new one.</p>
                  </GuideStep>
                  <GuideStep number="4" title="Enter Gmail Connection Details">
                    <p>Return here and enter the Gmail address plus the new App Password. The password field is masked. Spaces copied from Google are normalized automatically. Never enter your normal Google password.</p>
                  </GuideStep>
                  <GuideStep number="5" title="Connect Gmail">
                    <p>Click <strong>Connect Gmail</strong>. SafeApply checks the connection before showing Gmail Connected. Failed authentication displays an error and leaves the form available for retry.</p>
                  </GuideStep>
                  <GuideStep number="6" title="Synchronize Recruitment Emails">
                    <p>After connecting, use <strong>Sync Mailbox Now</strong> or open My Mailbox to manually synchronize and analyze recruitment emails. No background scanning or mailbox movement is enabled by connecting alone.</p>
                  </GuideStep>
                </div>
              </div>
            </details>

            {/* Mailbox Connect / Disconnect Buttons */}
            <div className="pt-3 border-t border-border-subtle flex flex-col gap-2">
              {mailboxStatus?.is_connected ? (
                <button
                  type="button"
                  onClick={async () => {
                    if (window.confirm('Disconnect your mailbox and stop monitoring?')) {
                      await api.disconnectMailbox();
                      queryClient.invalidateQueries({ queryKey: ['mailbox-status'] });
                      setBannerMsg({ type: 'warning', text: 'Mailbox disconnected and stored credentials removed.' });
                    }
                  }}
                  className="w-full py-2 px-3 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 font-medium text-xs transition"
                >
                  Disconnect Mailbox & Stop Monitoring
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowConnectForm(!showConnectForm)}
                  className="w-full py-2 px-3 rounded-xl border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 font-medium text-xs transition"
                >
                  {showConnectForm ? 'Cancel Connection' : '+ Connect Personal Mailbox (Gmail / IMAP)'}
                </button>
              )}

              {showConnectForm && !mailboxStatus?.is_connected && (
                <div className="p-3.5 rounded-xl bg-surface-raised border border-border-subtle space-y-2.5 text-xs">
                  <span className="font-semibold text-white block">Connect Mailbox Credentials:</span>
                  <input
                    type="email"
                    required
                    placeholder="your-email@gmail.com"
                    value={connEmail}
                    onChange={(e) => setConnEmail(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg bg-dark-900 border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
                  />
                  <input
                    type="password"
                    placeholder="16-character Google App Password"
                    autoComplete="new-password"
                    value={connPass}
                    onChange={(e) => setConnPass(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg bg-dark-900 border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
                  />
                  <input
                    type="text"
                    placeholder="imap.gmail.com"
                    value={connServer}
                    onChange={(e) => setConnServer(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg bg-dark-900 border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (!connEmail.trim() || !connPass.trim()) {
                        setBannerMsg({ type: 'error', text: 'Gmail address and Google App Password are required.' });
                        return;
                      }
                      if (!/^[^\s@]+@gmail\.com$/i.test(connEmail.trim())) {
                        setBannerMsg({ type: 'error', text: 'Enter a valid Gmail address ending in @gmail.com.' });
                        return;
                      }
                      connectMailboxMutation.mutate();
                    }}
                    disabled={connectMailboxMutation.isPending}
                    className="w-full py-2 rounded-lg bg-neon-cyan text-black font-semibold text-xs"
                  >
                    {connectMailboxMutation.isPending ? 'Checking Gmail Connection...' : 'Connect Gmail'}
                  </button>
                </div>
              )}
            </div>

            <details className="group rounded-xl border border-border-subtle bg-surface-raised/40 overflow-hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-xs font-semibold text-white">
                <span>App Password Help & Gmail Access FAQ</span>
                <ChevronDown className="w-4 h-4 text-slate-400 transition-transform group-open:rotate-180" />
              </summary>
              <div className="border-t border-border-subtle px-4 py-3 space-y-3 text-xs text-slate-300">
                <Faq question="Can I use my regular Gmail password?">No. This IMAP connection method uses a Google App Password.</Faq>
                <Faq question="What if I cannot see the App Passwords option?">Check that 2-Step Verification is enabled and that your account is eligible. Some managed accounts and security configurations do not permit App Passwords.</Faq>
                <Faq question="Can I recover an App Password after closing Google's page?">No. Generate a new App Password if the original is lost.</Faq>
                <Faq question="How do I revoke SafeApply's Gmail access?">Disconnect Gmail here and revoke the corresponding App Password in Google Account settings.</Faq>
                <Faq question="Does connecting Gmail allow SafeApply to send job applications?">No. Mailbox reading and application-email sending are separate capabilities and require separate authorization. Connecting Gmail does not automatically authorize application sending.</Faq>
              </div>
            </details>

            {/* Sync Controls */}
            {mailboxStatus?.is_connected && (
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
            )}
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

      {/* Candidate Privacy & Data Sovereignty Section */}
      <div className="rounded-2xl border border-rose-500/20 bg-dark-900/60 p-6 backdrop-blur-xl space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="font-heading text-sm font-bold text-white flex items-center gap-2">
              <Lock className="h-4 w-4 text-rose-400" />
              Candidate Privacy & Data Sovereignty
            </h3>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              SafeApply operates entirely account-free. All candidate profile details, analyzed emails, uploaded resumes,
              and prepared drafts are partitioned strictly to your anonymous session cookie. You maintain complete control to purge your data at any time.
            </p>
          </div>
        </div>

        <div className="pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="text-2xs text-slate-400">
            Clicking delete will purge your candidate profile, parsed resumes, scanned emails, and prepared applications.
          </div>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="flex items-center justify-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-2.5 text-xs font-bold text-rose-300 hover:bg-rose-500/20 transition shrink-0"
          >
            <Trash2 className="h-4 w-4" />
            <span>Delete All My Session Data</span>
          </button>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="w-full max-w-md rounded-2xl border border-rose-500/40 bg-dark-900 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-rose-400">
                <AlertCircle className="h-5 w-5" />
                <h3 className="font-heading text-sm font-bold text-white">Permanently Delete All Data?</h3>
              </div>
              <button
                onClick={() => setShowDeleteModal(false)}
                className="text-slate-400 hover:text-white transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              This action will permanently delete your candidate profile, uploaded resumes, scanned emails,
              quarantined messages, and application records associated with this session. This action cannot be undone.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="rounded-xl border border-slate-700 bg-dark-850 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-dark-800 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={purgeMutation.isPending}
                onClick={() => purgeMutation.mutate()}
                className="flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2 text-xs font-bold text-white hover:bg-rose-500 transition disabled:opacity-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>{purgeMutation.isPending ? 'Deleting...' : 'Yes, Delete Everything'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default Settings;
