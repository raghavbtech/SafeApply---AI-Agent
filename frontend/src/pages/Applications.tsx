import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { ApplicationRecordResponse } from '../api/contracts';
import { Loading } from '../components/Loading';
import { EmptyState } from '../components/EmptyState';
import {
  Send,
  Building,
  Calendar,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileText,
  Mail,
  CheckCircle2,
  Clock,
  Sparkles,
  Info
} from 'lucide-react';

export const Applications: React.FC = () => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: applications = [], isLoading, error } = useQuery<ApplicationRecordResponse[]>({
    queryKey: ['applications'],
    queryFn: () => api.listApplications(),
  });

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Send className="w-6 h-6 text-neon-cyan" />
            Application Dispatch Tracker
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time audit history of candidate-approved job applications, tracking IDs, and dispatch telemetry.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/jobs"
            className="px-4 py-2 rounded-xl bg-neon-cyan/10 border border-neon-cyan/30 text-xs font-semibold text-neon-cyan hover:bg-neon-cyan/20 transition-all shadow-glow-cyan flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            New Application
          </Link>
        </div>
      </div>

      {/* Info notice on dispatch truthfulness */}
      <div className="p-4 rounded-xl bg-surface-card border border-border-subtle flex items-start gap-3 text-xs text-slate-300">
        <Info className="w-4 h-4 text-neon-cyan shrink-0 mt-0.5" />
        <div>
          <strong className="text-neon-cyan font-medium">Telemetry Truthfulness:</strong>{' '}
          Each entry records the verified dispatch outcome. SafeApply explicitly distinguishes between live SMTP outbound mail vs local application sandbox records to guarantee zero false promises.
        </div>
      </div>

      {isLoading ? (
        <Loading message="Fetching application records and audit metadata..." />
      ) : error ? (
        <EmptyState
          icon={Send}
          title="Could Not Load Applications"
          description="Failed to load your submitted job application history."
        />
      ) : applications.length === 0 ? (
        <EmptyState
          icon={Send}
          title="No Applications Submitted Yet"
          description="Your verified opportunities will appear here once you approve and submit them via the Job Agent."
          action={{
            label: 'Open Job Agent',
            onClick: () => (window.location.href = '/jobs'),
          }}
        />
      ) : (
        <div className="space-y-4">
          {applications.map((app) => {
            const isExpanded = expandedId === app.submission_id;

            return (
              <div
                key={app.submission_id}
                className="rounded-2xl bg-surface-card border border-border-subtle overflow-hidden transition-all hover:border-slate-700"
              >
                {/* Header row */}
                <div
                  onClick={() => toggleExpand(app.submission_id)}
                  className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer select-none"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-mono text-2xs px-2 py-0.5 rounded bg-surface-raised border border-border-subtle text-slate-400">
                        {app.submission_id}
                      </span>
                      <span className="text-2xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        {app.status.toUpperCase()}
                      </span>
                      <span className="text-2xs font-mono text-slate-500">
                        {app.dispatch_status}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-white">
                      {app.role_title}
                    </h3>

                    <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
                      <span className="flex items-center gap-1.5 text-slate-300 font-medium">
                        <Building className="w-3.5 h-3.5 text-slate-500" />
                        {app.company_name}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {app.applied_at ? new Date(app.applied_at).toLocaleString() : 'N/A'}
                      </span>
                      {app.recruiter_email && (
                        <span className="flex items-center gap-1.5 text-slate-400">
                          <Mail className="w-3.5 h-3.5 text-slate-500" />
                          {app.recruiter_email}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    {app.portal_url && app.portal_url !== 'Not specified' && (
                      <a
                        href={app.portal_url.startsWith('http') ? app.portal_url : `https://${app.portal_url}`}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="px-3 py-1.5 rounded-lg bg-surface-raised border border-border-subtle text-xs text-slate-300 hover:text-white hover:bg-slate-700 transition-colors flex items-center gap-1.5"
                      >
                        Portal Link
                        <ExternalLink className="w-3 h-3 text-neon-cyan" />
                      </a>
                    )}

                    <button
                      type="button"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-raised transition-colors"
                    >
                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="border-t border-border-subtle p-5 bg-surface-raised/20 space-y-4">
                    {app.dispatch_notice && (
                      <div className="p-3 rounded-xl bg-neon-cyan/5 border border-neon-cyan/20 text-xs text-slate-300">
                        <strong className="text-neon-cyan font-medium">Dispatch Telemetry:</strong>{' '}
                        {app.dispatch_notice}
                      </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Cover Letter */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5 text-neon-cyan" />
                            Submitted Cover Letter Snippet
                          </span>
                        </div>
                        <pre className="p-3 rounded-xl bg-surface-raised border border-border-subtle font-mono text-2xs text-slate-300 whitespace-pre-wrap max-h-56 overflow-y-auto">
                          {app.cover_letter_snippet || '(None provided)'}
                        </pre>
                      </div>

                      {/* Recruiter Reply */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5 text-neon-violet" />
                            Approved Recruiter Reply Draft
                          </span>
                        </div>
                        <pre className="p-3 rounded-xl bg-surface-raised border border-border-subtle font-mono text-2xs text-slate-300 whitespace-pre-wrap max-h-56 overflow-y-auto">
                          {app.recruiter_reply || '(No direct recruiter reply attached)'}
                        </pre>
                      </div>
                    </div>

                    <div className="pt-2 flex items-center justify-between text-2xs text-slate-500 font-mono">
                      <span>Candidate: {app.candidate_name} ({app.candidate_email})</span>
                      {app.resume_filename && (
                        <span>Attached Resume: {app.resume_filename}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
export default Applications;
