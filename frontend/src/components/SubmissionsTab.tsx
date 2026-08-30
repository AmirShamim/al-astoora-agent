import React, { useState } from 'react';
import { 
  ScanEye, 
  Search, 
  CheckCircle2, 
  AlertCircle, 
  Eye, 
  FileCheck, 
  ShieldAlert,
  Inbox
} from 'lucide-react';
import { DocumentSubmission } from '../types/dashboard';
import { DocumentModal } from './DocumentModal';

interface SubmissionsTabProps {
  submissions: DocumentSubmission[];
}

export const SubmissionsTab: React.FC<SubmissionsTabProps> = ({ submissions = [] }) => {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'approved' | 'rejected'>('all');
  const [selectedSub, setSelectedSub] = useState<DocumentSubmission | null>(null);

  const filteredSubmissions = submissions.filter((sub) => {
    if (!sub) return false;
    const phone = sub.phone || '';
    const docType = sub.document_type || '';
    const matchesSearch =
      phone.toLowerCase().includes(search.toLowerCase()) ||
      docType.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filter === 'all' ||
      (filter === 'approved' && sub.is_valid) ||
      (filter === 'rejected' && !sub.is_valid);

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Header */}
      <div className="card p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <ScanEye className="w-5 h-5 text-slate-700" />
            <span>Gemini Vision Document Audits</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Multimodal visual verification and structured OCR extraction powered by <code className="font-mono text-slate-700 font-medium">Gemini 3.7 Flash</code>.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
            <input
              type="text"
              placeholder="Search phone or document..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field pl-8 w-48 text-xs"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center bg-slate-100 border border-slate-200 rounded-lg p-0.5 text-xs">
            <button
              onClick={() => setFilter('all')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                filter === 'all' ? 'bg-white text-slate-900 shadow-2xs font-semibold' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              All ({submissions.length})
            </button>
            <button
              onClick={() => setFilter('approved')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                filter === 'approved' ? 'bg-white text-emerald-700 shadow-2xs font-semibold' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Approved
            </button>
            <button
              onClick={() => setFilter('rejected')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                filter === 'rejected' ? 'bg-white text-rose-700 shadow-2xs font-semibold' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Rejected
            </button>
          </div>
        </div>
      </div>

      {/* Submissions Feed Cards */}
      {filteredSubmissions.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSubmissions.map((sub, idx) => {
            const fields = sub.extracted_fields || {};
            const issues = sub.issues || [];
            const docTypeName = (sub.document_type || 'Document').replace(/_/g, ' ');

            return (
              <div
                key={sub.id || idx}
                className="card p-4 flex flex-col justify-between hover:border-slate-300 transition-all"
              >
                <div>
                  
                  {/* Submission Header */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <span className="text-[11px] font-mono text-slate-500">{sub.phone || 'WhatsApp Client'}</span>
                      <h3 className="font-semibold text-sm text-slate-900 capitalize mt-0.5">
                        {docTypeName}
                      </h3>
                    </div>

                    {sub.is_valid ? (
                      <span className="badge-emerald">
                        <CheckCircle2 className="w-3 h-3" />
                        Approved
                      </span>
                    ) : (
                      <span className="badge-rose">
                        <AlertCircle className="w-3 h-3" />
                        Rejected
                      </span>
                    )}
                  </div>

                  {/* Rejection Details if rejected */}
                  {!sub.is_valid && (
                    <div className="mb-3 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800">
                      <div className="flex items-center gap-1 font-semibold text-rose-900 mb-1 text-[11px]">
                        <ShieldAlert className="w-3.5 h-3.5" />
                        <span>Rejection Reasons</span>
                      </div>
                      {issues.length > 0 ? (
                        <ul className="space-y-0.5 pl-3.5 list-disc text-[11px] text-rose-700">
                          {issues.map((issue, i) => (
                            <li key={i}>{issue}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-[11px] text-rose-700">Document failed eligibility or image quality criteria.</p>
                      )}
                    </div>
                  )}

                  {/* Extracted Fields Summary */}
                  {Object.keys(fields).length > 0 && (
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 mb-3 space-y-1">
                      <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                        Extracted Verification Details
                      </p>
                      {Object.entries(fields).slice(0, 4).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-xs">
                          <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                          <span className="text-slate-800 font-medium font-mono text-[11px] truncate max-w-[140px]">
                            {String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                </div>

                {/* Card Action */}
                <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400 font-mono">
                    {sub.created_at ? new Date(sub.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent'}
                  </span>

                  <button
                    onClick={() => setSelectedSub(sub)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>Inspect</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card p-10 text-center border-dashed">
          <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center mx-auto mb-3">
            <Inbox className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-semibold text-slate-900">Documents will appear here</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Verified documents uploaded by clients over WhatsApp will appear here automatically.
          </p>
        </div>
      )}

      {/* Selected Submission Inspector Modal */}
      {selectedSub && (
        <DocumentModal
          isOpen={true}
          onClose={() => setSelectedSub(null)}
          title={`Document Submission — ${(selectedSub.document_type || '').replace(/_/g, ' ')}`}
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
