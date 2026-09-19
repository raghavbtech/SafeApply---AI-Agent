import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { 
  VerificationChecklistResponse, 
  VerificationChecklistItem, 
  EmailListItem 
} from '../api/contracts';
import { RiskBadge } from '../components/RiskBadge';
import { Loading } from '../components/Loading';
import { EmptyState } from '../components/EmptyState';
import { StatusBanner } from '../components/StatusBanner';
import {
  HelpCircle,
  CheckSquare,
  Square,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Info,
  Building,
  UserCheck,
  CreditCard,
  Video
} from 'lucide-react';

const CHECKLIST_ICONS: Record<string, React.ElementType> = {
  domain: Building,
  recruiter: UserCheck,
  payment: CreditCard,
  interview: Video,
};

export const Verification: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const emailIdParam = searchParams.get('email_id');

  const [selectedEmailId, setSelectedEmailId] = useState<string>(emailIdParam || '');
  const [checklist, setChecklist] = useState<VerificationChecklistItem[]>([]);
  const [candidateNotes, setCandidateNotes] = useState<string>('');
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  // Fetch emails with Medium risk or ambiguous review status
  const { data: emailListResponse, isLoading: isListLoading } = useQuery({
    queryKey: ['verification-emails'],
    queryFn: () => api.listEmails({ risk_level: 'Medium', limit: 50 }),
  });

  const mediumEmails: EmailListItem[] = emailListResponse?.items || [];

  // Update selectedEmailId if URL param changes or default to first medium email
  useEffect(() => {
    if (emailIdParam) {
      setSelectedEmailId(emailIdParam);
    } else if (mediumEmails.length > 0 && !selectedEmailId) {
      setSelectedEmailId(mediumEmails[0].id);
    }
  }, [emailIdParam, mediumEmails, selectedEmailId]);

  // Fetch checklist for selected email
  const { 
    data: checklistData, 
    isLoading: isChecklistLoading,
    error: checklistError 
  } = useQuery<VerificationChecklistResponse>({
    queryKey: ['checklist', selectedEmailId],
    queryFn: () => api.getVerificationChecklist(selectedEmailId),
    enabled: !!selectedEmailId,
  });

  // Synchronize local checklist state when checklistData loads
  useEffect(() => {
    if (checklistData?.checklist) {
      setChecklist(checklistData.checklist);
    }
  }, [checklistData]);

  // Mutation for updating checklist / override
  const updateMutation = useMutation({
    mutationFn: ({ override }: { override: boolean }) =>
      api.updateVerification(selectedEmailId, checklist, override, candidateNotes),
    onSuccess: (data, variables) => {
      setBannerMsg({
        type: 'success',
        text: variables.override 
          ? 'Offer successfully verified and marked as TRUSTED by candidate.' 
          : 'Checklist progress saved.'
      });
      queryClient.invalidateQueries({ queryKey: ['checklist', selectedEmailId] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Failed to update verification: ${err.message || 'Unknown error'}`
      });
    }
  });

  // Mutation for quarantine if candidate finds red flags
  const quarantineMutation = useMutation({
    mutationFn: () => api.moveToSpam(selectedEmailId, `Failed candidate verification: ${candidateNotes || 'Red flags identified'}`),
    onSuccess: () => {
      setBannerMsg({
        type: 'warning',
        text: 'Offer flagged as malicious and routed to Quarantine Vault.'
      });
      queryClient.invalidateQueries({ queryKey: ['verification-emails'] });
      queryClient.invalidateQueries({ queryKey: ['quarantine'] });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Failed to quarantine: ${err.message || 'Unknown error'}`
      });
    }
  });

  const toggleCheckItem = (id: string) => {
    setChecklist((prev) =>
      prev.map((item) => (item.id === id ? { ...item, verified: !item.verified } : item))
    );
  };

  const allVerified = checklist.length > 0 && checklist.every((item) => item.verified);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <HelpCircle className="w-6 h-6 text-neon-cyan" />
            Offer Verification Checklist
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Resolve ambiguous, borderline, or unconfirmed solicitations with structured human-in-the-loop verification.
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

      {/* Info notice */}
      <div className="p-4 rounded-xl bg-neon-cyan/5 border border-neon-cyan/20 flex items-start gap-3 text-xs text-slate-300">
        <Info className="w-4 h-4 text-neon-cyan shrink-0 mt-0.5" />
        <div>
          <strong className="text-neon-cyan font-medium">Verification Protocol:</strong>{' '}
          Autonomous agents must never auto-apply or discard ambiguous offers without candidate approval. Complete the four-point verification checks below to safely mark an offer as trusted or immediately isolate it in the Threat Vault.
        </div>
      </div>

      {/* Email selector selector if multiple pending */}
      <div className="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="text-xs text-slate-300 font-medium">
          Select Solicitation to Review:
        </div>
        <div className="flex-1 max-w-md">
          {isListLoading ? (
            <span className="text-xs text-slate-500">Loading pending offers...</span>
          ) : mediumEmails.length === 0 && !selectedEmailId ? (
            <span className="text-xs text-slate-500">No ambiguous offers pending verification.</span>
          ) : (
            <select
              value={selectedEmailId}
              onChange={(e) => {
                setSelectedEmailId(e.target.value);
                setSearchParams({ email_id: e.target.value });
              }}
              className="w-full px-3 py-2 text-xs rounded-lg bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
            >
              {mediumEmails.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.subject || '(No Subject)'} — {e.company || e.sender}
                </option>
              ))}
              {selectedEmailId && !mediumEmails.some((e) => e.id === selectedEmailId) && (
                <option value={selectedEmailId}>Email ID: {selectedEmailId}</option>
              )}
            </select>
          )}
        </div>
      </div>

      {!selectedEmailId ? (
        <EmptyState
          icon={HelpCircle}
          title="No Ambiguous Offer Selected"
          description="Select an email from your Inbox or choose from the dropdown above to begin the verification protocol."
        />
      ) : isChecklistLoading ? (
        <Loading message="Fetching verification checklist and security signals..." />
      ) : checklistError ? (
        <EmptyState
          icon={AlertTriangle}
          title="Verification Unavailable"
          description="Could not load verification checklist for the specified message."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Checklist Form */}
          <div className="lg:col-span-2 space-y-4">
            <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-5">
              <div className="flex items-center justify-between border-b border-border-subtle pb-4">
                <div>
                  <h2 className="text-base font-semibold text-white">
                    4-Point Integrity Checklist
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Review each safety indicator. Check off items you have independently confirmed.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 font-mono">Risk Score:</span>
                  <span className="text-xs font-bold text-neon-amber px-2 py-0.5 rounded bg-neon-amber/10 border border-neon-amber/30">
                    {checklistData?.original_risk_score ?? 'N/A'}/100
                  </span>
                  <RiskBadge level={(checklistData?.original_risk_level as any) || 'Medium'} />
                </div>
              </div>

              {/* Items */}
              <div className="space-y-3">
                {checklist.map((item, idx) => {
                  const Icon = CHECKLIST_ICONS[item.risk_type] || Building;
                  return (
                    <div
                      key={item.id || idx}
                      onClick={() => toggleCheckItem(item.id)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer select-none flex items-start gap-3.5 ${
                        item.verified
                          ? 'bg-emerald-500/5 border-emerald-500/30 text-slate-200'
                          : 'bg-surface-raised/40 border-border-subtle hover:border-slate-700 text-slate-300'
                      }`}
                    >
                      <button
                        type="button"
                        className="mt-0.5 text-slate-400 hover:text-white transition-colors shrink-0"
                      >
                        {item.verified ? (
                          <CheckSquare className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <Square className="w-5 h-5 text-slate-500" />
                        )}
                      </button>

                      <div className="flex-1 space-y-1">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-white flex items-center gap-2">
                            <Icon className="w-4 h-4 text-neon-cyan" />
                            {item.description}
                          </h4>
                          <span className="text-2xs font-mono text-slate-500 uppercase">
                            {item.risk_type}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed">
                          <strong className="text-slate-300">Recommended Action:</strong>{' '}
                          {item.recommended_action}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Candidate Notes */}
              <div className="space-y-2 pt-2 border-t border-border-subtle">
                <label className="text-xs font-medium text-slate-300 block">
                  Candidate Verification Notes & Due Diligence Logs:
                </label>
                <textarea
                  value={candidateNotes}
                  onChange={(e) => setCandidateNotes(e.target.value)}
                  placeholder="e.g. Cross-referenced recruiter's profile on LinkedIn. Interviewer had valid corporate email. Confirmed no upfront equipment purchase required."
                  rows={3}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-surface-raised border border-border-subtle text-white placeholder-slate-500 focus:outline-none focus:border-neon-cyan resize-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => updateMutation.mutate({ override: false })}
                  disabled={updateMutation.isPending}
                  className="w-full sm:w-auto px-4 py-2 text-xs font-medium rounded-xl bg-surface-border text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save Checklist Progress'}
                </button>

                <div className="flex items-center gap-2.5 w-full sm:w-auto">
                  <button
                    type="button"
                    onClick={() => quarantineMutation.mutate()}
                    disabled={quarantineMutation.isPending}
                    className="flex-1 sm:flex-initial px-4 py-2 text-xs font-medium rounded-xl bg-neon-coral/10 border border-neon-coral/30 text-neon-coral hover:bg-neon-coral/20 transition-colors flex items-center justify-center gap-1.5"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Quarantine as Scam
                  </button>

                  <button
                    type="button"
                    onClick={() => updateMutation.mutate({ override: true })}
                    disabled={updateMutation.isPending || !allVerified}
                    title={!allVerified ? 'All 4 verification checks must be completed before marking as trusted.' : ''}
                    className={`flex-1 sm:flex-initial px-4 py-2 text-xs font-semibold rounded-xl flex items-center justify-center gap-2 transition-all ${
                      allVerified
                        ? 'bg-emerald-500 hover:bg-emerald-600 text-black shadow-glow-cyan'
                        : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
                    }`}
                  >
                    <ShieldCheck className="w-4 h-4" />
                    Mark as Trusted (Override)
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Verification Rules & Policy Sidebar */}
          <div className="lg:col-span-1 space-y-4">
            <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-3">
              <h3 className="font-semibold text-white text-sm">Human-in-the-Loop Policy</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Autonomous agents must strictly comply with SafeApply Safety Principles:
              </p>
              <ul className="text-xs text-slate-400 space-y-2 list-disc list-inside">
                <li>Never auto-send replies or applications for unverified solicitations.</li>
                <li>All verification overrides are cryptographically logged with candidate notes.</li>
                <li>Marking an offer as trusted unlocks the autonomous Application Agent for this opportunity.</li>
              </ul>

              {checklistData?.user_override && (
                <div className="mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300">
                  <div className="font-semibold mb-1">Current Status: {checklistData.review_status}</div>
                  <div>Override Decision: {checklistData.user_override}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default Verification;
