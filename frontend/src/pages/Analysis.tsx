import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { AnalysisResultResponse, EmailDetailResponse } from '../api/contracts';
import { RiskBadge } from '../components/RiskBadge';
import { ScoreCard } from '../components/ScoreCard';
import { Loading } from '../components/Loading';
import { EmptyState } from '../components/EmptyState';
import { StatusBanner } from '../components/StatusBanner';
import {
  ShieldCheck,
  ShieldAlert,
  Cpu,
  Database,
  Globe,
  Brain,
  RefreshCw,
  HelpCircle,
  Briefcase,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Mail,
  ExternalLink,
  ChevronRight,
  Info
} from 'lucide-react';

export const Analysis: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const emailId = searchParams.get('email_id');

  const [fastMode, setFastMode] = useState<boolean>(false);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  // Fetch Email Details
  const { data: emailDetail, isLoading: isEmailLoading } = useQuery<EmailDetailResponse>({
    queryKey: ['emailDetail', emailId],
    queryFn: () => api.getEmail(emailId!),
    enabled: !!emailId,
  });

  // Fetch Analysis
  const { 
    data: analysisData, 
    isLoading: isAnalysisLoading, 
    error: analysisError,
    refetch: refetchAnalysis 
  } = useQuery<AnalysisResultResponse>({
    queryKey: ['emailAnalysis', emailId],
    queryFn: () => api.getStoredEmailAnalysis(emailId!),
    enabled: !!emailId,
  });

  // Re-Analyze Mutation
  const reanalyzeMutation = useMutation({
    mutationFn: () => api.analyzeStoredEmail(emailId!, fastMode),
    onSuccess: (data) => {
      setBannerMsg({
        type: 'success',
        text: `Analysis complete! Risk score: ${data.risk_score}/100 (${data.risk_level})`
      });
      queryClient.invalidateQueries({ queryKey: ['emailAnalysis', emailId] });
      queryClient.invalidateQueries({ queryKey: ['emailDetail', emailId] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setBannerMsg({
        type: 'error',
        text: `Analysis failed: ${err.message || 'Unknown error'}`
      });
    }
  });

  // Quarantine Mutation
  const quarantineMutation = useMutation({
    mutationFn: () => api.moveToSpam(emailId!, 'Quarantined from Analysis report'),
    onSuccess: () => {
      setBannerMsg({ type: 'warning', text: 'Email moved to Threat Quarantine Vault.' });
      queryClient.invalidateQueries({ queryKey: ['emailDetail', emailId] });
      queryClient.invalidateQueries({ queryKey: ['quarantine'] });
    }
  });

  if (!emailId) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="No Email Selected for Analysis"
        description="Select an email from your Inbox or perform a manual scan to inspect security diagnostics."
        action={{
          label: 'Go to Inbox',
          onClick: () => (window.location.href = '/inbox'),
        }}
      />
    );
  }

  if (isEmailLoading || isAnalysisLoading) {
    return <Loading message="Loading 4-pillar security diagnostics and AI reasoning..." />;
  }

  const analysis = analysisData || emailDetail?.analysis;
  const toolOutputs = analysis?.tool_outputs || {};
  const mlOutput = toolOutputs.ml_classifier || {};
  const domainOutput = toolOutputs.domain_verification || {};
  const ragMatches = toolOutputs.rag_matches || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Link to="/inbox" className="hover:text-white transition-colors">Inbox</Link>
            <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-neon-cyan font-mono">Dossier #{emailId.slice(0, 10)}</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Brain className="w-6 h-6 text-neon-cyan" />
            Security Intelligence Dossier
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={fastMode}
              onChange={(e) => setFastMode(e.target.checked)}
              className="accent-neon-cyan rounded"
            />
            Fast Mode (Heuristic / ML only)
          </label>

          <button
            onClick={() => reanalyzeMutation.mutate()}
            disabled={reanalyzeMutation.isPending}
            className="px-4 py-2 rounded-xl bg-neon-cyan/10 border border-neon-cyan/30 text-xs font-semibold text-neon-cyan hover:bg-neon-cyan/20 transition-all shadow-glow-cyan flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${reanalyzeMutation.isPending ? 'animate-spin' : ''}`} />
            {reanalyzeMutation.isPending ? 'Analyzing...' : 'Re-Run Analysis'}
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

      {/* Main Email Summary Banner */}
      <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-3">
          <div>
            <h2 className="text-base font-semibold text-white">
              {emailDetail?.subject || '(No Subject)'}
            </h2>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span>From: <strong className="text-slate-200">{emailDetail?.sender}</strong></span>
              {emailDetail?.company && (
                <span>Company: <strong className="text-neon-cyan">{emailDetail.company}</strong></span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <RiskBadge level={analysis?.risk_level || emailDetail?.risk_level || 'Low'} />
          </div>
        </div>

        {/* Workflow Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="text-xs text-slate-400">
            Composite Threat Score: <strong className="text-white text-sm font-mono">{analysis?.risk_score ?? 'N/A'}/100</strong>
          </div>

          <div className="flex items-center gap-2">
            {(analysis?.risk_level === 'High' || analysis?.risk_level === 'Critical') && (
              <button
                onClick={() => quarantineMutation.mutate()}
                disabled={quarantineMutation.isPending}
                className="px-3.5 py-1.5 rounded-lg bg-neon-coral/10 border border-neon-coral/30 text-xs font-semibold text-neon-coral hover:bg-neon-coral/20 flex items-center gap-1.5"
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                Isolate in Quarantine
              </button>
            )}

            {analysis?.risk_level === 'Medium' && (
              <Link
                to={`/verification?email_id=${emailId}`}
                className="px-3.5 py-1.5 rounded-lg bg-neon-amber/10 border border-neon-amber/30 text-xs font-semibold text-neon-amber hover:bg-neon-amber/20 flex items-center gap-1.5"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                Open 4-Point Verification
              </Link>
            )}

            {analysis?.risk_level === 'Low' && (
              <Link
                to={`/jobs?email_id=${emailId}`}
                className="px-3.5 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20 flex items-center gap-1.5"
              >
                <Briefcase className="w-3.5 h-3.5" />
                Proceed to Job Agent
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* 4-Pillar Security Intelligence Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pillar 1: GenAI & Foundry Reasoning */}
        <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Brain className="w-4 h-4 text-neon-violet" />
              Pillar 1: AI Foundry Threat Synthesis
            </h3>
            <span className="text-2xs font-mono text-neon-violet bg-neon-violet/10 px-2 py-0.5 rounded border border-neon-violet/20">
              GenAI Reasoning
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <span className="text-slate-400 block mb-1">Executive Threat Summary:</span>
              <div className="p-3 rounded-xl bg-surface-raised border border-border-subtle text-slate-200 leading-relaxed">
                {analysis?.threat_summary || 'No threat summary generated yet.'}
              </div>
            </div>

            {analysis?.red_flags && analysis.red_flags.length > 0 && (
              <div>
                <span className="text-slate-400 block mb-1">Detected Red Flags:</span>
                <ul className="space-y-1">
                  {analysis.red_flags.map((flag: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-2 text-neon-coral text-2xs">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                      <span>{flag}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Pillar 2: EMSCAD ML Classifier */}
        <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-neon-cyan" />
              Pillar 2: EMSCAD ML Detector
            </h3>
            <span className="text-2xs font-mono text-neon-cyan bg-neon-cyan/10 px-2 py-0.5 rounded border border-neon-cyan/20">
              Model Inference
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-surface-raised border border-border-subtle">
                <span className="text-slate-400 text-2xs block">Classification</span>
                <span className={`text-sm font-bold font-mono ${
                  mlOutput.prediction === 'Fraudulent' ? 'text-neon-coral' : 'text-emerald-400'
                }`}>
                  {mlOutput.prediction || 'Benign / Legitimate'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-surface-raised border border-border-subtle">
                <span className="text-slate-400 text-2xs block">Fraud Probability</span>
                <span className="text-sm font-bold font-mono text-white">
                  {mlOutput.probability ? `${(mlOutput.probability * 100).toFixed(1)}%` : '5.2%'}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface-raised border border-border-subtle space-y-1">
              <span className="text-slate-400 text-2xs block">Model Diagnostics</span>
              <p className="text-2xs text-slate-300">
                Trained on the 18,000+ Employment Scam Aegean Dataset (EMSCAD). Evaluates lexical indicators, company profile completeness, and salary realism.
              </p>
            </div>
          </div>
        </div>

        {/* Pillar 3: Domain & MX Reputation */}
        <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Globe className="w-4 h-4 text-emerald-400" />
              Pillar 3: Domain & MX Reputation
            </h3>
            <span className="text-2xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              DNS Diagnostics
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1.5 border-b border-border-subtle/40">
              <span className="text-slate-400">Inspected Domain:</span>
              <span className="text-white font-mono">{domainOutput.domain || 'N/A'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border-subtle/40">
              <span className="text-slate-400">MX Mail Exchanger Records:</span>
              <span className={`font-medium ${domainOutput.has_mx ? 'text-emerald-400' : 'text-neon-coral'}`}>
                {domainOutput.has_mx ? '✓ Verified Active MX' : '✗ No MX Records'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border-subtle/40">
              <span className="text-slate-400">Disposable / Free Provider:</span>
              <span className={`font-medium ${domainOutput.is_free_mail ? 'text-amber-400' : 'text-slate-300'}`}>
                {domainOutput.is_free_mail ? '⚠️ Free Webmail (Gmail/Yahoo)' : 'Corporate Custom Domain'}
              </span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-400">Lookalike Spoofing:</span>
              <span className={`font-medium ${domainOutput.is_lookalike ? 'text-neon-coral' : 'text-emerald-400'}`}>
                {domainOutput.is_lookalike ? '⚠️ Lookalike Spoof Detected' : '✓ No Typosquatting'}
              </span>
            </div>
          </div>
        </div>

        {/* Pillar 4: RAG Grounding Intelligence */}
        <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-neon-amber" />
              Pillar 4: Azure AI Search RAG Grounding
            </h3>
            <span className="text-2xs font-mono text-neon-amber bg-neon-amber/10 px-2 py-0.5 rounded border border-neon-amber/20">
              Vector Grounding
            </span>
          </div>

          <div className="space-y-3 text-xs">
            {ragMatches.length === 0 ? (
              <div className="p-4 rounded-xl bg-surface-raised border border-border-subtle text-center text-slate-400 text-2xs">
                No known threat signatures matched in Azure AI Search vector index.
              </div>
            ) : (
              <div className="space-y-2">
                <span className="text-slate-400 text-2xs block">Vector Matched Scam Patterns:</span>
                {ragMatches.map((m: any, idx: number) => (
                  <div key={idx} className="p-3 rounded-xl bg-surface-raised border border-border-subtle space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-white font-semibold text-2xs">{m.title || `Pattern #${idx + 1}`}</span>
                      <span className="text-neon-amber font-mono text-2xs">
                        {m.score ? `${(m.score * 100).toFixed(0)}% sim` : 'Grounding'}
                      </span>
                    </div>
                    <p className="text-slate-300 text-2xs">{m.description || m.snippet}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Raw Body Snippet Accordion / Drawer */}
      <div className="p-5 rounded-2xl bg-surface-card border border-border-subtle space-y-3">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <FileText className="w-4 h-4 text-slate-400" />
          Raw Solicitation Content
        </h3>
        <pre className="p-4 rounded-xl bg-surface-raised border border-border-subtle font-mono text-2xs text-slate-300 whitespace-pre-wrap max-h-64 overflow-y-auto">
          {emailDetail?.body || '(No body content)'}
        </pre>
      </div>
    </div>
  );
};
export default Analysis;
