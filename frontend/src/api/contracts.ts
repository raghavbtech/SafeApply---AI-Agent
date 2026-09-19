/**
 * SafeApply TypeScript API Contracts.
 * Strictly typed interfaces matching backend Pydantic models.
 */

export interface SessionPrincipal {
  session_id: string;
  created_at: string;
  is_new?: boolean;
  user_id?: string;
  email?: string;
  full_name?: string | null;
  role?: string;
}

export type UserPrincipal = SessionPrincipal;

export interface SessionStatusResponse {
  session_id: string;
  created_at: string;
  expires_at?: string | null;
  has_profile: boolean;
  has_resume: boolean;
  has_mailbox: boolean;
  storage_mode: string;
}

export interface DataPurgeResponse {
  success: boolean;
  message: string;
  purged_items: Record<string, number>;
}

export interface EmailListItem {
  id: string;
  message_id?: string | null;
  imap_uid?: string | null;
  sender: string;
  sender_name?: string | null;
  subject: string;
  date?: string | null;
  received_at?: string | null;
  company?: string | null;
  company_name?: string | null;
  role_title?: string | null;
  status: string; // unscanned | scanned | error | applied | verified | quarantined
  folder: string; // inbox | spam
  mailbox_action: string;
  user_decision: string;
  is_recruitment: boolean;
  risk_score?: number | null;
  risk_level?: 'Low' | 'Medium' | 'High' | 'Critical' | null;
  quarantined_at?: string | null;
  quarantine_reason?: string | null;
  quarantined_automatically?: boolean;
  applied_at?: string | null;
  synced_at?: string | null;
}

export interface EmailDetailResponse extends EmailListItem {
  body: string;
  analysis?: any;
  original_risk_score?: number | null;
  original_risk_level?: string | null;
  user_override?: string | null;
  application_package?: any;
  submission_id?: string | null;
}

export interface ToolOutputsResponse {
  rag_matches?: any[];
  domain_verification?: Record<string, any>;
  salary_sanity?: Record<string, any>;
  ml_classifier?: Record<string, any>;
}

export interface AnalysisResultResponse {
  analysis_id?: string | null;
  email_id?: string | null;
  risk_level: 'Low' | 'Medium' | 'High' | 'Critical';
  risk_score: number;
  explanation: string;
  identified_red_flags: string[];
  extracted_data: Record<string, any>;
  tool_outputs: ToolOutputsResponse;
  responsible_ai_disclaimer?: string | null;
  execution_mode?: string | null;
  scanned_at?: string | null;
  review_status?: string | null;
}

export interface VerificationChecklistItem {
  id: string;
  risk_type: string;
  description: string;
  recommended_action: string;
  verified: boolean;
}

export interface VerificationChecklistResponse {
  email_id: string;
  original_risk_score: number;
  original_risk_level: string;
  review_status: string;
  user_override?: string | null;
  checklist: VerificationChecklistItem[];
}

export interface JobSpecResponse {
  company_name: string;
  role_title: string;
  location: string;
  salary: string;
  required_skills: string[];
  portal_url: string;
  contact_email: string;
  is_no_reply: boolean;
}

export interface MatchEvaluationResponse {
  match_percentage: number;
  match_rating: string;
  match_badge_color: string;
  matched_skills: string[];
  missing_skills: string[];
  total_required: number;
  candidate_skills_count: number;
}

export interface ApplicationDraftResponse {
  email_id: string;
  job_spec: JobSpecResponse;
  match_evaluation: MatchEvaluationResponse;
  cover_letter: string;
  recruiter_reply: string;
  qa_talking_points: string;
  resume_filename?: string | null;
  target_email: string;
  is_no_reply: boolean;
}

export interface ApplicationRecordResponse {
  submission_id: string;
  email_id: string;
  company_name: string;
  role_title: string;
  applied_at: string;
  candidate_name: string;
  candidate_email: string;
  portal_url: string;
  recruiter_email: string;
  cover_letter_snippet: string;
  recruiter_reply?: string | null;
  is_no_reply: boolean;
  dispatch_status: string;
  dispatch_notice?: string | null;
  status: string;
  resume_filename?: string | null;
}

export interface CandidateProfileSchema {
  full_name: string;
  email: string;
  phone?: string;
  education?: string;
  university?: string;
  gpa?: string;
  skills: string[];
  experience?: string;
  preferred_roles: string[];
  target_locations: string[];
  portfolio_url?: string;
  linkedin_url?: string;
  resume_path?: string;
  resume_filename?: string;
  is_complete: boolean;
}

export interface UserPreferencesSchema {
  auto_quarantine_enabled: boolean;
  auto_quarantine_threshold: number;
  auto_apply_enabled: boolean;
  auto_apply_max_risk_score: number;
  enable_real_smtp_dispatch: boolean;
}

export interface AuditRecordSchema {
  id: string;
  sequence: number;
  action: string;
  email_doc_id?: string | null;
  timestamp: string;
  details: Record<string, any>;
  prev_hash: string;
  record_hash: string;
}

export interface AuditChainStatusResponse {
  valid: boolean;
  records: number;
  broken_at?: number | null;
  reason?: string | null;
}

export interface MailboxConnectionStatus {
  provider: string;
  username: string;
  is_connected: boolean;
  status: string;
  imap_server?: string | null;
  imap_port?: number | null;
  last_sync?: string | null;
  stored_count?: number;
}

export interface DashboardStatsResponse {
  stats: {
    total: number;
    inbox: number;
    spam: number;
    unscanned: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    applied: number;
    ignored: number;
  };
  connection: MailboxConnectionStatus;
  service_health: Record<string, any>;
  storage_backend: string;
  audit_chain: AuditChainStatusResponse;
  total_applications: number;
  timestamp: string;
}

export interface PaginatedList<T> {
  items: T[];
  meta: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}
