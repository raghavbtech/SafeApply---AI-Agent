import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import {
  EmailListItem,
  ApplicationDraftResponse,
  ApplicationRecordResponse,
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
  ChevronDown,
  ChevronUp,
  Info,
  Check,
  History,
  User,
  ShieldCheck,
} from 'lucide-react';
import clsx from 'clsx';

export const Applications: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const tabParam = searchParams.get('tab') as 'opportunities' | 'prepare' | 'history' | null;
  const emailIdParam = searchParams.get('email_id');

  const [activeTab, setActiveTab] = useState<'opportunities' | 'prepare' | 'history'>(
    tabParam === 'opportunities' || tabParam === 'prepare' || tabParam === 'history'
      ? tabParam
      : emailIdParam
      ? 'prepare'
      : 'opportunities'
  );

  const [selectedEmailId, setSelectedEmailId] = useState<string>(emailIdParam || '');
  const [draftSubTab, setDraftSubTab] = useState<'cover_letter' | 'recruiter_reply' | 'talking_points'>('cover_letter');

  // Draft state for candidate edits
  const [editableCoverLetter, setEditableCoverLetter] = useState<string>('');
  const [editableRecruiterReply, setEditableRecruiterReply] = useState<string>('');
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState<boolean>(false);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);
  const [expandedAppId, setExpandedAppId] = useState<string | null>(null);

  // Sync tab with URL
  useEffect(() => {
    if (tabParam && ['opportunities', 'prepare', 'history'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  // Fetch Safe/Verified recruitment emails for application
  const { data: emailListResponse, isLoading: isEmailsLoading } = useQuery({
    queryKey: ['safe-recruitment-emails'],
    queryFn: () => api.listEmails({ folder: 'inbox', limit: 50 }),
  });

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

  // Fetch Candidate Profile to check completeness
  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
  });

  // Fetch Job Spec & Match Preview for selected email
  const { data: previewData, isLoading: isPreviewLoading } = useQuery({
    queryKey: ['job-preview', selectedEmailId],
    queryFn: () => api.previewJob(selectedEmailId),
    enabled: !!selectedEmailId && (activeTab === 'opportunities' || activeTab === 'prepare'),
  });

  // Fetch Submitted Applications (History)
  const { data: applications = [], isLoading: isHistoryLoading } = useQuery<ApplicationRecordResponse[]>({
    queryKey: ['applications'],
    queryFn: () => api.listApplications(),
    refetchInterval: 15000,
  });

  // Draft Generation Mutation
  const draftMutation = useMutation<ApplicationDraftResponse>({
    mutationFn: () => api.generateDraft(selectedEmailId),
    onSuccess: (data) => {
      setEditableCoverLetter(data.cover_letter);
      setEditableRecruiterReply(data.recruiter_reply);
      setBannerMsg({
        type: 'success',
        text: 'Tailored application package generated based on your profile and match analysis!'
      });
      setActiveTab('prepare');
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Failed to generate draft: ${err.message || 'Unknown error'}`
      });
    }
  });

  // Send / Submit Application Mutation
  const sendMutation = useMutation({
    mutationFn: () =>
      api.sendApprovedApplication(selectedEmailId, editableCoverLetter, editableRecruiterReply),
    onSuccess: (record) => {
      setIsConfirmModalOpen(false);
      setBannerMsg({
        type: 'success',
        text: `Application ${record.submission_id} submitted! Status: ${record.status}. View in History tab.`
      });
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      setActiveTab('history');
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Application submission failed: ${err.message || 'Unknown error'}`
      });
    }
  });

  const switchTab = (tab: 'opportunities' | 'prepare' | 'history') => {
    setActiveTab(tab);
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      p.set('tab', tab);
      return p;
    });
  };

  const isProfileReady = !!(profile?.full_name && profile?.email);

  return (
    <div className="space-y-5">
      {/* Top Header & Internal Tab Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-neon-cyan" />
            Job Applications
          </h1>
          <p className="text-xs text-slate-400">
            Evaluate skill match against verified offers, generate tailored application materials, and track submissions.
          </p>
        </div>

        {/* 3 Internal Tabs */}
        <div className="flex rounded-xl bg-dark-900 border border-slate-800 p-1 text-xs">
          <button
            onClick={() => switchTab('opportunities')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition',
              activeTab === 'opportunities'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-neon-cyan'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Opportunities ({candidateEmails.length})
          </button>
          <button
            onClick={() => switchTab('prepare')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition',
              activeTab === 'prepare'
                ? 'bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-neon-violet'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            <FileText className="w-3.5 h-3.5" />
            Prepare Application
          </button>
          <button
            onClick={() => switchTab('history')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition',
              activeTab === 'history'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-neon-emerald'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            <History className="w-3.5 h-3.5" />
            History ({applications.length})
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

      {/* Candidate Profile Missing Banner */}
      {!isProfileReady && activeTab !== 'history' && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between text-xs text-amber-300">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
            <span>
              Your candidate profile is incomplete. Add your name, skills, and resume in <b>My Profile</b> for AI skill matching and application tailoring.
            </span>
          </div>
          <Link
            to="/profile"
            className="px-3 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 font-semibold text-2xs text-amber-200 transition shrink-0"
          >
            Update Profile
          </Link>
        </div>
      )}

      {/* TAB 1: OPPORTUNITIES */}
      {activeTab === 'opportunities' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Opportunities List */}
          <div className="lg:col-span-1 space-y-2">
            <span className="text-xs font-bold text-slate-300 block mb-1">
              Verified Opportunities ({candidateEmails.length})
            </span>
            {isEmailsLoading ? (
              <Loading message="Scanning mailbox for safe opportunities..." />
            ) : candidateEmails.length === 0 ? (
              <EmptyState
                icon={Briefcase}
                title="No Opportunities Ready"
                description="SafeApply automatically filters low-risk and verified offers from your mailbox. Sync mailbox or scan offers to see opportunities here."
              />
            ) : (
              candidateEmails.map((item) => {
                const isSelected = selectedEmailId === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => {
                      setSelectedEmailId(item.id);
                      setSearchParams({ email_id: item.id, tab: 'opportunities' });
                    }}
                    className={clsx(
                      'p-3.5 rounded-xl border text-xs cursor-pointer transition',
                      isSelected
                        ? 'bg-cyan-500/10 border-cyan-500/50 shadow-neon-cyan'
                        : 'bg-surface-card border-border-subtle hover:border-slate-700'
                    )}
                  >
                    <div className="flex items-center justify-between text-2xs text-slate-400 mb-1">
                      <span className="font-semibold text-slate-300">{item.company_name}</span>
                      <span>{item.date}</span>
                    </div>
                    <h4 className="font-bold text-white text-xs truncate">{item.subject}</h4>
                    <span className="text-2xs text-slate-400 block mt-1">{item.role_title}</span>
                  </div>
                );
              })
            )}
          </div>

          {/* Opportunity Match Preview Detail */}
          <div className="lg:col-span-2">
            {isPreviewLoading ? (
              <Loading message="Extracting requirements and evaluating match..." />
            ) : !previewData ? (
              <EmptyState
                icon={Sparkles}
                title="Select an Opportunity"
                description="Choose an offer on the left to evaluate skill overlap and generate tailored application drafts."
              />
            ) : (
              <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-5">
                {/* Header Card */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-border-subtle">
                  <div>
                    <h2 className="text-base font-bold text-white">
                      {previewData.job_spec?.role_title || 'Role'} @ {previewData.job_spec?.company_name || 'Company'}
                    </h2>
                    <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                        {previewData.job_spec?.location || 'Not specified'}
                      </span>
                      <span className="flex items-center gap-1">
                        <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
                        {previewData.job_spec?.salary || 'Not specified'}
                      </span>
                    </div>
                  </div>

                  {/* Match Rating Badge */}
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-lg font-bold text-cyan-400 font-mono">
                        {previewData.match_evaluation?.match_percentage || 0}%
                      </span>
                      <span className="text-2xs text-slate-400 block">Match Rating</span>
                    </div>
                    <button
                      onClick={() => draftMutation.mutate()}
                      disabled={draftMutation.isPending}
                      className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:opacity-95 text-xs font-bold text-white shadow-neon-cyan transition disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      {draftMutation.isPending ? 'Generating...' : 'Prepare Application'}
                    </button>
                  </div>
                </div>

                {/* Extracted Skills & Requirements */}
                <div className="space-y-3">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                    Skills Overlap & Match Breakdown
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-dark-850 border border-slate-800 space-y-1.5">
                      <span className="text-emerald-400 font-semibold flex items-center gap-1.5 text-2xs uppercase">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Matched Candidate Skills ({previewData.match_evaluation?.matched_skills?.length || 0})
                      </span>
                      <div className="flex flex-wrap gap-1 pt-1">
                        {previewData.match_evaluation?.matched_skills?.length > 0 ? (
                          previewData.match_evaluation.matched_skills.map((s: string) => (
                            <span key={s} className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-2xs">
                              {s}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-500 text-2xs italic">No matched skills detected</span>
                        )}
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-dark-850 border border-slate-800 space-y-1.5">
                      <span className="text-amber-400 font-semibold flex items-center gap-1.5 text-2xs uppercase">
                        <AlertCircle className="w-3.5 h-3.5" />
                        Missing Required Skills ({previewData.match_evaluation?.missing_skills?.length || 0})
                      </span>
                      <div className="flex flex-wrap gap-1 pt-1">
                        {previewData.match_evaluation?.missing_skills?.length > 0 ? (
                          previewData.match_evaluation.missing_skills.map((s: string) => (
                            <span key={s} className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-2xs">
                              {s}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-500 text-2xs italic">No critical missing skills</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Portal / Contact Notice */}
                <div className="p-3 rounded-xl bg-dark-850/60 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
                  <span>
                    Contact Channel: <b>{previewData.job_spec?.contact_email || 'Not specified'}</b>
                    {previewData.job_spec?.is_no_reply && (
                      <span className="ml-2 text-2xs font-mono text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">No-Reply Sender</span>
                    )}
                  </span>
                  {previewData.job_spec?.portal_url && previewData.job_spec.portal_url !== 'Not specified' && (
                    <a
                      href={previewData.job_spec.portal_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-2xs font-semibold"
                    >
                      Official Careers Portal <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: PREPARE APPLICATION */}
      {activeTab === 'prepare' && (
        <div className="space-y-5">
          {!previewData ? (
            <EmptyState
              icon={Briefcase}
              title="No Job Opportunity Selected"
              description="Please select an opportunity from the Opportunities tab first to generate and tailor application drafts."
              action={{
                label: 'View Opportunities',
                onClick: () => switchTab('opportunities'),
              }}
            />
          ) : (
            <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-5">
              {/* Draft Header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-border-subtle">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-neon-cyan" />
                    Application Package: {previewData.job_spec?.role_title} @ {previewData.job_spec?.company_name}
                  </h2>
                  <p className="text-xs text-slate-400">
                    Review and edit the tailored draft before granting explicit candidate approval for submission.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => draftMutation.mutate()}
                    disabled={draftMutation.isPending}
                    className="px-3 py-1.5 rounded-lg bg-dark-850 hover:bg-slate-800 text-xs font-medium text-slate-300 border border-slate-700 transition"
                  >
                    {draftMutation.isPending ? 'Regenerating...' : 'Regenerate Package'}
                  </button>

                  <button
                    onClick={() => setIsConfirmModalOpen(true)}
                    disabled={!editableCoverLetter}
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white shadow-neon-emerald transition disabled:opacity-50 flex items-center gap-1.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    Approve & Submit Application
                  </button>
                </div>
              </div>

              {/* Sub-Tabs: Cover Letter | Recruiter Reply | Talking Points */}
              <div className="flex gap-2 border-b border-border-subtle pb-2 text-xs">
                <button
                  onClick={() => setDraftSubTab('cover_letter')}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg font-semibold transition',
                    draftSubTab === 'cover_letter'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  )}
                >
                  Formal Cover Letter
                </button>
                <button
                  onClick={() => setDraftSubTab('recruiter_reply')}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg font-semibold transition',
                    draftSubTab === 'recruiter_reply'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  )}
                >
                  Candidate Recruiter Reply
                </button>
                <button
                  onClick={() => setDraftSubTab('talking_points')}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg font-semibold transition',
                    draftSubTab === 'talking_points'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  )}
                >
                  Interview Talking Points
                </button>
              </div>

              {/* Sub-Tab Editor Content */}
              {draftSubTab === 'cover_letter' && (
                <div className="space-y-2">
                  <label className="text-2xs font-semibold uppercase tracking-wider text-slate-400 block">
                    Tailored Cover Letter (Editable)
                  </label>
                  <textarea
                    rows={12}
                    value={editableCoverLetter}
                    onChange={(e) => setEditableCoverLetter(e.target.value)}
                    placeholder="Click 'Prepare Application' or 'Regenerate Package' to populate tailored cover letter..."
                    className="w-full p-3.5 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black font-sans text-xs leading-relaxed focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                  />
                </div>
              )}

              {draftSubTab === 'recruiter_reply' && (
                <div className="space-y-2">
                  <label className="text-2xs font-semibold uppercase tracking-wider text-slate-400 block">
                    Direct Email Reply to Hiring Team (Editable)
                  </label>
                  <textarea
                    rows={10}
                    value={editableRecruiterReply}
                    onChange={(e) => setEditableRecruiterReply(e.target.value)}
                    placeholder="Email reply written from you to the recruiter..."
                    className="w-full p-3.5 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black font-sans text-xs leading-relaxed focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                  />
                </div>
              )}

              {draftSubTab === 'talking_points' && (
                <div className="space-y-2">
                  <label className="text-2xs font-semibold uppercase tracking-wider text-slate-400 block">
                    Candidate Preparation Talking Points
                  </label>
                  <div className="p-4 rounded-xl bg-dark-850 border border-slate-800 text-xs text-slate-300 space-y-2 leading-relaxed">
                    <p><b>Target Role:</b> {previewData.job_spec?.role_title}</p>
                    <p><b>Key Match Strengths:</b> {previewData.match_evaluation?.matched_skills?.join(', ') || 'General engineering background'}</p>
                    <p><b>Recommended Focus:</b> Emphasize problem-solving, project portfolio, and system design fundamentals relevant to {previewData.job_spec?.company_name}.</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: APPLICATION HISTORY */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300">
              Submitted Applications Audit Trail ({applications.length})
            </span>
          </div>

          {isHistoryLoading ? (
            <Loading message="Loading application submission history..." />
          ) : applications.length === 0 ? (
            <EmptyState
              icon={History}
              title="No Applications Submitted Yet"
              description="Your submitted applications, tracking IDs, and dispatch logs will appear here once you approve submissions in Prepare Application."
              action={{
                label: 'View Opportunities',
                onClick: () => switchTab('opportunities'),
              }}
            />
          ) : (
            <div className="space-y-3">
              {applications.map((app) => {
                const isExpanded = expandedAppId === app.submission_id;
                return (
                  <div
                    key={app.submission_id}
                    className="rounded-2xl bg-surface-card border border-border-subtle overflow-hidden transition-all hover:border-slate-700"
                  >
                    {/* Summary Row */}
                    <div
                      onClick={() => setExpandedAppId(isExpanded ? null : app.submission_id)}
                      className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer select-none"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
                          <Building className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-white">{app.company_name}</span>
                            <span className="text-2xs font-mono text-slate-500">ID: {app.submission_id}</span>
                          </div>
                          <span className="text-xs text-slate-400">{app.role_title}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {/* Status Badge */}
                        <span
                          className={clsx(
                            'px-2.5 py-1 rounded-full text-2xs font-semibold border',
                            app.status.includes('Dispatched') || app.status.includes('Sent')
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : app.status.includes('Portal')
                              ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                              : 'bg-slate-800 text-slate-300 border-slate-700'
                          )}
                        >
                          {app.status}
                        </span>

                        <span className="text-2xs text-slate-500 font-mono flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : 'Recorded'}
                        </span>

                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                    </div>

                    {/* Expandable Detail View */}
                    {isExpanded && (
                      <div className="px-5 pb-5 pt-2 border-t border-border-subtle bg-dark-900/60 space-y-4 text-xs">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-1">
                            <span className="text-2xs font-bold text-slate-400 uppercase">Target Contact</span>
                            <p className="text-slate-300 font-mono">{app.recruiter_email || 'Portal Application'}</p>
                          </div>
                          <div className="space-y-1">
                            <span className="text-2xs font-bold text-slate-400 uppercase">Attached Resume</span>
                            <p className="text-slate-300">{app.resume_filename ? `Yes (${app.resume_filename})` : 'Profile Summary'}</p>
                          </div>
                        </div>

                        {app.cover_letter_snippet && (
                          <div className="space-y-1">
                            <span className="text-2xs font-bold text-slate-400 uppercase">Approved Cover Letter</span>
                            <pre className="p-3 rounded-xl bg-dark-950 font-sans text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                              {app.cover_letter_snippet}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* EXPLICIT APPROVAL CONFIRMATION MODAL */}
      {isConfirmModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-2xl bg-surface-card border border-border-subtle space-y-4 shadow-glass">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Confirm Application Submission</h3>
                <p className="text-2xs text-slate-400">Explicit human-in-the-loop authorization required</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              You are about to record and submit your application for <b>{previewData?.job_spec?.role_title}</b> at <b>{previewData?.job_spec?.company_name}</b>.
            </p>

            <div className="p-3 rounded-xl bg-dark-850 border border-slate-800 text-2xs text-slate-400 space-y-1">
              <p>• <b>Recipient:</b> {previewData?.job_spec?.contact_email || 'Portal'}</p>
              <p>• <b>Attached Resume:</b> {profile?.resume_filename || 'Candidate Resume'}</p>
              <p>• <b>Candidate:</b> {profile?.full_name || 'Anonymous Visitor'}</p>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsConfirmModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-dark-850 hover:bg-slate-800 text-xs font-semibold text-slate-300 border border-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => sendMutation.mutate()}
                disabled={sendMutation.isPending}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white shadow-neon-emerald transition flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                {sendMutation.isPending ? 'Submitting...' : 'Confirm & Dispatch'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
