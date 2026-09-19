import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { EmailListItem, EmailDetailResponse } from '../api/contracts';
import { RiskBadge } from '../components/RiskBadge';
import { Loading } from '../components/Loading';
import { EmptyState } from '../components/EmptyState';
import { StatusBanner } from '../components/StatusBanner';
import { 
  ShieldAlert, 
  RotateCcw, 
  AlertTriangle, 
  CheckCircle2, 
  FolderArchive,
  Info,
  Calendar,
  User,
  ExternalLink,
  Lock
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const Spam: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  const { data: emailListResponse, isLoading, error } = useQuery({
    queryKey: ['quarantine'],
    queryFn: () => api.listEmails({ folder: 'spam', limit: 100 }),
  });

  const emails: EmailListItem[] = emailListResponse?.items || [];

  const { data: selectedDetail, isLoading: isDetailLoading } = useQuery<EmailDetailResponse>({
    queryKey: ['emailDetail', selectedEmailId],
    queryFn: () => api.getEmail(selectedEmailId!),
    enabled: !!selectedEmailId,
  });

  const restoreMutation = useMutation({
    mutationFn: (emailId: string) => api.restoreFromSpam(emailId),
    onSuccess: (data, emailId) => {
      setBannerMsg({
        type: 'success',
        text: `Threat restored to inbox. ${data.mailbox_restored ? 'Restored on remote IMAP server.' : 'Restored in SafeApply local vault.'}`
      });
      queryClient.invalidateQueries({ queryKey: ['quarantine'] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      if (selectedEmailId === emailId) {
        setSelectedEmailId(null);
      }
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Failed to restore threat: ${err.message || 'Unknown error'}`
      });
    }
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <ShieldAlert className="w-6 h-6 text-neon-coral" />
            Threat Quarantine Vault
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Isolate and review malicious, phishing, or high-risk solicitations. Transparent IMAP vs local vault tracking ensures zero false claims.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1.5 rounded-lg bg-surface-raised border border-border-subtle text-xs text-slate-300 font-mono">
            {emails.length} {emails.length === 1 ? 'threat isolated' : 'threats isolated'}
          </span>
        </div>
      </div>

      {bannerMsg && (
        <StatusBanner 
          type={bannerMsg.type} 
          message={bannerMsg.text} 
          onDismiss={() => setBannerMsg(null)} 
        />
      )}

      {/* Info notice explaining IMAP vs Local quarantine */}
      <div className="p-4 rounded-xl bg-neon-coral/5 border border-neon-coral/20 flex items-start gap-3 text-xs text-slate-300">
        <Info className="w-4 h-4 text-neon-coral shrink-0 mt-0.5" />
        <div>
          <strong className="text-neon-coral font-medium">Mailbox Isolation Truthfulness:</strong>{' '}
          When a high-risk solicitation is quarantined, SafeApply attempts an IMAP move to your mailbox Spam folder. If remote IMAP credentials are not configured or the move is unconfirmed, SafeApply isolates it inside the local cryptographic vault. Restoring moves it back to your active candidate inbox.
        </div>
      </div>

      {isLoading ? (
        <Loading message="Scanning quarantine vault..." />
      ) : error ? (
        <EmptyState
          icon={AlertTriangle}
          title="Failed to load quarantine"
          description="Could not fetch quarantined messages from the secure vault."
        />
      ) : emails.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="Quarantine Vault is Empty"
          description="No threats currently isolated. SafeApply automatically intercepts dangerous phishing solicitations."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* List of quarantined items */}
          <div className="lg:col-span-2 space-y-3">
            {emails.map((item) => {
              const isSelected = selectedEmailId === item.id;
              // True if mailbox_action indicates an IMAP move occurred
              const hasImapMoved = item.mailbox_action === 'moved_to_spam';

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedEmailId(item.id)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-surface-raised border-neon-coral/60 shadow-glow-coral'
                      : 'bg-surface-card border-border-subtle hover:border-slate-700 hover:bg-surface-raised/40'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <RiskBadge level={item.risk_level || 'High'} />
                      <span className="text-xs text-slate-400 font-mono">ID: {item.id.slice(0, 10)}</span>
                    </div>

                    {/* IMAP vs Local Vault Indicator */}
                    {hasImapMoved ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-2xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        <CheckCircle2 className="w-3 h-3" />
                        IMAP [Spam] Moved
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-2xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                        <FolderArchive className="w-3 h-3" />
                        SafeApply Vault (Local)
                      </span>
                    )}
                  </div>

                  <h3 className="text-sm font-semibold text-white mb-1 line-clamp-1">
                    {item.subject || '(No Subject)'}
                  </h3>

                  <div className="flex items-center gap-4 text-xs text-slate-400 mb-2">
                    <span className="flex items-center gap-1 truncate max-w-[220px]">
                      <User className="w-3.5 h-3.5 text-slate-500" />
                      {item.sender}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      {item.received_at ? new Date(item.received_at).toLocaleDateString() : 'Unknown'}
                    </span>
                  </div>

                  {item.quarantine_reason && (
                    <p className="text-xs text-neon-coral/90 bg-neon-coral/10 p-2 rounded-lg border border-neon-coral/20 font-mono line-clamp-2">
                      Reason: {item.quarantine_reason}
                    </p>
                  )}

                  <div className="mt-3 pt-2 border-t border-border-subtle/50 flex items-center justify-between">
                    <span className="text-2xs text-slate-500">
                      {item.quarantined_automatically ? '⚡ Auto-Quarantined' : '👤 Quarantined by Candidate'}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        restoreMutation.mutate(item.id);
                      }}
                      disabled={restoreMutation.isPending}
                      className="px-2.5 py-1 text-xs font-medium rounded-lg bg-surface-border text-slate-200 hover:text-white hover:bg-slate-700 transition-colors flex items-center gap-1.5"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Restore
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Detailed Threat View */}
          <div className="lg:col-span-1">
            {selectedEmailId ? (
              isDetailLoading ? (
                <div className="p-6 rounded-2xl bg-surface-card border border-border-subtle">
                  <Loading message="Loading threat dossier..." />
                </div>
              ) : selectedDetail ? (
                <div className="sticky top-6 p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
                  <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                    <h3 className="font-semibold text-white text-sm">Threat Dossier</h3>
                    <RiskBadge level={selectedDetail.risk_level || 'High'} />
                  </div>

                  <div className="space-y-3 text-xs">
                    <div>
                      <label className="text-slate-400 block mb-1">Subject</label>
                      <div className="p-2.5 rounded-lg bg-surface-raised border border-border-subtle font-medium text-white break-words">
                        {selectedDetail.subject || '(No Subject)'}
                      </div>
                    </div>

                    <div>
                      <label className="text-slate-400 block mb-1">Sender</label>
                      <div className="p-2.5 rounded-lg bg-surface-raised border border-border-subtle font-mono text-slate-300 break-all">
                        {selectedDetail.sender}
                      </div>
                    </div>

                    <div>
                      <label className="text-slate-400 block mb-1">Quarantine State</label>
                      <div className="p-2.5 rounded-lg bg-surface-raised border border-border-subtle">
                        <div className="flex items-center gap-2 mb-1">
                          {selectedDetail.mailbox_action === 'moved_to_spam' ? (
                            <span className="text-emerald-400 font-semibold flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Remote IMAP Moved
                            </span>
                          ) : (
                            <span className="text-amber-400 font-semibold flex items-center gap-1">
                              <FolderArchive className="w-3.5 h-3.5" /> Local SafeApply Vault
                            </span>
                          )}
                        </div>
                        <p className="text-slate-400 text-2xs">
                          {selectedDetail.mailbox_action === 'moved_to_spam'
                            ? 'This message was physically relocated to the remote IMAP Spam folder.'
                            : 'Message isolated in local encrypted vault. Remote IMAP move was either not configured or bypassed.'}
                        </p>
                      </div>
                    </div>

                    {selectedDetail.analysis?.threat_summary && (
                      <div>
                        <label className="text-slate-400 block mb-1">Threat Analysis</label>
                        <div className="p-2.5 rounded-lg bg-neon-coral/10 border border-neon-coral/30 text-slate-200 leading-relaxed">
                          {selectedDetail.analysis.threat_summary}
                        </div>
                      </div>
                    )}

                    <div>
                      <label className="text-slate-400 block mb-1">Raw Message Snippet</label>
                      <pre className="p-2.5 rounded-lg bg-surface-raised border border-border-subtle font-mono text-2xs text-slate-300 overflow-x-auto max-h-36 whitespace-pre-wrap">
                        {selectedDetail.body?.slice(0, 500) || '(No Body Content)'}
                      </pre>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-border-subtle flex flex-col gap-2">
                    <button
                      onClick={() => restoreMutation.mutate(selectedDetail.id)}
                      disabled={restoreMutation.isPending}
                      className="w-full py-2 px-3 rounded-lg bg-surface-raised border border-border-subtle text-white font-medium text-xs hover:bg-slate-700 transition-colors flex items-center justify-center gap-2 shadow-sm"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      {restoreMutation.isPending ? 'Restoring...' : 'Restore to Active Inbox'}
                    </button>
                    <Link
                      to={`/analysis?email_id=${selectedDetail.id}`}
                      className="w-full py-2 px-3 rounded-lg bg-surface-border text-slate-300 font-medium text-xs hover:text-white hover:bg-slate-700 transition-colors flex items-center justify-center gap-2"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      View Full Analysis Dossier
                    </Link>
                  </div>
                </div>
              ) : null
            ) : (
              <div className="p-8 rounded-2xl bg-surface-card border border-border-subtle text-center text-slate-400 text-xs">
                <ShieldAlert className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                Select an isolated threat from the list to inspect the security dossier and quarantine status.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
export default Spam;
