/**
 * SafeApply API HTTP Client.
 */

import {
  AnalysisResultResponse,
  ApplicationDraftResponse,
  ApplicationRecordResponse,
  AuditChainStatusResponse,
  AuditRecordSchema,
  CandidateProfileSchema,
  DashboardStatsResponse,
  EmailDetailResponse,
  EmailListItem,
  PaginatedList,
  TokenResponse,
  UserPreferencesSchema,
  UserPrincipal,
  VerificationChecklistResponse,
  VerificationChecklistItem,
  MailboxConnectionStatus,
} from './contracts';

const API_BASE = '/api/v1';

class ApiClient {
  private getToken(): string | null {
    return localStorage.getItem('safeapply_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    const token = this.getToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      let errorMsg = 'An unexpected error occurred';
      try {
        const errorData = await response.json();
        errorMsg = errorData.error?.message || errorData.detail || errorMsg;
      } catch {
        errorMsg = `Server error (${response.status})`;
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  // Auth
  async login(email: string, password: string): Promise<TokenResponse> {
    const res = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('safeapply_token', res.access_token);
    return res;
  }

  async register(email: string, password: string, fullName: string): Promise<TokenResponse> {
    const res = await this.request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    localStorage.setItem('safeapply_token', res.access_token);
    return res;
  }

  async getMe(): Promise<UserPrincipal> {
    return this.request<UserPrincipal>('/auth/me');
  }

  logout(): void {
    localStorage.removeItem('safeapply_token');
    fetch(`${API_BASE}/auth/logout`, { method: 'POST' }).catch(() => {});
  }

  // Dashboard
  async getDashboard(): Promise<DashboardStatsResponse> {
    return this.request<DashboardStatsResponse>('/dashboard');
  }

  // Emails
  async listEmails(params: {
    folder?: string;
    status?: string;
    risk_level?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedList<EmailListItem>> {
    const query = new URLSearchParams();
    if (params.folder) query.set('folder', params.folder);
    if (params.status) query.set('status', params.status);
    if (params.risk_level) query.set('risk_level', params.risk_level);
    if (params.search) query.set('search', params.search);
    if (params.limit) query.set('limit', params.limit.toString());
    if (params.offset) query.set('offset', params.offset.toString());

    return this.request<PaginatedList<EmailListItem>>(`/emails?${query.toString()}`);
  }

  async getEmail(emailId: string): Promise<EmailDetailResponse> {
    return this.request<EmailDetailResponse>(`/emails/${emailId}`);
  }

  async importEml(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/emails/import-eml', {
      method: 'POST',
      body: formData,
    });
  }

  async batchScan(limit: number = 50): Promise<any> {
    return this.request(`/emails/batch-scan?limit=${limit}`, {
      method: 'POST',
    });
  }

  // Analysis
  async analyzeText(text: string, fastMode: boolean = false): Promise<AnalysisResultResponse> {
    return this.request<AnalysisResultResponse>('/analysis/text', {
      method: 'POST',
      body: JSON.stringify({ text, fast_mode: fastMode }),
    });
  }

  async analyzeStoredEmail(emailId: string, fastMode: boolean = false): Promise<AnalysisResultResponse> {
    return this.request<AnalysisResultResponse>(`/emails/${emailId}/analyze?fast_mode=${fastMode}`, {
      method: 'POST',
    });
  }

  async getStoredEmailAnalysis(emailId: string): Promise<AnalysisResultResponse> {
    return this.request<AnalysisResultResponse>(`/emails/${emailId}/analysis`);
  }

  // Mailbox Actions
  async getMailboxStatus(): Promise<MailboxConnectionStatus> {
    return this.request<MailboxConnectionStatus>('/mailboxes');
  }

  async syncMailbox(maxMessages: number = 15): Promise<any> {
    return this.request('/mailboxes/sync', {
      method: 'POST',
      body: JSON.stringify({ max_messages: maxMessages }),
    });
  }

  async moveToSpam(emailId: string, reason?: string): Promise<any> {
    return this.request(`/emails/${emailId}/spam`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || 'Manually quarantined by candidate' }),
    });
  }

  async restoreFromSpam(emailId: string): Promise<any> {
    return this.request(`/emails/${emailId}/restore`, {
      method: 'POST',
    });
  }

  // Verification
  async getVerificationChecklist(emailId: string): Promise<VerificationChecklistResponse> {
    return this.request<VerificationChecklistResponse>(`/emails/${emailId}/verification`);
  }

  async updateVerification(
    emailId: string,
    checklist: VerificationChecklistItem[],
    override: boolean = false,
    notes?: string
  ): Promise<VerificationChecklistResponse> {
    return this.request<VerificationChecklistResponse>(`/emails/${emailId}/verification`, {
      method: 'POST',
      body: JSON.stringify({
        checklist_answers: checklist,
        override_to_trusted: override,
        candidate_notes: notes,
      }),
    });
  }

  // Job Agent
  async previewJob(emailId: string): Promise<any> {
    return this.request(`/jobs/${emailId}/preview`);
  }

  async generateDraft(emailId: string): Promise<ApplicationDraftResponse> {
    return this.request<ApplicationDraftResponse>(`/jobs/${emailId}/draft`, {
      method: 'POST',
    });
  }

  async sendApprovedApplication(
    emailId: string,
    coverLetter: string,
    recruiterReply: string
  ): Promise<ApplicationRecordResponse> {
    return this.request<ApplicationRecordResponse>(`/jobs/${emailId}/send`, {
      method: 'POST',
      body: JSON.stringify({
        approved_cover_letter: coverLetter,
        approved_recruiter_reply: recruiterReply,
      }),
    });
  }

  async listApplications(): Promise<ApplicationRecordResponse[]> {
    return this.request<ApplicationRecordResponse[]>('/applications');
  }

  // Candidate Profile
  async getProfile(): Promise<CandidateProfileSchema> {
    return this.request<CandidateProfileSchema>('/profile');
  }

  async updateProfile(profile: CandidateProfileSchema): Promise<CandidateProfileSchema> {
    return this.request<CandidateProfileSchema>('/profile', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  }

  async uploadResume(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/profile/resume', {
      method: 'POST',
      body: formData,
    });
  }

  // Preferences
  async getPreferences(): Promise<UserPreferencesSchema> {
    return this.request<UserPreferencesSchema>('/preferences');
  }

  async updatePreferences(prefs: UserPreferencesSchema): Promise<UserPreferencesSchema> {
    return this.request<UserPreferencesSchema>('/preferences', {
      method: 'PUT',
      body: JSON.stringify(prefs),
    });
  }

  // Audit
  async getAuditTrail(): Promise<AuditRecordSchema[]> {
    return this.request<AuditRecordSchema[]>('/audit');
  }

  async verifyAuditChain(): Promise<AuditChainStatusResponse> {
    return this.request<AuditChainStatusResponse>('/audit/verify');
  }
}

export const api = new ApiClient();
