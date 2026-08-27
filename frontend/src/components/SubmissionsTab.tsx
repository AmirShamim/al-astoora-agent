import React, { useState } from 'react';
import { 
  ScanEye, 
  Search, 
  CheckCircle2, 
  AlertCircle, 
  Eye, 
  Sparkles, 
  FileCheck, 
  ShieldAlert 
} from 'lucide-react';
import { DocumentSubmission } from '../types/dashboard';
import { DocumentModal } from './DocumentModal';

interface SubmissionsTabProps {
  submissions: DocumentSubmission[];
}

export const SubmissionsTab: React.FC<SubmissionsTabProps> = ({ submissions }) => {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'valid' | 'invalid'>('all');
  const [selectedSub, setSelectedSub] = useState<DocumentSubmission | null>(null);

  const filteredSubmissions = submissions.filter((sub) => {
    const matchesSearch =
      sub.phone.includes(search) ||
      sub.document_type.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filter === 'all' ||
      (filter === 'valid' && sub.is_valid) ||
      (filter === 'invalid' && !sub.is_valid);

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Top Header */}
      <div className="glass-card p-6 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ScanEye className="w-5 h-5 text-purple-400" />
            <span>Gemini Multimodal Vision Submissions Audit</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Raw visual perception records processed concurrently via Module D & <code className="text-brand-300">Gemini 3.7 Flash</code>.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search phone or doc type..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="glass-input pl-9 w-56 text-xs"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded-xl p-1 text-xs">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                filter === 'all' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All ({submissions.length})
            </button>
            <button
              onClick={() => setFilter('valid')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                filter === 'valid' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Valid
            </button>
            <button
              onClick={() => setFilter('invalid')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                filter === 'invalid' ? 'bg-rose-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Rejected
            </button>
          </div>
        </div>
      </div>

      {/* Submissions Feed Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredSubmissions.length > 0 ? (
          filteredSubmissions.map((sub, idx) => {
            const fields = sub.extracted_fields || {};
            const issues = sub.issues || [];

            return (
              <div
                key={sub.id || idx}
                className="glass-card p-6 border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition-all"
              >
                <div>
                  
                  {/* Submission Header */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <span className="text-xs font-mono text-slate-400">{sub.phone}</span>
                      <h3 className="font-bold text-base text-slate-100 capitalize mt-0.5">
                        {sub.document_type.replace(/_/g, ' ')}
                      </h3>
                    </div>

                    {sub.is_valid ? (
                      <span className="badge-emerald">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Valid
                      </span>
                    ) : (
                      <span className="badge-rose">
                        <AlertCircle className="w-3.5 h-3.5" />
                        Rejected
                      </span>
                    )}
                  </div>

                  {/* Gemini Vision Confidence */}
                  <div className="flex items-center gap-2 mb-4 text-[11px] text-slate-400">
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                    <span>Gemini 3.7 Flash Multimodal Analysis</span>
                  </div>

                  {/* Issues box if invalid */}
                  {!sub.is_valid && issues.length > 0 && (
                    <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
                      <div className="flex items-center gap-1.5 font-semibold text-rose-400 mb-1">
                        <ShieldAlert className="w-3.5 h-3.5" />
                        <span>Validation Issues Detected</span>
                      </div>
                      <ul className="space-y-1 pl-4 list-disc text-[11px]">
                        {issues.map((issue, i) => (
                          <li key={i}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Extracted Fields Summary */}
                  {Object.keys(fields).length > 0 ? (
                    <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 mb-4 space-y-1.5">
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Extracted Fields
                      </p>
                      {Object.entries(fields).slice(0, 4).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-xs">
                          <span className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}:</span>
                          <span className="text-slate-200 font-medium font-mono text-[11px] truncate max-w-[140px]">
                            {String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500 italic p-3 bg-slate-950/30 rounded-xl border border-slate-800/50 mb-4">
                      No extracted fields for this submission.
                    </div>
                  )}

                </div>

                {/* Card Action */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 font-mono">
                    {sub.created_at ? new Date(sub.created_at).toLocaleTimeString() : 'Recent'}
                  </span>

                  <button
                    onClick={() => setSelectedSub(sub)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-600/20 hover:bg-brand-600/30 text-brand-300 border border-brand-500/30 text-xs font-semibold transition-all"
                  >
                    <Eye className="w-3.5 h-3.5 text-brand-400" />
                    <span>Inspect File</span>
                  </button>
                </div>
              </div>
            );
          })
        ) : (
          <div className="col-span-full glass-card p-12 text-center text-slate-500">
            <FileCheck className="w-12 h-12 mx-auto mb-3 opacity-40 text-slate-400" />
            <p className="text-sm font-medium text-slate-300">No document submissions found.</p>
            <p className="text-xs text-slate-500 mt-1">Uploaded images and PDFs will appear here with vision extractions.</p>
          </div>
        )}
      </div>

      {/* Selected Submission Inspector Modal */}
      {selectedSub && (
        <DocumentModal
          isOpen={true}
          onClose={() => setSelectedSub(null)}
          title={`Document Submission — ${selectedSub.document_type}`}
          url={selectedSub.signed_url}
          docType={selectedSub.document_type}
          isValid={selectedSub.is_valid}
          issues={selectedSub.issues}
          extractedFields={selectedSub.extracted_fields}
        />
      )}

    </div>
  );
};
