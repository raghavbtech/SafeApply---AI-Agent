import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Inbox as InboxIcon,
  Search,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Scan,
  RefreshCw,
  RotateCcw,
  Building2,
  Mail,
  HelpCircle,
  CheckSquare,
  Square,
  UserCheck,
  CreditCard,
  Video,
  Info,
  ExternalLink,
  Briefcase,
  Layers,
} from 'lucide-react';
import { api } from '../api/client';
import { 
  EmailListItem, 
  VerificationChecklistItem, 
  VerificationChecklistResponse 
} from '../api/contracts';
import { RiskBadge } from '../components/RiskBadge';
import { Loading } from '../components/Loading';
import { EmptyState } from '../components/EmptyState';
import { StatusBanner } from '../components/StatusBanner';
import clsx from 'clsx';

const CHECKLIST_ICONS: Record<string, React.ElementType> = {
  domain: Building2,
  recruiter: UserCheck,
  payment: CreditCard,
  interview: Video,
};

export const Inbox: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // URL Query Parameters
  const tabParam = searchParams.get('tab');
  const selectedParam = searchParams.get('selected');
  const filterParam = searchParams.get('filter');

  const [mainView, setMainView] = useState<'inbox' | 'quarantine'>(
    tabParam === 'quarantine' || tabParam === 'spam' ? 'quarantine' : 'inbox'
  );

  const [filterOpt, setFilterOpt] = useState<string>(
    filterParam === 'Medium' || tabParam === 'verification' ? 'Medium' : 'All'
  );
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [activeAnalysisTab, setActiveAnalysisTab] = useState<'rules' | 'ml' | 'rag' | 'domain'>('rules');

  // Verification state for selected email
  const [checklist, setChecklist] = useState<VerificationChecklistItem[]>([]);
  const [candidateNotes, setCandidateNotes] = useState<string>('');
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  // Sync tab state with URL parameter if it changes externally
  useEffect(() => {
    if (tabParam === 'quarantine' || tabParam === 'spam') {
      setMainView('quarantine');
    } else if (tabParam === 'inbox') {
      setMainView('inbox');
    }
  }, [tabParam]);

  // Fetch Inbox or Quarantined Emails
  const { data: emailData, isLoading } = useQuery({
    queryKey: ['emails', mainView, filterOpt, searchKeyword],
    queryFn: () => {
      let riskLevel: string | undefined = undefined;
      let status: string | undefined = undefined;

      if (mainView === 'inbox') {
        if (filterOpt === 'Unscanned') status = 'unscanned';
        if (filterOpt === 'High') riskLevel = 'High';
        if (filterOpt === 'Medium') riskLevel = 'Medium';
        if (filterOpt === 'Low') riskLevel = 'Low';
        if (filterOpt === 'Applied') status = 'applied';

        return api.listEmails({
          folder: 'inbox',
          status,
          risk_level: riskLevel,
          search: searchKeyword || undefined,
          limit: 10,
        });
      } else {
        return api.listEmails({
          folder: 'spam',
          search: searchKeyword || undefined,
          limit: 50,
        });
      }
    },
    refetchInterval: 12000,
  });

  const emails: EmailListItem[] = emailData?.items || [];

  // Determine selected email
  const selectedEmailId = selectedParam || (emails.length > 0 ? emails[0].id : null);

  // Fetch selected email detail
  const { data: selectedEmail, isLoading: detailLoading } = useQuery({
    queryKey: ['email', selectedEmailId],
    queryFn: () => (selectedEmailId ? api.getEmail(selectedEmailId) : null),
    enabled: !!selectedEmailId,
  });

  // Fetch verification checklist if selected email is Medium risk / ambiguous
  const isAmbiguous = selectedEmail?.risk_level === 'Medium' || selectedEmail?.review_status === 'pending_review';

  const { data: checklistData } = useQuery<VerificationChecklistResponse>({
    queryKey: ['checklist', selectedEmailId],
    queryFn: () => api.getVerificationChecklist(selectedEmailId!),
    enabled: !!selectedEmailId && isAmbiguous,
  });

  useEffect(() => {
    if (checklistData?.checklist) {
      setChecklist(checklistData.checklist);
    }
  }, [checklistData]);

  // Mutations
  const scanMutation = useMutation({
    mutationFn: (emailId: string) => api.analyzeStoredEmail(emailId),
    onSuccess: () => {
      setBannerMsg({ type: 'success', text: '4-Pillar security analysis completed.' });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['email', selectedEmailId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setBannerMsg({ type: 'error', text: `Analysis failed: ${err.message || 'Unknown error'}` });
    }
  });

  const syncMutation = useMutation({
    mutationFn: () => api.syncMailbox(15),
    onSuccess: (res) => {
      if (res.ok === false || res.error) {
        setBannerMsg({
          type: 'warning',
          text: `Mailbox sync warning: ${res.error || 'Unable to fetch recent messages.'}`
        });
      } else {
        setBannerMsg({
          type: 'success',
          text: `Mailbox synchronized: inspected ${res.inspected || 0} messages (${res.new_stored || 0} new recruitment offers).`
        });
      }
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setBannerMsg({ type: 'error', text: `Sync failed: ${err.message || 'Unknown error'}` });
    }
  });

  const spamMutation = useMutation({
    mutationFn: (emailId: string) => api.moveToSpam(emailId, candidateNotes || 'Moved to quarantine by candidate'),
    onSuccess: (data) => {
      const text = data.local_quarantined && data.mailbox_moved
        ? 'Email moved to SafeApply Quarantine and Gmail Spam.'
        : data.local_quarantined && data.error?.includes('No linked Gmail message')
          ? 'Email quarantined in SafeApply. No linked Gmail message was available to move.'
          : data.local_quarantined
            ? 'Email quarantined in SafeApply, but it could not be moved to Gmail Spam. Check your mailbox connection.'
            : (data.error || 'Quarantine failed.');
      setBannerMsg({
        type: data.local_quarantined && data.mailbox_moved ? 'success' : 'warning',
        text,
      });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setBannerMsg({ type: 'error', text: `Failed to move: ${err.message || 'Unknown error'}` });
    }
  });

  const restoreMutation = useMutation({
    mutationFn: (emailId: string) => api.restoreFromSpam(emailId),
    onSuccess: (data) => {
      const restoredInMailbox = data.mailbox_restored === true;
      const localOnlyRestore = data.ok === true && !data.mailbox_restored && !data.error;
      setBannerMsg({
        type: restoredInMailbox ? 'success' : localOnlyRestore ? 'warning' : 'error',
        text: restoredInMailbox
          ? 'Email restored to SafeApply and Gmail Inbox.'
          : localOnlyRestore
            ? 'Email restored in SafeApply. Gmail was not modified.'
            : `Gmail restoration failed: ${data.error || 'Check your mailbox connection.'}`
      });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setBannerMsg({ type: 'error', text: `Failed to restore: ${err.message || 'Unknown error'}` });
    }
  });

  const verificationMutation = useMutation({
    mutationFn: ({ override }: { override: boolean }) =>
      api.updateVerification(selectedEmailId!, checklist, override, candidateNotes),
    onSuccess: (data, vars) => {
      setBannerMsg({
        type: 'success',
        text: vars.override
          ? 'Offer verified as TRUSTED candidate override. Recorded in audit trail.'
          : 'Checklist observations saved.'
      });
      queryClient.invalidateQueries({ queryKey: ['checklist', selectedEmailId] });
      queryClient.invalidateQueries({ queryKey: ['email', selectedEmailId] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setBannerMsg({ type: 'error', text: `Verification update failed: ${err.message || 'Unknown error'}` });
    }
  });

  const selectEmail = (id: string) => {
    setSearchParams({ selected: id, tab: mainView });
  };

  const switchMainView = (view: 'inbox' | 'quarantine') => {
    setMainView(view);
    setSearchParams({ tab: view });
  };

  const toggleCheckItem = (id: string) => {
    setChecklist((prev) =>
      prev.map((item) => (item.id === id ? { ...item, verified: !item.verified } : item))
    );
  };

  return (
    <div className="space-y-4">
      {/* Top Header & View Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <InboxIcon className="w-5 h-5 text-neon-cyan" />
            My Mailbox
          </h1>
          <p className="text-xs text-slate-400">
            Synchronize, review top 10 incoming mailbox messages, verify ambiguous signals, and isolate threats.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Main View Switcher */}
          <div className="flex rounded-xl bg-dark-900 border border-slate-800 p-1 text-xs">
            <button
              onClick={() => switchMainView('inbox')}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition',
                mainView === 'inbox'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-neon-cyan'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              <InboxIcon className="w-3.5 h-3.5" />
              Active Inbox
            </button>
            <button
              onClick={() => switchMainView('quarantine')}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition',
                mainView === 'quarantine'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-neon-rose'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              Quarantined Threats
            </button>
          </div>

          {/* Sync Button */}
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-dark-900 border border-slate-700 hover:border-cyan-500/50 text-xs font-semibold text-slate-200 hover:text-cyan-300 transition disabled:opacity-50"
          >
            <RefreshCw className={clsx('w-3.5 h-3.5', syncMutation.isPending && 'animate-spin')} />
            <span>{syncMutation.isPending ? 'Syncing...' : 'Sync Mailbox'}</span>
          </button>
        </div>
      </div>

      {bannerMsg && (
        <StatusBanner
          type={bannerMsg.type}
          message={bannerMsg.text}
          onDismiss={() => setBannerMsg(null)}
        />
      )}

      {/* Two-Pane Workspace */}
      <div className="flex h-[calc(100vh-12rem)] gap-5 overflow-hidden">
        {/* LEFT COLUMN: Message List */}
        <div className="flex w-[380px] shrink-0 min-w-0 flex-col rounded-2xl border border-slate-800/80 bg-dark-900/60 backdrop-blur-xl">
          {/* List Header & Filters */}
          <div className="border-b border-slate-800 p-3.5 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300">
                {mainView === 'inbox' ? 'Top 10 Inbox Messages' : 'Isolated Threats Vault'}
              </span>
              <span className="text-2xs font-mono text-slate-500">
                {emails.length} {mainView === 'inbox' ? 'messages (Top 10)' : 'items'}
              </span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search company, subject, sender..."
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                className="w-full rounded-xl border border-slate-700/80 bg-dark-850 pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            {/* Inbox Filter Pills (Only shown in Active Inbox) */}
            {mainView === 'inbox' && (
              <div className="flex flex-wrap gap-1 text-2xs">
                {['All', 'Unscanned', 'High', 'Medium', 'Low', 'Applied'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setFilterOpt(filter)}
                    className={clsx(
                      'rounded-md px-2 py-0.5 font-medium transition',
                      filterOpt === filter
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        : 'bg-dark-850 text-slate-400 hover:text-slate-200'
                    )}
                  >
                    {filter === 'High' ? '🚨 High' : filter === 'Medium' ? '⚠️ Ambiguous' : filter === 'Low' ? '✅ Low Risk' : filter}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Scrollable Message List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {isLoading ? (
              <Loading message="Fetching messages..." />
            ) : emails.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                {mainView === 'inbox'
                  ? 'No messages found in active inbox. Sync your mailbox or run a manual scan.'
                  : 'Quarantine vault is empty. No threats currently isolated.'}
              </div>
            ) : (
              emails.map((em) => {
                const isSelected = em.id === selectedEmailId;
                const hasImapMoved = em.mailbox_action === 'moved_to_spam' || em.mailbox_action === 'moved_to_junk';

                return (
                  <div
                    key={em.id}
                    onClick={() => selectEmail(em.id)}
                    className={clsx(
                      'cursor-pointer rounded-xl border p-3 transition-all duration-150',
                      isSelected
                        ? mainView === 'quarantine'
                          ? 'border-rose-500/50 bg-rose-500/10 shadow-neon-rose'
                          : 'border-cyan-500/50 bg-cyan-500/10 shadow-neon-cyan'
                        : 'border-slate-800/80 bg-dark-850/40 hover:border-slate-700 hover:bg-dark-850/80'
                    )}
                  >
                    <div className="flex items-center justify-between gap-2 min-w-0">
                      <span className="text-2xs font-semibold text-slate-500 truncate min-w-0 flex-1">{em.date || em.id}</span>
                      <div className="shrink-0"><RiskBadge level={em.risk_level} score={em.risk_score} status={em.status} /></div>
                    </div>

                    <h4 className="mt-1 text-xs font-bold text-white truncate">{em.subject}</h4>
                    <div className="mt-1 flex items-center justify-between text-2xs text-slate-400">
                      <span className="truncate font-medium text-slate-300">{em.company_name}</span>
                      {hasImapMoved && (
                        <span className="text-2xs font-mono text-rose-400 bg-rose-500/10 px-1 rounded">IMAP Spam</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Dossier View, Verification & 4-Pillars */}
        <div className="flex flex-1 min-w-0 flex-col rounded-2xl border border-slate-800/80 bg-dark-900/60 backdrop-blur-xl overflow-y-auto p-5 space-y-5">
          {detailLoading ? (
            <Loading message="Loading offer dossier & risk assessment..." />
          ) : !selectedEmail ? (
            <EmptyState
              title="No Message Selected"
              description="Select an email from the left pane to view its security analysis, verification checklist, or quarantine actions."
            />
          ) : (
            <>
              {/* Header / Meta Card */}
              <div className="rounded-xl border border-slate-800 bg-dark-850/70 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1.5 min-w-0">
                    <h3 className="text-sm font-bold text-white truncate">{selectedEmail.subject}</h3>
                    <div className="space-y-0.5 text-xs text-slate-400">
                      <p className="flex items-center gap-2 truncate">
                        <Mail className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                        <span className="font-semibold text-slate-300">{selectedEmail.sender_name}</span>
                        <span className="text-slate-500 truncate">&lt;{selectedEmail.sender}&gt;</span>
                      </p>
                      <p className="flex items-center gap-2 text-2xs">
                        <Building2 className="h-3.5 w-3.5 text-violet-400 shrink-0" />
                        <span>Claimed: <b>{selectedEmail.company_name && !["unknown", "not specified"].includes(selectedEmail.company_name.toLowerCase()) ? selectedEmail.company_name : (selectedEmail.analysis?.extracted_data?.company_name || "Not identified")}</b> <span className="text-amber-300">(unverified claim)</span></span>
                        <span>· Date: {selectedEmail.date}</span>
                      </p>
                    </div>
                  </div>

                  <div className="shrink-0 flex flex-col items-end gap-2">
                    <RiskBadge
                      level={selectedEmail.risk_level}
                      score={selectedEmail.risk_score}
                      status={selectedEmail.status}
                    />

                    {selectedEmail.status === 'unscanned' && (
                      <button
                        onClick={() => scanMutation.mutate(selectedEmail.id)}
                        disabled={scanMutation.isPending}
                        className="flex items-center gap-1.5 rounded-lg bg-cyan-500/20 px-3 py-1 text-xs font-bold text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition shadow-neon-cyan"
                      >
                        <Scan className="h-3 w-3" />
                        {scanMutation.isPending ? 'Scanning...' : 'Scan Offer'}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* QUARANTINE ACTION BAR (When viewing Quarantined item) */}
              {mainView === 'quarantine' || selectedEmail.status === 'quarantined' ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-rose-400 flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4" />
                      Isolated Threat in Secure Vault
                    </span>
                    <button
                      onClick={() => restoreMutation.mutate(selectedEmail.id)}
                      disabled={restoreMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
                    >
                      <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
                      {restoreMutation.isPending ? 'Restoring...' : 'Restore to Active Inbox'}
                    </button>
                  </div>
                  <p className="text-2xs text-slate-300">
                    This solicitation was flagged and isolated to protect your inbox. If you believe this is a legitimate communication, you can safely restore it.
                  </p>
                </div>
              ) : null}

              {/* CONTEXTUAL VERIFICATION CHECKLIST (For Medium / Ambiguous offers) */}
              {isAmbiguous && checklist.length > 0 && mainView === 'inbox' && (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-amber-500/20">
                    <span className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
                      <HelpCircle className="w-4 h-4 text-amber-400" />
                      Candidate Verification Checklist (Ambiguous Offer)
                    </span>
                    <span className="text-2xs text-slate-400">
                      Original Risk: {selectedEmail.risk_score}/100
                    </span>
                  </div>

                  <p className="text-2xs text-slate-300">
                    SafeApply detected incomplete or borderline signals. Review these verification items before responding:
                  </p>

                  <div className="space-y-2">
                    {checklist.map((item) => {
                      const IconComponent = CHECKLIST_ICONS[item.risk_type.toLowerCase()] || AlertTriangle;
                      return (
                        <div
                          key={item.id}
                          onClick={() => toggleCheckItem(item.id)}
                          className={clsx(
                            'p-2.5 rounded-lg border text-xs cursor-pointer transition flex items-start gap-2.5',
                            item.verified
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-slate-200'
                              : 'bg-dark-850 border-slate-800 text-slate-300 hover:border-slate-700'
                          )}
                        >
                          {item.verified ? (
                            <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                          )}
                          <div className="space-y-0.5 flex-1">
                            <span className="font-semibold text-white block">{item.description}</span>
                            <span className="text-2xs text-slate-400 block">{item.recommended_action}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Candidate Decision Actions */}
                  <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-amber-500/20">
                    <button
                      onClick={() => verificationMutation.mutate({ override: true })}
                      disabled={verificationMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white transition shadow-neon-emerald"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {verificationMutation.isPending ? 'Saving...' : 'Verify & Trust Offer (Candidate Override)'}
                    </button>

                    <button
                      onClick={() => spamMutation.mutate(selectedEmail.id)}
                      disabled={spamMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600/80 hover:bg-rose-500 text-xs font-bold text-white transition"
                    >
                      <ShieldAlert className="w-3.5 h-3.5" />
                      {spamMutation.isPending ? 'Moving...' : 'Flag & Move to Quarantine'}
                    </button>
                  </div>
                </div>
              )}

              {/* 4-Pillar Security Analysis */}
              {selectedEmail.analysis && (
                <div className="space-y-4">
                  {/* Summary card */}
                  <div className="rounded-xl border border-slate-800 bg-dark-850/50 p-4 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-200">
                      <span>Advisory Security Assessment: {selectedEmail.risk_score}/100 ({selectedEmail.risk_level} Risk)</span>
                      <span className="text-2xs font-normal text-slate-500">
                        {selectedEmail.analysis.execution_mode || '4-Pillar Analysis'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {selectedEmail.analysis.explanation}
                    </p>
                  </div>

                  {/* Breakdown Tabs */}
                  <div className="rounded-xl border border-slate-800 bg-dark-850/40 p-4 space-y-3">
                    <div className="flex gap-1.5 border-b border-slate-800 pb-2 text-xs">
                      {[
                        { key: 'rules', label: '1. Rules & Red Flags' },
                        { key: 'ml', label: '2. EMSCAD ML' },
                        { key: 'rag', label: '3. Azure Search RAG' },
                        { key: 'domain', label: '4. Domain & Salary' },
                      ].map((t) => (
                        <button
                          key={t.key}
                          onClick={() => setActiveAnalysisTab(t.key as any)}
                          className={clsx(
                            'rounded-lg px-2.5 py-1 font-semibold transition text-2xs',
                            activeAnalysisTab === t.key
                              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                              : 'text-slate-400 hover:text-slate-200'
                          )}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>

                    <div className="text-xs">
                      {activeAnalysisTab === 'rules' && (
                        <div>
                          {selectedEmail.analysis.identified_red_flags?.length > 0 ? (
                            <div className="space-y-1.5">
                              {selectedEmail.analysis.identified_red_flags.map((flag: string, i: number) => (
                                <div key={i} className="flex items-start gap-2 rounded-lg bg-rose-500/10 border border-rose-500/20 p-2 text-rose-300 text-xs">
                                  <span>🚩</span>
                                  <span>{flag}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-emerald-400 font-medium text-xs">
                              ✅ No upfront registration fee or urgency red flags observed.
                            </div>
                          )}
                        </div>
                      )}

                      {activeAnalysisTab === 'ml' && (
                        <div className="grid grid-cols-2 gap-3">
                          <div className="rounded-lg bg-dark-900 p-2.5 border border-slate-800">
                            <span className="text-2xs text-slate-400 uppercase font-bold">Fraud Probability</span>
                            <p className="text-lg font-bold text-white mt-0.5">
                              {selectedEmail.analysis.tool_outputs?.ml_classifier?.fraud_probability_pct ??
                               selectedEmail.analysis.ml_classifier?.fraud_probability_pct ?? 0}%
                            </p>
                          </div>
                          <div className="rounded-lg bg-dark-900 p-2.5 border border-slate-800">
                            <span className="text-2xs text-slate-400 uppercase font-bold">Model Band</span>
                            <p className="text-lg font-bold text-white mt-0.5">
                              {selectedEmail.analysis.tool_outputs?.ml_classifier?.risk_band ??
                               selectedEmail.analysis.ml_classifier?.risk_band ?? 'Standard'}
                            </p>
                          </div>
                        </div>
                      )}

                      {activeAnalysisTab === 'rag' && (
                        <div className="space-y-2">
                          {selectedEmail.analysis.tool_outputs?.rag_matches?.length > 0 ? (
                            selectedEmail.analysis.tool_outputs.rag_matches.map((pat: any, i: number) => (
                              <div key={i} className="rounded-lg bg-dark-900 p-2 border border-slate-800 text-2xs">
                                <span className="font-bold text-amber-300">Related reference: {String(pat.category || "unknown").replace(/_/g, " ")}</span>
                                {Array.isArray(pat.evidence) && pat.evidence.length > 0 ? (
                                  <div className="mt-1 text-slate-200"><span className="font-semibold">Observed in this email:</span> {pat.evidence.join('; ')}</div>
                                ) : <p className="mt-1 text-amber-300">No direct evidence recorded for this reference.</p>}
                                <p className="mt-1 text-slate-400"><span className="font-semibold">Related knowledge-base pattern (not an observed fact):</span> {pat.pattern}</p>
                              </div>
                            ))
                          ) : (
                            <p className="text-slate-500 text-2xs">No matched historical scam patterns.</p>
                          )}
                        </div>
                      )}

                      {activeAnalysisTab === 'domain' && (
                        <div className="space-y-1 text-xs text-slate-300">
                          <p><b>Domain:</b> {selectedEmail.analysis.tool_outputs?.domain_verification?.message || selectedEmail.analysis.tool_outputs?.domain_verification?.status || 'Employer affiliation not verified'}</p>
                          <p><b>Salary Sanity:</b> {selectedEmail.analysis.tool_outputs?.salary_sanity?.message || selectedEmail.analysis.tool_outputs?.salary_sanity?.assessment || 'No salary assessment available'}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Action Shortcuts for Low Risk offers */}
                  {selectedEmail.risk_level === 'Low' && mainView === 'inbox' && (
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 flex items-center justify-between">
                      <div>
                        <span className="font-bold text-emerald-400 text-xs">Advisory Low Risk Offer</span>
                        <p className="text-2xs text-slate-400">Match with your candidate profile and draft application materials.</p>
                      </div>
                      <button
                        onClick={() => navigate(`/applications?email_id=${selectedEmail.id}&tab=prepare`)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white shadow-neon-emerald transition"
                      >
                        <Briefcase className="w-3.5 h-3.5" />
                        Apply in Job Applications
                      </button>
                    </div>
                  )}

                  {/* Manual Quarantine Button for Active Inbox offers */}
                  {(selectedEmail.risk_level === 'High' || selectedEmail.risk_level === 'Critical') && mainView === 'inbox' && (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 flex items-center justify-between">
                      <div>
                        <span className="font-bold text-rose-400 text-xs">High-Risk Fraud Threat</span>
                        <p className="text-2xs text-slate-400">Isolate this communication into the secure quarantine vault.</p>
                      </div>
                      <button
                        onClick={() => spamMutation.mutate(selectedEmail.id)}
                        disabled={spamMutation.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-bold text-white shadow-neon-rose transition"
                      >
                        <ShieldAlert className="w-3.5 h-3.5" />
                        {spamMutation.isPending ? 'Isolating...' : 'Move to Quarantine'}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Original Message Body */}
              <div className="rounded-xl border border-slate-800 bg-dark-850/30 p-3.5 space-y-2">
                <span className="text-2xs font-bold uppercase tracking-wider text-slate-400">Message Content</span>
                <pre className="max-h-56 overflow-y-auto whitespace-pre-wrap break-words overflow-x-hidden rounded-lg bg-dark-950 p-3 font-mono text-[11px] text-slate-300 max-w-full">
                  {selectedEmail.body}
                </pre>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
