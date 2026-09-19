import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Inbox as InboxIcon,
  Search,
  Filter,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Send,
  Scan,
  FileText,
  Clock,
  Sparkles,
  ChevronDown,
  Building2,
  Mail,
} from 'lucide-react';
import { api } from '../api/client';
import { RiskBadge } from '../components/RiskBadge';
import { Loading } from '../components/Loading';
import { EmptyState } from '../components/EmptyState';
import clsx from 'clsx';

export const Inbox: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const selectedParam = searchParams.get('selected');
  const [filterOpt, setFilterOpt] = useState<string>('All');
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'rules' | 'ml' | 'rag' | 'domain'>('rules');

  // Fetch emails
  const { data: emailData, isLoading } = useQuery({
    queryKey: ['emails', filterOpt, searchKeyword],
    queryFn: () => {
      let riskLevel: string | undefined = undefined;
      let status: string | undefined = undefined;

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
      });
    },
    refetchInterval: 10000,
  });

  const emails = emailData?.items || [];

  // Determine selected email
  const selectedEmailId = selectedParam || (emails.length > 0 ? emails[0].id : null);

  // Fetch selected email detail
  const { data: selectedEmail, isLoading: detailLoading } = useQuery({
    queryKey: ['email', selectedEmailId],
    queryFn: () => (selectedEmailId ? api.getEmail(selectedEmailId) : null),
    enabled: !!selectedEmailId,
  });

  // Actions
  const scanMutation = useMutation({
    mutationFn: (emailId: string) => api.analyzeStoredEmail(emailId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['email', selectedEmailId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const spamMutation = useMutation({
    mutationFn: (emailId: string) => api.moveToSpam(emailId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const selectEmail = (id: string) => {
    setSearchParams({ selected: id });
  };

  return (
    <div className="flex h-[calc(100vh-8.5rem)] gap-6 overflow-hidden">
      {/* LEFT COLUMN: Message List */}
      <div className="flex w-2/5 flex-col rounded-2xl border border-slate-800/80 bg-dark-900/60 backdrop-blur-xl">
        {/* Header & Controls */}
        <div className="border-b border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-heading text-sm font-bold text-white">Incoming Messages</span>
            <span className="text-xs font-semibold text-slate-400">{emails.length} offers</span>
          </div>

          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search sender, company, role..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              className="w-full rounded-xl border border-slate-700/80 bg-dark-850 pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap gap-1.5 text-[11px]">
            {['All', 'Unscanned', 'High', 'Medium', 'Low', 'Applied'].map((filter) => (
              <button
                key={filter}
                onClick={() => setFilterOpt(filter)}
                className={clsx(
                  'rounded-lg px-2.5 py-1 font-semibold transition',
                  filterOpt === filter
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-neon-cyan'
                    : 'bg-dark-850 text-slate-400 hover:text-slate-200'
                )}
              >
                {filter === 'High' ? '🚨 High Risk' : filter === 'Medium' ? '⚠️ Ambiguous' : filter === 'Low' ? '✅ Legitimate' : filter}
              </button>
            ))}
          </div>
        </div>

        {/* Scrollable Email List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoading ? (
            <Loading label="Fetching inbox messages..." />
          ) : emails.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No messages match this filter.
            </div>
          ) : (
            emails.map((em) => {
              const isSelected = em.id === selectedEmailId;
              return (
                <div
                  key={em.id}
                  onClick={() => selectEmail(em.id)}
                  className={clsx(
                    'cursor-pointer rounded-xl border p-3.5 transition-all duration-200',
                    isSelected
                      ? 'border-cyan-500/50 bg-cyan-500/5 shadow-neon-cyan'
                      : 'border-slate-800/80 bg-dark-850/40 hover:border-slate-700 hover:bg-dark-850/80'
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-semibold text-slate-500 truncate">{em.id} · {em.date}</span>
                    <RiskBadge level={em.risk_level} score={em.risk_score} status={em.status} />
                  </div>

                  <h4 className="mt-1 font-heading text-xs font-bold text-white truncate">{em.subject}</h4>
                  <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="truncate font-semibold text-slate-300">{em.company_name}</span>
                    <span className="truncate text-slate-500">{em.role_title}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* RIGHT COLUMN: Dossier View & 4-Pillar Breakdown */}
      <div className="flex w-3/5 flex-col rounded-2xl border border-slate-800/80 bg-dark-900/60 backdrop-blur-xl overflow-y-auto p-6">
        {detailLoading ? (
          <Loading label="Loading email dossier & risk analysis..." />
        ) : !selectedEmail ? (
          <EmptyState
            title="No Email Selected"
            description="Select an incoming recruitment email from the left pane to view its security analysis and job match dossier."
          />
        ) : (
          <div className="space-y-6">
            {/* Header / Meta Card */}
            <div className="rounded-xl border border-slate-800 bg-dark-850/70 p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-heading text-base font-bold text-white">{selectedEmail.subject}</h3>
                  <div className="mt-2 space-y-1 text-xs text-slate-400">
                    <p className="flex items-center gap-2">
                      <Mail className="h-3.5 w-3.5 text-cyan-400" />
                      <span className="font-semibold text-slate-300">{selectedEmail.sender_name}</span>
                      <span className="text-slate-500">&lt;{selectedEmail.sender}&gt;</span>
                    </p>
                    <p className="flex items-center gap-2">
                      <Building2 className="h-3.5 w-3.5 text-violet-400" />
                      <span>Claimed Employer: <b>{selectedEmail.company_name}</b></span>
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
                      className="mt-1 flex items-center gap-1.5 rounded-lg bg-cyan-500/20 px-3 py-1 text-xs font-bold text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition shadow-neon-cyan"
                    >
                      <Scan className="h-3.5 w-3.5" />
                      {scanMutation.isPending ? 'Analyzing...' : 'Scan Offer'}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Analysis Breakdown if Scanned */}
            {selectedEmail.analysis ? (
              <div className="space-y-4">
                {/* Agent Risk Assessment Explanation */}
                <div className="rounded-xl border border-slate-800 bg-dark-850/50 p-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-200">
                      SafeApply Assessment ({selectedEmail.risk_score}/100 — {selectedEmail.risk_level} Risk)
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {selectedEmail.analysis.execution_mode || 'Live 4-Pillar Pipeline'}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-300 leading-relaxed">
                    {selectedEmail.analysis.explanation}
                  </p>
                </div>

                {/* 4-Pillar Breakdown Tabs */}
                <div className="rounded-xl border border-slate-800 bg-dark-850/40 p-4">
                  <div className="flex gap-2 border-b border-slate-800 pb-2 text-xs">
                    {[
                      { key: 'rules', label: '1. Rules & Red Flags' },
                      { key: 'ml', label: '2. EMSCAD ML' },
                      { key: 'rag', label: '3. Azure Search RAG' },
                      { key: 'domain', label: '4. Domain & Salary' },
                    ].map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key as any)}
                        className={clsx(
                          'rounded-lg px-3 py-1.5 font-semibold transition',
                          activeTab === tab.key
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                            : 'text-slate-400 hover:text-slate-200'
                        )}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  <div className="mt-4 text-xs">
                    {activeTab === 'rules' && (
                      <div>
                        {selectedEmail.analysis.identified_red_flags?.length > 0 ? (
                          <div className="space-y-2">
                            <span className="font-bold text-rose-400">Observed Scam Indicators:</span>
                            {selectedEmail.analysis.identified_red_flags.map((flag: string, i: number) => (
                              <div key={i} className="flex items-start gap-2 rounded-lg bg-rose-500/10 border border-rose-500/20 p-2 text-rose-300">
                                <span>🚩</span>
                                <span>{flag}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-emerald-400 font-medium">
                            ✅ No deterministic advance-fee or urgency red flags observed in message headers or body.
                          </div>
                        )}
                      </div>
                    )}

                    {activeTab === 'ml' && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="rounded-lg bg-dark-900 p-3 border border-slate-800">
                            <span className="text-[10px] text-slate-400 uppercase font-bold">Fraud Probability</span>
                            <p className="text-xl font-bold text-white mt-1">
                              {selectedEmail.analysis.tool_outputs?.ml_classifier?.fraud_probability_pct ??
                               selectedEmail.analysis.ml_classifier?.fraud_probability_pct ?? 0}%
                            </p>
                          </div>
                          <div className="rounded-lg bg-dark-900 p-3 border border-slate-800">
                            <span className="text-[10px] text-slate-400 uppercase font-bold">Model Band</span>
                            <p className="text-xl font-bold text-white mt-1">
                              {selectedEmail.analysis.tool_outputs?.ml_classifier?.risk_band ??
                               selectedEmail.analysis.ml_classifier?.risk_band ?? 'Standard'}
                            </p>
                          </div>
                        </div>
                        <p className="text-[11px] text-slate-500">
                          Statistical model trained on 17,880 EMSCAD real-world job postings.
                        </p>
                      </div>
                    )}

                    {activeTab === 'rag' && (
                      <div className="space-y-2">
                        {selectedEmail.analysis.tool_outputs?.rag_matches?.length > 0 ? (
                          selectedEmail.analysis.tool_outputs.rag_matches.map((pat: any, i: number) => (
                            <div key={i} className="rounded-lg bg-dark-900 p-2.5 border border-slate-800">
                              <span className="font-bold text-amber-300">Category: {pat.category}</span>
                              <p className="mt-1 text-slate-400">{pat.pattern}</p>
                            </div>
                          ))
                        ) : (
                          <p className="text-slate-500">No gated RAG scam patterns matched this offer text.</p>
                        )}
                      </div>
                    )}

                    {activeTab === 'domain' && (
                      <div className="space-y-2">
                        <p className="text-slate-300">
                          <b>Domain Assessment:</b>{' '}
                          {selectedEmail.analysis.tool_outputs?.domain_verification?.assessment || 'Verified'}
                        </p>
                        <p className="text-slate-300">
                          <b>Salary Sanity:</b>{' '}
                          {selectedEmail.analysis.tool_outputs?.salary_sanity?.assessment || 'Realistic'}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Workflow Actions (High Risk vs Low Risk vs Medium Risk) */}
                <div className="pt-2">
                  {selectedEmail.risk_level === 'High' || selectedEmail.risk_level === 'Critical' ? (
                    <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 space-y-3">
                      <div className="flex items-center gap-2 text-rose-400 font-bold text-xs">
                        <ShieldAlert className="h-4 w-4" />
                        High-Risk Scam Threat Detected
                      </div>
                      <p className="text-xs text-slate-300">
                        SafeApply identified severe recruitment fraud indicators. Move this threat to Junk to isolate it.
                      </p>
                      <button
                        onClick={() => spamMutation.mutate(selectedEmail.id)}
                        disabled={spamMutation.isPending}
                        className="rounded-lg bg-rose-600 px-4 py-2 text-xs font-bold text-white shadow-neon-rose hover:bg-rose-500 transition disabled:opacity-50"
                      >
                        {spamMutation.isPending ? 'Moving to Junk...' : '🛡️ Move to Mailbox Junk / Quarantine'}
                      </button>
                    </div>
                  ) : selectedEmail.risk_level === 'Low' ? (
                    <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 flex items-center justify-between">
                      <div>
                        <span className="font-bold text-emerald-400 text-xs">Legitimate Opportunity Verified</span>
                        <p className="text-xs text-slate-400">Ready for Autonomous Job Application review & tailoring.</p>
                      </div>
                      <a
                        href={`/job-agent?email=${selectedEmail.id}`}
                        className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-neon-emerald hover:bg-emerald-500 transition"
                      >
                        🚀 Open Job Agent
                      </a>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 flex items-center justify-between">
                      <div>
                        <span className="font-bold text-amber-400 text-xs">Ambiguous Offer — Incomplete Signals</span>
                        <p className="text-xs text-slate-400">Requires candidate verification before applying or responding.</p>
                      </div>
                      <a
                        href={`/verification?email=${selectedEmail.id}`}
                        className="rounded-lg bg-amber-600 px-4 py-2 text-xs font-bold text-white hover:bg-amber-500 transition"
                      >
                        ⚠️ Review Verification
                      </a>
                    </div>
                  )}
                </div>
              </div>
            ) : null}

            {/* Original Message Content */}
            <div className="rounded-xl border border-slate-800 bg-dark-850/30 p-4">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Original Message Content</span>
              <pre className="mt-3 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg bg-dark-950 p-3 font-mono text-[11px] text-slate-300">
                {selectedEmail.body}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
