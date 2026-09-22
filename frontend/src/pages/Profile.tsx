import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { CandidateProfileSchema } from '../api/contracts';
import { useSession } from '../auth/AuthProvider';
import { Loading } from '../components/Loading';
import { StatusBanner } from '../components/StatusBanner';
import { RESUME_ACCEPT, validateResumeFile } from '../utils/resumeValidation';
import {
  User,
  Mail,
  Phone,
  Briefcase,
  GraduationCap,
  FileText,
  Upload,
  Download,
  CheckCircle2,
  AlertCircle,
  Plus,
  X,
  Globe,
  Linkedin,
  MapPin,
  Save
} from 'lucide-react';

export const Profile: React.FC = () => {
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState<CandidateProfileSchema>({
    full_name: '',
    email: '',
    phone: '',
    education: '',
    university: '',
    cgpa: '',
    grading_scale: '',
    skills: [],
    experience: '',
    preferred_roles: [],
    target_locations: [],
    portfolio_url: '',
    linkedin_url: '',
    resume_filename: '',
    is_complete: false,
  });

  const [newSkill, setNewSkill] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const isDirtyRef = React.useRef(false);

  const handleInputChange = (field: keyof CandidateProfileSchema, value: any) => {
    isDirtyRef.current = true;
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const { loading: sessionLoading, session } = useSession();
  const sessionIdRef = React.useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!session?.session_id) return;
    if (sessionIdRef.current && sessionIdRef.current !== session.session_id) {
      isDirtyRef.current = false;
      setFormData({
        full_name: '', email: '', phone: '', education: '', university: '', cgpa: '',
        grading_scale: '', skills: [], experience: '', preferred_roles: [],
        target_locations: [], portfolio_url: '', linkedin_url: '', resume_filename: '',
        is_complete: false,
      });
      setNewSkill('');
      setNewRole('');
      setNewLocation('');
    }
    sessionIdRef.current = session.session_id;
  }, [session?.session_id]);

  const { data: profile, isLoading } = useQuery<CandidateProfileSchema>({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
    enabled: !sessionLoading && Boolean(session),
  });

  useEffect(() => {
    if (profile) {
      setFormData((prev) => {
        // If the user has unsaved edits in the form, preserve their inputs and only merge server fields
        if (isDirtyRef.current) return prev;
        return profile;
      });
    }
  }, [profile]);

  const updateMutation = useMutation({
    mutationFn: (updated: CandidateProfileSchema) => api.updateProfile(updated),
    onSuccess: (data) => {
      isDirtyRef.current = false;
      setFormData(data);
      setBannerMsg({
        type: 'success',
        text: 'Candidate profile updated successfully. Job matching weights updated!'
      });
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Failed to update profile: ${err.message || 'Unknown error'}`
      });
    }
  });

  const uploadResumeMutation = useMutation({
    mutationFn: async (file: File) => {
      // Auto-save candidate details first so the backend updates candidate_profile before attaching resume
      const hasUserData = Boolean(
        formData.full_name || formData.email || formData.phone || formData.education ||
        formData.university || formData.cgpa || formData.experience || formData.skills.length > 0
      );
      if (hasUserData) {
        try {
          await api.updateProfile(formData);
          isDirtyRef.current = false;
        } catch (e) {
          console.warn('Could not auto-save candidate profile before resume upload:', e);
        }
      }
      return api.uploadResume(file);
    },
    onSuccess: (data) => {
      closePreview();
      setFormData((prev) => ({ ...prev, resume_filename: data.filename }));
      setBannerMsg({
        type: 'success',
        text: `Resume "${data.filename}" uploaded and attached to profile successfully!`
      });
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
    onError: (err: any) => {
      const message = err.message || '';
      const friendlyMessage = message.includes('10MB')
        ? 'That resume is larger than the 10MB limit.'
        : message.includes('Supported resume formats') || message.includes('Invalid')
          ? 'Please choose a valid PDF, DOCX, or TXT resume.'
          : 'We could not attach that resume right now. Please try again.';
      setBannerMsg({
        type: 'error',
        text: friendlyMessage
      });
    }
  });

  const handleAddSkill = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const s = newSkill.trim();
    if (s && !formData.skills.includes(s)) {
      isDirtyRef.current = true;
      setFormData((prev) => ({ ...prev, skills: [...prev.skills, s] }));
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    isDirtyRef.current = true;
    setFormData((prev) => ({
      ...prev,
      skills: prev.skills.filter((s) => s !== skillToRemove),
    }));
  };

  const handleAddRole = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const r = newRole.trim();
    if (r && !formData.preferred_roles.includes(r)) {
      isDirtyRef.current = true;
      setFormData((prev) => ({ ...prev, preferred_roles: [...prev.preferred_roles, r] }));
      setNewRole('');
    }
  };

  const handleRemoveRole = (roleToRemove: string) => {
    isDirtyRef.current = true;
    setFormData((prev) => ({
      ...prev,
      preferred_roles: prev.preferred_roles.filter((r) => r !== roleToRemove),
    }));
  };

  const handleAddLocation = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const loc = newLocation.trim();
    if (loc && !formData.target_locations.includes(loc)) {
      isDirtyRef.current = true;
      setFormData((prev) => ({ ...prev, target_locations: [...prev.target_locations, loc] }));
      setNewLocation('');
    }
  };

  const handleRemoveLocation = (locToRemove: string) => {
    isDirtyRef.current = true;
    setFormData((prev) => ({
      ...prev,
      target_locations: prev.target_locations.filter((l) => l !== locToRemove),
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.full_name || !formData.email) {
      setBannerMsg({ type: 'error', text: 'Full Name and Email are required fields.' });
      return;
    }
    updateMutation.mutate({
      ...formData,
      is_complete: true,
    });
  };

  const handleResumeSelection = (file: File | undefined) => {
    if (!file) return;
    const validationError = validateResumeFile(file);
    if (validationError) {
      setBannerMsg({ type: 'error', text: validationError });
      return;
    }
    uploadResumeMutation.mutate(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleResumeSelection(e.target.files?.[0]);
    e.target.value = '';
  };

  const closePreview = () => {
    setIsPreviewOpen(false);
    setPreviewError(null);
  };

  useEffect(() => {
    if (!isPreviewOpen || !formData.resume_filename) return;

    const isPdf = formData.resume_filename.toLowerCase().endsWith('.pdf');
    let cancelled = false;
    setPreviewLoading(true);
    setPreviewError(null);
    const getResumeFile = isPdf ? api.getResumePreview : api.getResumeDownload;
    getResumeFile.call(api)
      .then((blob) => {
        if (!cancelled) setPreviewUrl(URL.createObjectURL(blob));
      })
      .catch((error: Error) => {
        if (!cancelled) setPreviewError(error.message || 'Unable to load resume preview.');
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });

    return () => {
      cancelled = true;
      setPreviewUrl((url) => {
        if (url) URL.revokeObjectURL(url);
        return null;
      });
    };
  }, [isPreviewOpen, formData.resume_filename]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  if (isLoading) {
    return <Loading message="Loading candidate profile and skills index..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <User className="w-6 h-6 text-neon-cyan" />
            Candidate Profile & Match Tuning
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure your professional qualifications, target roles, and resume to power the Autonomous Job Agent.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {formData.is_complete ? (
            <span className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-400 font-medium flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Profile Ready
            </span>
          ) : (
            <span className="px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-400 font-medium flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" />
              Setup Incomplete
            </span>
          )}
        </div>
      </div>

      {bannerMsg && (
        <StatusBanner 
          type={bannerMsg.type} 
          message={bannerMsg.text} 
          onDismiss={() => setBannerMsg(null)} 
        />
      )}

      <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Main Profile Details */}
        <div className="lg:col-span-2 space-y-5">
          {/* Personal Info */}
          <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
            <h3 className="text-sm font-semibold text-white border-b border-border-subtle pb-3 flex items-center gap-2">
              <User className="w-4 h-4 text-neon-cyan" />
              Identity & Contact Coordinates
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Full Name *</label>
                <div className="relative">
                  <User className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={formData.full_name}
                    onChange={(e) => handleInputChange('full_name', e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Email Address *</label>
                <div className="relative">
                  <Mail className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    placeholder="jane.doe@example.com"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Phone Number</label>
                <div className="relative">
                  <Phone className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    value={formData.phone || ''}
                    onChange={(e) => handleInputChange('phone', e.target.value)}
                    placeholder="+91 98xx00xx00"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Years of Experience</label>
                <div className="relative">
                  <Briefcase className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    value={formData.experience || ''}
                    onChange={(e) => handleInputChange('experience', e.target.value)}
                    placeholder="e.g. 5+ years"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-2">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">LinkedIn Profile URL</label>
                <div className="relative">
                  <Linkedin className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="url"
                    value={formData.linkedin_url || ''}
                    onChange={(e) => handleInputChange('linkedin_url', e.target.value)}
                    placeholder="https://linkedin.com/in/janedoe"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Portfolio or GitHub URL</label>
                <div className="relative">
                  <Globe className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="url"
                    value={formData.portfolio_url || ''}
                    onChange={(e) => handleInputChange('portfolio_url', e.target.value)}
                    placeholder="https://github.com/janedoe"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Education */}
          <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
            <h3 className="text-sm font-semibold text-white border-b border-border-subtle pb-3 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-neon-violet" />
              Academic Credentials
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Degree & Field</label>
                <input
                  type="text"
                  value={formData.education || ''}
                  onChange={(e) => handleInputChange('education', e.target.value)}
                  placeholder="B.S. in Computer Science"
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-violet focus:ring-1 focus:ring-neon-violet font-medium"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">University / College</label>
                <input
                  type="text"
                  value={formData.university || ''}
                  onChange={(e) => handleInputChange('university', e.target.value)}
                  placeholder="University of Washington"
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-violet focus:ring-1 focus:ring-neon-violet font-medium"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">CGPA</label>
                <input
                  type="text"
                  value={formData.cgpa || ''}
                  onChange={(e) => handleInputChange('cgpa', e.target.value)}
                  placeholder="Enter your CGPA (e.g., 8.5)"
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-violet focus:ring-1 focus:ring-neon-violet font-medium"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Grading Scale</label>
                <input
                  type="text"
                  value={formData.grading_scale || ''}
                  onChange={(e) => handleInputChange('grading_scale', e.target.value)}
                  placeholder="e.g., 10 or 4"
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-violet focus:ring-1 focus:ring-neon-violet font-medium"
                />
              </div>
            </div>
          </div>

          {/* Skills Tag Management */}
          <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
            <div className="border-b border-border-subtle pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Technical & Core Skills</h3>
                <p className="text-xs text-slate-400">Add keywords used to compute job match percentages.</p>
              </div>
              <span className="text-xs font-mono text-neon-cyan px-2 py-0.5 rounded bg-neon-cyan/10 border border-neon-cyan/30">
                {formData.skills.length} skills indexed
              </span>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
                placeholder="Add skill (e.g. Python, Azure, React, Docker)..."
                className="flex-1 px-3.5 py-2 text-xs rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
              />
              <button
                type="button"
                onClick={() => handleAddSkill()}
                className="px-4 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white text-xs font-medium hover:bg-slate-700 transition-colors flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Add
              </button>
            </div>

            <div className="flex flex-wrap gap-2 pt-1 min-h-[48px]">
              {formData.skills.length === 0 ? (
                <span className="text-xs text-slate-500 italic">No skills added yet. Add skills later to improve job matching.</span>
              ) : (
                formData.skills.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-neon-cyan/10 border border-neon-cyan/30 text-neon-cyan"
                  >
                    {skill}
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(skill)}
                      className="hover:text-neon-coral transition-colors"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>

          {/* Preferences: Target Roles & Locations */}
          <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
            <h3 className="text-sm font-semibold text-white border-b border-border-subtle pb-3">
              Target Roles & Geographical Preferences
            </h3>

            <div className="space-y-4 text-xs">
              {/* Target Roles */}
              <div className="space-y-2">
                <label className="text-slate-300 font-medium">Preferred Job Titles</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddRole())}
                    placeholder="e.g. Senior Software Engineer, Cloud Architect..."
                    className="flex-1 px-3.5 py-2 text-xs rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
                  />
                  <button
                    type="button"
                    onClick={() => handleAddRole()}
                    className="px-3.5 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white text-xs hover:bg-slate-700"
                  >
                    Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {formData.preferred_roles.map((role) => (
                    <span
                      key={role}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-surface-raised border border-border-subtle text-slate-300"
                    >
                      {role}
                      <button type="button" onClick={() => handleRemoveRole(role)} className="hover:text-neon-coral">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* Target Locations */}
              <div className="space-y-2 pt-2">
                <label className="text-slate-300 font-medium">Target Locations & Work Modes</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newLocation}
                    onChange={(e) => setNewLocation(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddLocation())}
                    placeholder="e.g. Remote, San Francisco, CA, New York, NY..."
                    className="flex-1 px-3.5 py-2 text-xs rounded-xl bg-white border border-slate-300 text-slate-900 placeholder:text-slate-500 caret-black focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan font-medium"
                  />
                  <button
                    type="button"
                    onClick={() => handleAddLocation()}
                    className="px-3.5 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white text-xs hover:bg-slate-700"
                  >
                    Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {formData.target_locations.map((loc) => (
                    <span
                      key={loc}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-surface-raised border border-border-subtle text-slate-300"
                    >
                      <MapPin className="w-3 h-3 text-slate-500" />
                      {loc}
                      <button type="button" onClick={() => handleRemoveLocation(loc)} className="hover:text-neon-coral">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Resume Upload & Save */}
        <div className="lg:col-span-1 space-y-5">
          {/* Resume Card */}
          <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
            <h3 className="text-sm font-semibold text-white border-b border-border-subtle pb-3 flex items-center gap-2">
              <FileText className="w-4 h-4 text-neon-cyan" />
              Attached Resume
            </h3>

            {formData.resume_filename ? (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 space-y-1">
                <div className="flex items-center gap-2 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span className="truncate">{formData.resume_filename}</span>
                </div>
                <p className="text-2xs text-slate-400">
                  Ready for autonomous application drafting.
                </p>
                <p className="text-2xs text-slate-500 uppercase tracking-wide">
                  File type: {formData.resume_filename.split('.').pop()?.toUpperCase() || 'Unknown'}
                </p>
              </div>
            ) : (
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300">
                No resume file attached yet. Upload a PDF or DOCX file to attach to applications.
              </div>
            )}

            {formData.resume_filename && (
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => {
                    setPreviewError(null);
                    setIsPreviewOpen(true);
                  }}
                  className="w-full py-2 px-3 rounded-lg border border-neon-cyan/40 bg-neon-cyan/10 hover:bg-neon-cyan/20 text-neon-cyan font-medium text-xs flex items-center justify-center gap-1.5 transition"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Preview Resume
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    if (window.confirm('Delete your uploaded resume file?')) {
                      closePreview();
                      await api.deleteResume();
                      setFormData((prev) => ({ ...prev, resume_filename: '', resume_path: '' }));
                      queryClient.invalidateQueries({ queryKey: ['profile'] });
                      setBannerMsg({ type: 'success', text: 'Resume file deleted successfully.' });
                    }
                  }}
                  className="w-full py-2 px-3 rounded-lg border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 font-medium text-xs flex items-center justify-center gap-1.5 transition"
                >
                  <X className="w-3.5 h-3.5" />
                  Remove Attached Resume
                </button>
              </div>
            )}

            <div>
              <label className="block text-2xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Upload New Resume (PDF, DOCX, TXT)
              </label>
              <label
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  handleResumeSelection(event.dataTransfer.files?.[0]);
                }}
                className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border-subtle bg-surface-raised/40 p-6 transition-colors hover:border-neon-cyan"
              >
                <Upload className="w-6 h-6 text-neon-cyan mb-2" />
                <span className="text-xs font-medium text-slate-300">
                  {uploadResumeMutation.isPending ? 'Uploading file...' : 'Select or drop resume'}
                </span>
                <span className="text-2xs text-slate-500 mt-1">Up to 10MB</span>
                <input
                  type="file"
                  accept={RESUME_ACCEPT}
                  onChange={handleFileChange}
                  disabled={uploadResumeMutation.isPending}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* Submit Action */}
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="w-full py-3.5 px-4 rounded-xl bg-neon-cyan hover:bg-neon-cyan/90 text-black font-semibold text-xs tracking-wide transition-all shadow-glow-cyan flex items-center justify-center gap-2"
          >
            <Save className="w-4 h-4" />
            {updateMutation.isPending ? 'Saving Profile...' : 'Save Profile & Update Matching'}
          </button>

          {formData.full_name && (
            <button
              type="button"
              onClick={async () => {
                if (window.confirm('Clear all profile details and delete attached resume?')) {
                  await api.deleteProfile();
                  setFormData({
                    full_name: '',
                    email: '',
                    phone: '',
                    education: '',
                    university: '',
                    cgpa: '',
                    grading_scale: '',
                    skills: [],
                    experience: '',
                    preferred_roles: [],
                    target_locations: [],
                    portfolio_url: '',
                    linkedin_url: '',
                    resume_filename: '',
                    is_complete: false,
                  });
                  queryClient.setQueryData(['profile'], {
                    full_name: '',
                    email: '',
                    phone: '',
                    education: '',
                    university: '',
                    cgpa: '',
                    grading_scale: '',
                    skills: [],
                    experience: '',
                    preferred_roles: [],
                    target_locations: [],
                    portfolio_url: '',
                    linkedin_url: '',
                    resume_filename: '',
                    is_complete: false,
                  });
                  queryClient.invalidateQueries({ queryKey: ['profile'] });
                  setBannerMsg({ type: 'success', text: 'Candidate profile and resume cleared.' });
                }
              }}
              className="w-full py-2.5 px-3 rounded-xl border border-slate-700 bg-surface-raised hover:bg-slate-800 text-slate-400 hover:text-rose-400 text-xs font-medium transition flex items-center justify-center gap-1.5"
            >
              Clear Profile Information
            </button>
          )}
        </div>
      </form>

      {isPreviewOpen && formData.resume_filename && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-3 sm:p-6 backdrop-blur-md" role="dialog" aria-modal="true" aria-labelledby="resume-preview-title">
          <div className="flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-border-subtle bg-surface-card shadow-2xl">
            <div className="flex items-center justify-between gap-3 border-b border-border-subtle px-4 py-3 sm:px-6">
              <h2 id="resume-preview-title" className="truncate text-sm font-semibold text-white">{formData.resume_filename}</h2>
              <button type="button" onClick={closePreview} aria-label="Close resume preview" className="rounded-lg p-2 text-slate-400 hover:bg-surface-raised hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 bg-slate-950 p-3 sm:p-5">
              {formData.resume_filename.toLowerCase().endsWith('.pdf') ? (
                previewLoading ? (
                  <div className="flex h-full items-center justify-center text-sm text-slate-400">Loading resume preview...</div>
                ) : previewError ? (
                  <div className="flex h-full items-center justify-center text-center text-sm text-rose-300">{previewError}</div>
                ) : previewUrl ? (
                  <iframe title={`Preview of ${formData.resume_filename}`} src={previewUrl} className="h-full w-full rounded-lg bg-white" />
                ) : null
              ) : (
                <div className="flex h-full items-center justify-center px-5 text-center text-sm text-slate-300">
                  Preview is currently available for PDF resumes. Download this DOCX file to view it.
                </div>
              )}
            </div>
            <div className="flex flex-col-reverse gap-2 border-t border-border-subtle px-4 py-3 sm:flex-row sm:justify-end sm:px-6">
              <button type="button" onClick={closePreview} className="rounded-lg border border-border-subtle px-4 py-2 text-xs font-medium text-slate-300 hover:bg-surface-raised">Close</button>
              {previewUrl && (
                <a href={previewUrl} download={formData.resume_filename} className="flex items-center justify-center gap-1.5 rounded-lg bg-neon-cyan px-4 py-2 text-xs font-semibold text-black hover:bg-neon-cyan/90">
                  <Download className="h-3.5 w-3.5" />
                  Download
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default Profile;
