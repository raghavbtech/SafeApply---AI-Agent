import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { 
  EmailListItem, 
  ApplicationDraftResponse, 
  ApplicationRecordResponse 
} from '../api/contracts';
import { Loading } from '../components/Loading';
import { EmptyState } from '../components/EmptyState';
import { StatusBanner } from '../components/StatusBanner';
import {
  Briefcase,
  Sparkles,
  Send,
  Building,
  MapPin,
  DollarSign,
  FileText,
  MessageSquare,
  CheckCircle2,
  AlertCircle,
  Clock,
  ExternalLink,
  ShieldCheck,
  Info,
  Check
} from 'lucide-react';

export const JobAgent: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const emailIdParam = searchParams.get('email_id');

  const [selectedEmailId, setSelectedEmailId] = useState<string>(emailIdParam || '');
  const [activeTab, setActiveTab] = useState<'cover_letter' | 'recruiter_reply' | 'talking_points'>('cover_letter');

  // Draft state for user edits
  const [editableCoverLetter, setEditableCoverLetter] = useState<string>('');
  const [editableRecruiterReply, setEditableRecruiterReply] = useState<string>('');
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState<boolean>(false);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);
  const [lastDispatchedRecord, setLastDispatchedRecord] = useState<ApplicationRecordResponse | null>(null);

  // Fetch safe or verified recruitment emails
  const { data: emailListResponse, isLoading: isListLoading } = useQuery({
    queryKey: ['safe-recruitment-emails'],
    queryFn: () => api.listEmails({ folder: 'inbox', limit: 50 }),
  });

  // Filter for emails that are recruitment and safe (Low risk or verified)
  const candidateEmails: EmailListItem[] = (emailListResponse?.items || []).filter(
    (e) => e.is_recruitment && (e.risk_level === 'Low' || e.user_decision === 'trusted_override' || !e.risk_level)
  );

  // Auto-select email if none selected yet
  useEffect(() => {
    if (emailIdParam) {
      setSelectedEmailId(emailIdParam);
    } else if (candidateEmails.length > 0 && !selectedEmailId) {
      setSelectedEmailId(candidateEmails[0].id);
    }
  }, [emailIdParam, candidateEmails, selectedEmailId]);

  // Fetch preview for selected email
  const { 
    data: previewData, 
    isLoading: isPreviewLoading 
  } = useQuery({
    queryKey: ['job-preview', selectedEmailId],
    queryFn: () => api.previewJob(selectedEmailId),
    enabled: !!selectedEmailId,
  });

  // Generate draft mutation
  const draftMutation = useMutation<ApplicationDraftResponse>({
    mutationFn: () => api.generateDraft(selectedEmailId),
    onSuccess: (data) => {
      setEditableCoverLetter(data.cover_letter);
      setEditableRecruiterReply(data.recruiter_reply);
      setBannerMsg({
        type: 'success',
        text: 'Tailored application package generated based on your candidate profile and skills match!'
      });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Failed to generate application package: ${err.message || 'Unknown error'}`
      });
    }
  });

  // Send approved application mutation
  const sendMutation = useMutation<ApplicationRecordResponse>({
    mutationFn: () =>
      api.sendApprovedApplication(selectedEmailId, editableCoverLetter, editableRecruiterReply),
    onSuccess: (record) => {
      setIsConfirmModalOpen(false);
      setLastDispatchedRecord(record);
      setBannerMsg({
        type: 'success',
        text: `Application successfully submitted! Submission ID: ${record.submission_id}`
      });
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setIsConfirmModalOpen(false);
      setBannerMsg({
        type: 'error',
        text: `Application dispatch failed: ${err.message || 'Unknown error'}`
      });
    }
  });

  const jobSpec = previewData?.job_spec;
  const matchEval = previewData?.match;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Briefcase className="w-6 h-6 text-neon-cyan" />
            Autonomous Job Agent
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Evaluate skill match, generate tailored materials, and approve secure application dispatch with human-in-the-loop oversight.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/applications"
            className="px-3 py-1.5 rounded-lg bg-surface-raised border border-border-subtle text-xs text-slate-300 hover:text-white flex items-center gap-1.5"
          >
            <Clock className="w-3.5 h-3.5 text-neon-cyan" />
            Application Tracker
          </Link>
        </div>
      </div>

      {bannerMsg && (
        <StatusBanner 
          type={bannerMsg.type} 
          message={bannerMsg.text} 
          onDismiss={() => setBannerMsg(null)} 
        />
      )}

      {/* Safety Policy Banner */}
      <div className="p-4 rounded-xl bg-neon-cyan/5 border border-neon-cyan/20 flex items-start gap-3 text-xs text-slate-300">
        <ShieldCheck className="w-4 h-4 text-neon-cyan shrink-0 mt-0.5" />
        <div>
          <strong className="text-neon-cyan font-medium">SafeApply Human Oversight Protocol:</strong>{' '}
          The Job Agent will never automatically dispatch applications or contact recruiters without your explicit review and sign-off. Review and modify the tailored draft before final submission.
        </div>
      </div>

      {/* Email Selector */}
      <div className="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="text-xs text-slate-300 font-medium">
          Select Verified Opportunity:
        </div>
        <div className="flex-1 max-w-md">
          {isListLoading ? (
            <span className="text-xs text-slate-500">Loading opportunities...</span>
          ) : candidateEmails.length === 0 && !selectedEmailId ? (
            <span className="text-xs text-slate-500">No verified recruitment solicitations found in Inbox.</span>
          ) : (
            <select
              value={selectedEmailId}
              onChange={(e) => {
                setSelectedEmailId(e.target.value);
                setSearchParams({ email_id: e.target.value });
                setEditableCoverLetter('');
                setEditableRecruiterReply('');
                setLastDispatchedRecord(null);
              }}
              className="w-full px-3 py-2 text-xs rounded-lg bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
            >
              {candidateEmails.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.company ? `[${e.company}] ` : ''}{e.subject || '(No Subject)'}
                </option>
              ))}
              {selectedEmailId && !candidateEmails.some((e) => e.id === selectedEmailId) && (
                <option value={selectedEmailId}>Opportunity ID: {selectedEmailId}</option>
              )}
            </select>
          )}
        </div>
      </div>

      {!selectedEmailId ? (
        <EmptyState
          icon={Briefcase}
          title="No Opportunity Selected"
          description="Select a verified job solicitation to view requirements and generate tailored application materials."
        />
      ) : isPreviewLoading ? (
        <Loading message="Extracting job specifications and evaluating skill match..." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Job Spec & Match Breakdown */}
          <div className="lg:col-span-1 space-y-4">
            {/* Job Details Card */}
            <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
              <div className="border-b border-border-subtle pb-3">
                <span className="text-2xs font-mono text-neon-cyan uppercase tracking-wider">Opportunity Profile</span>
                <h2 className="text-lg font-bold text-white mt-1">
                  {jobSpec?.role_title || 'Software Opportunity'}
                </h2>
                <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-1">
                  <Building className="w-3.5 h-3.5 text-slate-500" />
                  <span className="text-slate-200 font-medium">{jobSpec?.company_name || 'Confidential'}</span>
                </div>
              </div>

              <div className="space-y-2 text-xs text-slate-300">
                <div className="flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-slate-500" />
                  <span>{jobSpec?.location || 'Remote / Unspecified'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <DollarSign className="w-3.5 h-3.5 text-slate-500" />
                  <span>{jobSpec?.salary || 'Market Rate / Competitive'}</span>
                </div>
                {jobSpec?.is_no_reply && (
                  <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-2xs">
                    ⚠️ Automated No-Reply sender detected. Application will be routed via company portal URL.
                  </div>
                )}
              </div>

              {/* Match Evaluation Pill */}
              <div className="pt-3 border-t border-border-subtle space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Profile Skill Match</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    (matchEval?.match_percentage ?? 0) >= 70
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                  }`}>
                    {matchEval?.match_percentage ?? 0}% {matchEval?.match_rating || 'Evaluated'}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full h-1.5 bg-surface-raised rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-neon-cyan to-neon-violet transition-all duration-500"
                    style={{ width: `${matchEval?.match_percentage || 0}%` }}
                  />
                </div>

                {/* Skills tags */}
                {matchEval?.matched_skills && matchEval.matched_skills.length > 0 && (
                  <div className="pt-2">
                    <span className="text-2xs text-slate-400 block mb-1">Matched Skills:</span>
                    <div className="flex flex-wrap gap-1">
                      {matchEval.matched_skills.map((skill: string, i: number) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-2xs">
                          ✓ {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {matchEval?.missing_skills && matchEval.missing_skills.length > 0 && (
                  <div className="pt-1">
                    <span className="text-2xs text-slate-400 block mb-1">Missing / Unlisted:</span>
                    <div className="flex flex-wrap gap-1">
                      {matchEval.missing_skills.map((skill: string, i: number) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-surface-raised text-slate-400 border border-border-subtle text-2xs">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Generate Trigger Button */}
            <button
              onClick={() => draftMutation.mutate()}
              disabled={draftMutation.isPending}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-neon-cyan/20 to-neon-violet/20 hover:from-neon-cyan/30 hover:to-neon-violet/30 border border-neon-cyan/40 text-neon-cyan font-semibold text-xs tracking-wide transition-all shadow-glow-cyan flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4 text-neon-cyan" />
              {draftMutation.isPending ? 'Generating Tailored Package...' : 'Generate Application Package'}
            </button>
          </div>

          {/* Right Column: Application Package Editor & Approval */}
          <div className="lg:col-span-2 space-y-4">
            <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
              {/* Navigation Tabs */}
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('cover_letter')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                      activeTab === 'cover_letter'
                        ? 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    Cover Letter
                  </button>
                  <button
                    onClick={() => setActiveTab('recruiter_reply')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                      activeTab === 'recruiter_reply'
                        ? 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    Recruiter Reply
                  </button>
                  <button
                    onClick={() => setActiveTab('talking_points')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                      activeTab === 'talking_points'
                        ? 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Interview Prep
                  </button>
                </div>

                {editableCoverLetter && (
                  <span className="text-2xs text-slate-500 font-mono">
                    Editable Draft
                  </span>
                )}
              </div>

              {/* Tab Contents */}
              {!editableCoverLetter && !draftMutation.data ? (
                <div className="py-16 text-center text-slate-400 text-xs">
                  <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  Click "Generate Application Package" on the left to create a customized cover letter and interview strategy.
                </div>
              ) : (
                <div className="space-y-4">
                  {activeTab === 'cover_letter' && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-2xs text-slate-400">
                        <span>Personalize your tailored cover letter:</span>
                        <span>{editableCoverLetter.length} characters</span>
                      </div>
                      <textarea
                        value={editableCoverLetter}
                        onChange={(e) => setEditableCoverLetter(e.target.value)}
                        rows={14}
                        className="w-full p-3.5 rounded-xl bg-surface-raised border border-border-subtle text-xs text-slate-200 font-sans leading-relaxed focus:outline-none focus:border-neon-cyan resize-none"
                      />
                    </div>
                  )}

                  {activeTab === 'recruiter_reply' && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-2xs text-slate-400">
                        <span>Candidate email reply draft:</span>
                        <span>{editableRecruiterReply.length} characters</span>
                      </div>
                      <textarea
                        value={editableRecruiterReply}
                        onChange={(e) => setEditableRecruiterReply(e.target.value)}
                        rows={10}
                        className="w-full p-3.5 rounded-xl bg-surface-raised border border-border-subtle text-xs text-slate-200 font-sans leading-relaxed focus:outline-none focus:border-neon-cyan resize-none"
                      />
                    </div>
                  )}

                  {activeTab === 'talking_points' && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold text-white">Suggested Q&A Talking Points:</h4>
                      <pre className="p-3.5 rounded-xl bg-surface-raised border border-border-subtle text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">
                        {draftMutation.data?.qa_talking_points || 'No talking points generated.'}
                      </pre>
                    </div>
                  )}

                  {/* Dispatch Controls */}
                  <div className="pt-4 border-t border-border-subtle flex flex-col sm:flex-row items-center justify-between gap-3">
                    <span className="text-2xs text-slate-400">
                      Destination: {jobSpec?.contact_email || 'Careers Portal'}
                    </span>

                    <button
                      onClick={() => setIsConfirmModalOpen(true)}
                      disabled={!editableCoverLetter.trim()}
                      className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-black font-semibold text-xs tracking-wide transition-all shadow-glow-cyan flex items-center justify-center gap-2"
                    >
                      <Send className="w-3.5 h-3.5" />
                      Approve & Dispatch Application
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Last Dispatched Record Preview */}
            {lastDispatchedRecord && (
              <div className="p-4 rounded-xl bg-surface-card border border-emerald-500/30 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Application Successfully Dispatched
                  </span>
                  <span className="font-mono text-2xs text-slate-400">
                    ID: {lastDispatchedRecord.submission_id}
                  </span>
                </div>
                <div className="text-slate-300">
                  {lastDispatchedRecord.dispatch_notice}
                </div>
                <div className="flex items-center gap-3 pt-1 text-2xs text-slate-400">
                  <span>Status: <strong className="text-white">{lastDispatchedRecord.status}</strong></span>
                  <span>Dispatch: <strong className="text-white">{lastDispatchedRecord.dispatch_status}</strong></span>
                  <Link to="/applications" className="text-neon-cyan hover:underline flex items-center gap-1">
                    View in Application Tracker <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {isConfirmModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-surface-card border border-border-subtle p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                <Send className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Confirm Application Dispatch</h3>
                <p className="text-xs text-slate-400">
                  Review the target endpoint and submission parameters.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface-raised border border-border-subtle text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Role:</span>
                <span className="text-white font-medium">{jobSpec?.role_title}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Company:</span>
                <span className="text-white font-medium">{jobSpec?.company_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Recipient:</span>
                <span className="text-slate-200 font-mono">{jobSpec?.contact_email || 'Portal Endpoint'}</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200">
              <strong>Simulated vs Live SMTP Dispatch:</strong> SafeApply enforces safe dispatch defaults. If live SMTP dispatch is disabled in your configuration, this action will record the submission and simulate portal delivery.
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsConfirmModalOpen(false)}
                className="px-4 py-2 text-xs font-medium rounded-xl bg-surface-raised border border-border-subtle text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => sendMutation.mutate()}
                disabled={sendMutation.isPending}
                className="px-5 py-2 text-xs font-semibold rounded-xl bg-emerald-500 hover:bg-emerald-600 text-black flex items-center gap-2"
              >
                <Check className="w-4 h-4" />
                {sendMutation.isPending ? 'Submitting...' : 'Confirm & Send'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default JobAgent;
