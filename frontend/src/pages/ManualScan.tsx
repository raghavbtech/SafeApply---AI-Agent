import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  FileScan,
  Upload,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  FileText,
  Clock,
  Send,
  AlertTriangle,
  Cpu,
  Layers,
} from 'lucide-react';
import { api } from '../api/client';
import { RiskBadge } from '../components/RiskBadge';
import { Loading } from '../components/Loading';
import clsx from 'clsx';

const PRESET_SAMPLES: Record<string, string> = {
  'Select a preset sample...': '',
  '🚨 High Risk Scam (Advance Fee & Fake Domain)': `Congratulations! You have been selected at TechCorp Solutions for the role of Graduate Software Engineer.
Annual package: INR 8,00,000 per annum.
To confirm your placement slot and receive your formal appointment letter, please remit a refundable registration fee of Rs 1,499 via UPI within 2 hours.
Send your payment confirmation screenshot immediately to hr.techcorp@gmail.com or your candidature will be permanently cancelled.`,
  '✅ Legitimate Offer (Microsoft India Internship)': `Dear Candidate,

Following your technical interviews with our engineering team, we are pleased to offer you an internship at Microsoft India (R&D) Pvt. Ltd.

Role: Software Engineering Intern
Stipend: INR 50,000 per month
Location: Hyderabad Campus

Microsoft never charges any fees or security deposits at any stage of our recruitment process.
Please review and sign your formal offer letter on the Microsoft Careers Portal: https://careers.microsoft.com.

University Recruiting Team, Microsoft India
Email: university-recruiting@microsoft.com`,
  '⚠️ Ambiguous Offer (Unverified Small Agency)': `Hi,

I found your profile on LinkedIn for our boutique digital marketing agency, Apex Media.
We have an open junior web designer role. Salary is around INR 25,000 per month depending on your portfolio.
Please reply with your resume and sample links if interested.

Regards,
Karan
Email: karan.apexmedia@gmail.com`,
};

export const ManualScan: React.FC = () => {
  const [activeMode, setActiveMode] = useState<'text' | 'eml'>('text');
  const [selectedPreset, setSelectedPreset] = useState<string>('Select a preset sample...');
  const [offerText, setOfferText] = useState<string>('');
  const [emlFile, setEmlFile] = useState<File | null>(null);

  // Text Analysis Mutation
  const textMutation = useMutation({
    mutationFn: (text: string) => api.analyzeText(text, false),
  });

  // EML Ingest Mutation
  const emlMutation = useMutation({
    mutationFn: (file: File) => api.importEml(file),
  });

  const handlePresetChange = (presetKey: string) => {
    setSelectedPreset(presetKey);
    setOfferText(PRESET_SAMPLES[presetKey] || '');
  };

  const handleRunAnalysis = () => {
    if (offerText.trim().length >= 10) {
      textMutation.mutate(offerText);
    }
  };

  const handleEmlUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (emlFile) {
      emlMutation.mutate(emlFile);
    }
  };

  const analysis = textMutation.data;

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {/* Header */}
      <div>
        <h2 className="font-heading text-xl font-extrabold text-white">Ad-Hoc Offer & EML Analyzer</h2>
        <p className="text-xs text-slate-400">
          Paste any placement letter, WhatsApp offer, or upload an exported .eml file to run the 4-pillar detection pipeline.
        </p>
      </div>

      {/* Mode Switcher */}
      <div className="flex gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveMode('text')}
          className={clsx(
            'flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition',
            activeMode === 'text'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-neon-cyan'
              : 'text-slate-400 hover:bg-dark-850 hover:text-white'
          )}
        >
          <FileText className="h-4 w-4" /> Paste Offer Text
        </button>
        <button
          onClick={() => setActiveMode('eml')}
          className={clsx(
            'flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition',
            activeMode === 'eml'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-neon-cyan'
              : 'text-slate-400 hover:bg-dark-850 hover:text-white'
          )}
        >
          <Upload className="h-4 w-4" /> Import .EML File
        </button>
      </div>

      {/* TEXT MODE */}
      {activeMode === 'text' && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800/80 bg-dark-900/60 p-6 backdrop-blur-xl space-y-4">
            {/* Presets dropdown */}
            <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Preset Evaluation Benchmarks
              </label>
              <select
                value={selectedPreset}
                onChange={(e) => handlePresetChange(e.target.value)}
                className="rounded-xl border border-slate-700 bg-dark-850 px-3 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
              >
                {Object.keys(PRESET_SAMPLES).map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
              </select>
            </div>

            {/* Offer Text Area */}
            <div>
              <textarea
                rows={7}
                placeholder="Paste recruitment text, job offer, or campus placement notice here..."
                value={offerText}
                onChange={(e) => setOfferText(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-dark-850 p-4 font-mono text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            {/* Analyze Button */}
            <div className="flex justify-end">
              <button
                onClick={handleRunAnalysis}
                disabled={offerText.trim().length < 10 || textMutation.isPending}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-6 py-2.5 text-xs font-bold text-white shadow-neon-cyan transition hover:opacity-95 disabled:opacity-50"
              >
                <Sparkles className={`h-4 w-4 ${textMutation.isPending ? 'animate-spin' : ''}`} />
                <span>{textMutation.isPending ? 'Analyzing with 4 Pillars...' : 'Run Full 4-Pillar Analysis'}</span>
              </button>
            </div>
          </div>

          {/* Analysis Results Display */}
          {textMutation.isPending ? (
            <Loading label="Evaluating text with Rules, EMSCAD ML, Search RAG & Foundry..." />
          ) : analysis ? (
            <div className="rounded-2xl border border-slate-800 bg-dark-900/80 p-6 backdrop-blur-xl space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div>
                  <h3 className="font-heading text-lg font-bold text-white">SafeApply Security Assessment</h3>
                  <p className="text-xs text-slate-400">Execution Mode: {analysis.execution_mode}</p>
                </div>
                <RiskBadge level={analysis.risk_level} score={analysis.risk_score} />
              </div>

              {/* Explanation Box */}
              <div className="rounded-xl border border-slate-800 bg-dark-850/60 p-4">
                <span className="text-xs font-bold text-cyan-400">Synthesized Agent Explanation:</span>
                <p className="mt-2 text-xs text-slate-300 leading-relaxed">{analysis.explanation}</p>
              </div>

              {/* 4 Pillars Breakdown Grid */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {/* 1. Rules */}
                <div className="rounded-xl border border-slate-800 bg-dark-850/40 p-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">1. Rules & Red Flags</span>
                  <div className="mt-3 space-y-1.5 text-xs">
                    {analysis.identified_red_flags?.length > 0 ? (
                      analysis.identified_red_flags.map((flag, idx) => (
                        <div key={idx} className="flex items-start gap-2 rounded bg-rose-500/10 p-2 text-rose-300 border border-rose-500/20">
                          <span>🚩</span> <span>{flag}</span>
                        </div>
                      ))
                    ) : (
                      <span className="text-emerald-400 font-medium">✅ No deterministic advance-fee or urgency flags.</span>
                    )}
                  </div>
                </div>

                {/* 2. EMSCAD ML */}
                <div className="rounded-xl border border-slate-800 bg-dark-850/40 p-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">2. EMSCAD Machine Learning</span>
                  <div className="mt-3 space-y-2 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Fraud Probability:</span>
                      <span className="font-heading text-base font-bold text-white">
                        {analysis.tool_outputs?.ml_classifier?.fraud_probability_pct ?? 0}%
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Statistical Band:</span>
                      <span className="font-semibold text-cyan-400">
                        {analysis.tool_outputs?.ml_classifier?.risk_band || 'Standard'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 3. Search RAG */}
                <div className="rounded-xl border border-slate-800 bg-dark-850/40 p-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">3. Azure Search RAG</span>
                  <div className="mt-3 space-y-2 text-xs">
                    {(analysis.tool_outputs?.rag_matches?.length ?? 0) > 0 ? (
                      analysis.tool_outputs?.rag_matches?.map((p: any, i: number) => (
                        <div key={i} className="rounded bg-dark-900 p-2 border border-slate-800">
                          <span className="font-bold text-amber-300">{p.category}</span>
                          <p className="text-[11px] text-slate-400 mt-0.5">{p.pattern}</p>
                        </div>
                      ))
                    ) : (
                      <span className="text-slate-500">No matching scam pattern vectors.</span>
                    )}
                  </div>
                </div>

                {/* 4. Domain & Salary */}
                <div className="rounded-xl border border-slate-800 bg-dark-850/40 p-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">4. Domain & Salary Sanity</span>
                  <div className="mt-3 space-y-2 text-xs text-slate-300">
                    <p><b>Domain:</b> {analysis.tool_outputs?.domain_verification?.assessment || 'N/A'}</p>
                    <p><b>Salary:</b> {analysis.tool_outputs?.salary_sanity?.assessment || 'N/A'}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* EML MODE */}
      {activeMode === 'eml' && (
        <div className="rounded-2xl border border-slate-800/80 bg-dark-900/60 p-8 backdrop-blur-xl space-y-6">
          <div className="text-center max-w-md mx-auto">
            <Upload className="h-12 w-12 text-cyan-400 mx-auto" />
            <h3 className="mt-3 font-heading text-lg font-bold text-white">Upload MIME Email File (.eml)</h3>
            <p className="mt-1 text-xs text-slate-400">
              Download any email from Gmail or Outlook ('Download original message') and drop it here to parse authentic headers and links.
            </p>
          </div>

          <form onSubmit={handleEmlUpload} className="max-w-md mx-auto space-y-4">
            <input
              type="file"
              accept=".eml"
              required
              onChange={(e) => setEmlFile(e.target.files?.[0] || null)}
              className="w-full rounded-xl border border-slate-700 bg-dark-850 p-3 text-xs text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-cyan-500/20 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-cyan-300 hover:file:bg-cyan-500/30"
            />

            <button
              type="submit"
              disabled={!emlFile || emlMutation.isPending}
              className="w-full rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 py-2.5 text-xs font-bold text-white shadow-neon-cyan transition hover:opacity-95 disabled:opacity-50"
            >
              {emlMutation.isPending ? 'Ingesting and Parsing EML...' : 'Ingest & Scan EML File'}
            </button>
          </form>

          {emlMutation.data && (
            <div className="mt-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 max-w-md mx-auto text-xs space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 font-bold">
                <CheckCircle2 className="h-4 w-4" /> EML Ingested Successfully!
              </div>
              <p className="text-slate-300"><b>Subject:</b> {emlMutation.data.subject}</p>
              <p className="text-slate-300"><b>From:</b> {emlMutation.data.sender}</p>
              <p className="text-slate-400">
                Recruitment classified: {emlMutation.data.is_recruitment ? '✅ Yes' : '❌ Non-recruitment'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
