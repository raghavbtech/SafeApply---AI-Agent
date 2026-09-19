import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { AuditRecordSchema, AuditChainStatusResponse } from '../api/contracts';
import { Loading } from '../components/Loading';
import { EmptyState } from '../components/EmptyState';
import { StatusBanner } from '../components/StatusBanner';
import {
  FileCode,
  ShieldCheck,
  ShieldAlert,
  Link as LinkIcon,
  RefreshCw,
  Hash,
  Clock,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Database,
  Lock
} from 'lucide-react';

export const Audit: React.FC = () => {
  const queryClient = useQueryClient();
  const [expandedSeq, setExpandedSeq] = useState<number | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  // Fetch Audit Trail
  const { data: auditRecords = [], isLoading: isRecordsLoading } = useQuery<AuditRecordSchema[]>({
    queryKey: ['audit-trail'],
    queryFn: () => api.getAuditTrail(),
  });

  // Fetch / Verify Hash Chain
  const { 
    data: chainStatus, 
    isLoading: isChainLoading, 
    refetch: refetchVerification,
    isRefetching: isVerifying 
  } = useQuery<AuditChainStatusResponse>({
    queryKey: ['audit-verify'],
    queryFn: () => api.verifyAuditChain(),
  });

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleVerifyChain = async () => {
    const res = await refetchVerification();
    if (res.data?.valid) {
      setBannerMsg({
        type: 'success',
        text: `Cryptographic SHA-256 verification passed: All ${res.data.records} chained blocks are mathematically tamper-evident.`
      });
    } else {
      setBannerMsg({
        type: 'error',
        text: `Chain verification failed! Broken block detected at sequence #${res.data?.broken_at}: ${res.data?.reason || 'Hash mismatch'}`
      });
    }
  };

  const isChainValid = chainStatus?.valid;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Hash className="w-6 h-6 text-neon-cyan" />
            Cryptographic Audit Ledger
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Immutable SHA-256 linked chain logging every scan, quarantine, human override, and application dispatch.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleVerifyChain}
            disabled={isVerifying}
            className="px-4 py-2 rounded-xl bg-neon-cyan/10 border border-neon-cyan/30 text-xs font-semibold text-neon-cyan hover:bg-neon-cyan/20 transition-all shadow-glow-cyan flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
            {isVerifying ? 'Re-Verifying Chain...' : 'Verify Cryptographic Integrity'}
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

      {/* Cryptographic Chain Integrity Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-border-subtle relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-neon-cyan/5 rounded-full blur-3xl -z-10 pointer-events-none" />

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-center">
          <div className="md:col-span-2 space-y-2">
            <div className="flex items-center gap-2.5">
              {isChainLoading ? (
                <div className="w-6 h-6 rounded-full border-2 border-neon-cyan border-t-transparent animate-spin" />
              ) : isChainValid ? (
                <span className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  <ShieldCheck className="w-6 h-6" />
                </span>
              ) : (
                <span className="p-2 rounded-xl bg-neon-coral/10 border border-neon-coral/30 text-neon-coral">
                  <ShieldAlert className="w-6 h-6" />
                </span>
              )}
              <div>
                <h3 className="text-lg font-bold text-white">
                  {isChainValid ? 'Tamper-Evident Chain Intact' : 'Integrity Anomaly Detected'}
                </h3>
                <p className="text-xs text-slate-400">
                  {isChainValid
                    ? '100% cryptographic SHA-256 parent-child hash verification verified.'
                    : `Discrepancy at block #${chainStatus?.broken_at}: ${chainStatus?.reason}`}
                </p>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-surface-raised border border-border-subtle text-xs">
            <span className="text-slate-400 block text-2xs uppercase tracking-wider">Indexed Blocks</span>
            <span className="text-xl font-bold font-mono text-white">
              {chainStatus?.records ?? auditRecords.length}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-surface-raised border border-border-subtle text-xs">
            <span className="text-slate-400 block text-2xs uppercase tracking-wider">Genesis Block Algorithm</span>
            <span className="text-base font-semibold font-mono text-neon-cyan">
              SHA-256 HMAC
            </span>
          </div>
        </div>
      </div>

      {/* Ledger Table */}
      {isRecordsLoading ? (
        <Loading message="Fetching cryptographic ledger blocks..." />
      ) : auditRecords.length === 0 ? (
        <EmptyState
          icon={FileCode}
          title="Audit Ledger is Empty"
          description="Security operations, scans, and candidate actions will be permanently recorded here in the cryptographic chain."
        />
      ) : (
        <div className="space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
            Chronological Ledger Sequence ({auditRecords.length} Events)
          </div>

          <div className="space-y-2">
            {auditRecords.map((record) => {
              const isExpanded = expandedSeq === record.sequence;

              return (
                <div
                  key={record.id || record.sequence}
                  className="rounded-xl bg-surface-card border border-border-subtle hover:border-slate-700 transition-all overflow-hidden"
                >
                  <div
                    onClick={() => setExpandedSeq(isExpanded ? null : record.sequence)}
                    className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="px-2 py-0.5 rounded bg-surface-raised border border-border-subtle text-2xs font-mono font-bold text-neon-cyan">
                        #{record.sequence.toString().padStart(4, '0')}
                      </span>

                      <span className="text-xs font-semibold text-white font-mono">
                        {record.action}
                      </span>

                      {record.email_doc_id && (
                        <span className="text-2xs text-slate-400 font-mono">
                          target: {record.email_doc_id.slice(0, 12)}...
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-4 text-xs font-mono">
                      <span className="text-slate-400 text-2xs flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {new Date(record.timestamp).toLocaleString()}
                      </span>

                      <div className="flex items-center gap-1.5 text-2xs text-slate-400">
                        <span className="text-slate-500">hash:</span>
                        <span className="text-neon-violet">{record.record_hash?.slice(0, 8)}...</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCopy(record.record_hash);
                          }}
                          className="hover:text-white transition-colors"
                        >
                          {copiedHash === record.record_hash ? (
                            <Check className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <Copy className="w-3 h-3 text-slate-500" />
                          )}
                        </button>
                      </div>

                      <button
                        type="button"
                        className="p-1 text-slate-400 hover:text-white"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Block Inspector */}
                  {isExpanded && (
                    <div className="border-t border-border-subtle p-4 bg-surface-raised/20 space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-2xs font-mono">
                        <div className="p-2.5 rounded-lg bg-surface-raised border border-border-subtle break-all">
                          <span className="text-slate-500 block mb-1">Previous Block Hash (Parent):</span>
                          <span className="text-slate-300">{record.prev_hash || '0'.repeat(64)}</span>
                        </div>
                        <div className="p-2.5 rounded-lg bg-surface-raised border border-border-subtle break-all">
                          <span className="text-slate-500 block mb-1">Current Block Hash (Self):</span>
                          <span className="text-neon-cyan">{record.record_hash}</span>
                        </div>
                      </div>

                      <div>
                        <span className="text-2xs text-slate-400 font-medium block mb-1">
                          Block Payload Data (Immutable Audit Record):
                        </span>
                        <pre className="p-3 rounded-lg bg-surface-raised border border-border-subtle text-2xs text-slate-300 font-mono max-h-48 overflow-y-auto whitespace-pre-wrap">
                          {JSON.stringify(record.details || {}, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
export default Audit;
