import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { CandidateProfileSchema } from '../api/contracts';
import { Loading } from '../components/Loading';
import { StatusBanner } from '../components/StatusBanner';
import {
  User,
  Mail,
  Phone,
  Briefcase,
  GraduationCap,
  FileText,
  Upload,
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
    gpa: '',
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

  const { data: profile, isLoading } = useQuery<CandidateProfileSchema>({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
  });

  useEffect(() => {
    if (profile) {
      setFormData(profile);
    }
  }, [profile]);

  const updateMutation = useMutation({
    mutationFn: (updated: CandidateProfileSchema) => api.updateProfile(updated),
    onSuccess: (data) => {
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
    mutationFn: (file: File) => api.uploadResume(file),
    onSuccess: (data) => {
      setFormData((prev) => ({ ...prev, resume_filename: data.filename }));
      setBannerMsg({
        type: 'success',
        text: `Resume ${data.filename} uploaded and parsed successfully!`
      });
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Resume upload failed: ${err.message || 'Unknown error'}`
      });
    }
  });

  const handleAddSkill = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const s = newSkill.trim();
    if (s && !formData.skills.includes(s)) {
      setFormData((prev) => ({ ...prev, skills: [...prev.skills, s] }));
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setFormData((prev) => ({
      ...prev,
      skills: prev.skills.filter((s) => s !== skillToRemove),
    }));
  };

  const handleAddRole = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const r = newRole.trim();
    if (r && !formData.preferred_roles.includes(r)) {
      setFormData((prev) => ({ ...prev, preferred_roles: [...prev.preferred_roles, r] }));
      setNewRole('');
    }
  };

  const handleRemoveRole = (roleToRemove: string) => {
    setFormData((prev) => ({
      ...prev,
      preferred_roles: prev.preferred_roles.filter((r) => r !== roleToRemove),
    }));
  };

  const handleAddLocation = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const loc = newLocation.trim();
    if (loc && !formData.target_locations.includes(loc)) {
      setFormData((prev) => ({ ...prev, target_locations: [...prev.target_locations, loc] }));
      setNewLocation('');
    }
  };

  const handleRemoveLocation = (locToRemove: string) => {
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
    if (formData.skills.length < 3) {
      setBannerMsg({ type: 'warning', text: 'Please add at least 3 skills for accurate AI job matching.' });
      return;
    }

    updateMutation.mutate({
      ...formData,
      is_complete: true,
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadResumeMutation.mutate(file);
    }
  };

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
                  <User className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    required
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    placeholder="Jane Doe"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Email Address *</label>
                <div className="relative">
                  <Mail className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="jane.doe@example.com"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Phone Number</label>
                <div className="relative">
                  <Phone className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={formData.phone || ''}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+1 (555) 019-2834"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Years of Experience</label>
                <div className="relative">
                  <Briefcase className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={formData.experience || ''}
                    onChange={(e) => setFormData({ ...formData, experience: e.target.value })}
                    placeholder="e.g. 5+ years"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-2">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">LinkedIn Profile URL</label>
                <div className="relative">
                  <Linkedin className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="url"
                    value={formData.linkedin_url || ''}
                    onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
                    placeholder="https://linkedin.com/in/janedoe"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Portfolio or GitHub URL</label>
                <div className="relative">
                  <Globe className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="url"
                    value={formData.portfolio_url || ''}
                    onChange={(e) => setFormData({ ...formData, portfolio_url: e.target.value })}
                    placeholder="https://github.com/janedoe"
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
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

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Degree & Field</label>
                <input
                  type="text"
                  value={formData.education || ''}
                  onChange={(e) => setFormData({ ...formData, education: e.target.value })}
                  placeholder="B.S. in Computer Science"
                  className="w-full px-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-violet"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">University / College</label>
                <input
                  type="text"
                  value={formData.university || ''}
                  onChange={(e) => setFormData({ ...formData, university: e.target.value })}
                  placeholder="University of Washington"
                  className="w-full px-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-violet"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">GPA</label>
                <input
                  type="text"
                  value={formData.gpa || ''}
                  onChange={(e) => setFormData({ ...formData, gpa: e.target.value })}
                  placeholder="3.85"
                  className="w-full px-3 py-2 rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-violet"
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
                className="flex-1 px-3.5 py-2 text-xs rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
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
                <span className="text-xs text-slate-500 italic">No skills added yet. Minimum 3 required.</span>
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
                    className="flex-1 px-3.5 py-2 text-xs rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
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
                    className="flex-1 px-3.5 py-2 text-xs rounded-xl bg-surface-raised border border-border-subtle text-white focus:outline-none focus:border-neon-cyan"
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
              </div>
            ) : (
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300">
                No resume file attached yet. Upload a PDF or DOCX file to attach to applications.
              </div>
            )}

            <div>
              <label className="block text-2xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Upload New Resume (PDF, DOCX)
              </label>
              <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-border-subtle hover:border-neon-cyan rounded-xl cursor-pointer bg-surface-raised/40 transition-colors">
                <Upload className="w-6 h-6 text-neon-cyan mb-2" />
                <span className="text-xs font-medium text-slate-300">
                  {uploadResumeMutation.isPending ? 'Uploading file...' : 'Select or drop resume'}
                </span>
                <span className="text-2xs text-slate-500 mt-1">Up to 10MB</span>
                <input
                  type="file"
                  accept=".pdf,.docx,.doc"
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
        </div>
      </form>
    </div>
  );
};
export default Profile;
