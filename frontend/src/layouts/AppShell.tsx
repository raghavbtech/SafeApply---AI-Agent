import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Header } from '../components/Header';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { AlertTriangle, Upload, Check, Sparkles } from 'lucide-react';

export const AppShell: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Page titles map
  const pageMeta: Record<string, { title: string; subtitle: string }> = {
    '/dashboard': { title: 'Security Command Dashboard', subtitle: 'Real-time overview of threats, scan metrics, and mailbox status' },
    '/inbox': { title: 'Recruitment Mailbox & Scanner', subtitle: 'Filterable live inbox with 4-pillar risk detection' },
    '/scan': { title: 'Ad-Hoc Text & EML Offer Analyzer', subtitle: 'Analyze custom text or upload exported .eml email messages' },
    '/quarantine': { title: 'Threat Quarantine Vault', subtitle: 'Safely isolated recruitment scams with one-click restore' },
    '/verification': { title: 'Ambiguous Offer Verification', subtitle: 'Step-by-step verification checklist and trusted overrides' },
    '/job-agent': { title: 'Autonomous Job Application Agent', subtitle: 'Skill matching, AI cover letter, and recruiter reply draft' },
    '/applications': { title: 'Job Application Tracker', subtitle: 'Audit log of all prepared and dispatched job applications' },
    '/profile': { title: 'Candidate Profile & Resume', subtitle: 'Manage your skills, experience, and uploaded resume' },
    '/audit': { title: 'Tamper-Evident Security Audit Log', subtitle: 'Cryptographic SHA-256 hash chain verification' },
    '/settings': { title: 'Agent Settings & Automation Policy', subtitle: 'Configure IMAP/SMTP links and automation controls' },
  };

  const currentMeta = pageMeta[location.pathname] || {
    title: 'SafeApply Agent',
    subtitle: 'Autonomous Recruitment Defense & Job Hub',
  };

  // Check candidate profile onboarding status
  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
  });

  // Local state for onboarding modal form
  const [obName, setObName] = useState('');
  const [obEmail, setObEmail] = useState('');
  const [obPhone, setObPhone] = useState('');
  const [obEdu, setObEdu] = useState('');
  const [obSkills, setObSkills] = useState('');
  const [obResume, setObResume] = useState<File | null>(null);

  const onboardingMutation = useMutation({
    mutationFn: async () => {
      if (!profile) return;
      const updated = {
        ...profile,
        full_name: obName || profile.full_name,
        email: obEmail || profile.email,
        phone: obPhone || profile.phone,
        education: obEdu || profile.education,
        skills: obSkills ? obSkills.split(',').map((s) => s.trim()).filter(Boolean) : profile.skills,
      };
      await api.updateProfile(updated);
      if (obResume) {
        await api.uploadResume(obResume);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });

  const [dismissedOnboarding, setDismissedOnboarding] = useState(false);

  const showOnboarding = !dismissedOnboarding && profile && !profile.is_complete && location.pathname !== '/profile';

  return (
    <div className="flex min-h-screen bg-dark-950 text-slate-100">
      <Sidebar />
      <div className="flex flex-1 flex-col pl-64 min-w-0 overflow-x-hidden">
        <Header title={currentMeta.title} subtitle={currentMeta.subtitle} />
        <main className="flex-1 p-8 min-w-0 max-w-full">
          <Outlet />
        </main>
      </div>

      {/* Optional Onboarding Modal with Skip Action */}
      {showOnboarding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
          <div className="w-full max-w-xl rounded-2xl border border-cyan-500/30 bg-dark-900 p-6 shadow-2xl shadow-cyan-500/10 relative">
            <button
              type="button"
              onClick={() => setDismissedOnboarding(true)}
              className="absolute right-4 top-4 p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-surface-raised"
            >
              ✕
            </button>
            <div className="flex items-center gap-3 text-cyan-400">
              <Sparkles className="h-6 w-6 shrink-0" />
              <h2 className="font-heading text-lg font-bold text-white">
                Candidate Profile Setup (Optional)
              </h2>
            </div>
            <p className="mt-2 text-xs text-slate-400">
              Enter your qualifications and upload your resume to enable personalized job matching and tailored applications. You can skip this step and use the recruitment fraud scanner immediately.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                onboardingMutation.mutate();
              }}
              className="mt-4 space-y-3"
            >
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300">Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Aarav Sharma"
                    defaultValue={profile?.full_name || ''}
                    onChange={(e) => setObName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-500 caret-black font-medium focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300">Email Address *</label>
                  <input
                    type="email"
                    required
                    placeholder="e.g. aarav@example.com"
                    defaultValue={profile?.email || ''}
                    onChange={(e) => setObEmail(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-500 caret-black font-medium focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300">Phone Number</label>
                  <input
                    type="text"
                    placeholder="+91 98765 43210"
                    defaultValue={profile?.phone || ''}
                    onChange={(e) => setObPhone(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-500 caret-black font-medium focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300">Degree / Major</label>
                  <input
                    type="text"
                    placeholder="B.Tech Computer Science"
                    defaultValue={profile?.education || ''}
                    onChange={(e) => setObEdu(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-500 caret-black font-medium focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-300">Technical Skills (comma-separated)</label>
                <input
                  type="text"
                  placeholder="Python, SQL, REST APIs, Git, Docker"
                  defaultValue={profile?.skills?.join(', ') || ''}
                  onChange={(e) => setObSkills(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-500 caret-black font-medium focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-300">Candidate Resume (PDF, DOCX, TXT) *</label>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => setObResume(e.target.files?.[0] || null)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-dark-850 px-3 py-1.5 text-xs text-slate-400 file:mr-3 file:rounded-md file:border-0 file:bg-cyan-500/10 file:px-2.5 file:py-1 file:text-xs file:font-semibold file:text-cyan-300 hover:file:bg-cyan-500/20"
                />
              </div>

              <div className="mt-5 flex items-center justify-between gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setDismissedOnboarding(true)}
                  className="rounded-lg border border-slate-700 bg-surface-raised px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white"
                >
                  Skip for now (Scanner Only)
                </button>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setDismissedOnboarding(true);
                      navigate('/profile');
                    }}
                    className="rounded-lg px-3 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                  >
                    Open Profile Page
                  </button>
                  <button
                    type="submit"
                    disabled={onboardingMutation.isPending}
                    className="rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2 text-xs font-semibold text-white shadow-neon-cyan hover:opacity-90 transition disabled:opacity-50"
                  >
                    {onboardingMutation.isPending ? 'Saving...' : '🚀 Save Profile & Continue'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
