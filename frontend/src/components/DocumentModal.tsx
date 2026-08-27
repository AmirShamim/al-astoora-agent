import React from 'react';
import { X, ExternalLink, Download, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

interface DocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  url?: string;
  extractedFields?: Record<string, any>;
  isValid?: boolean;
  issues?: string[];
  docType?: string;
}

export const DocumentModal: React.FC<DocumentModalProps> = ({
  isOpen,
  onClose,
  title,
  url,
  extractedFields,
  isValid,
  issues,
  docType,
}) => {
  if (!isOpen) return null;

  const isPdf = url?.toLowerCase().includes('.pdf');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-brand-500/20 text-brand-300">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-100">{title}</h3>
              <p className="text-xs text-slate-400 font-mono">{docType || 'Document Inspection'}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {url && (
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Open Link</span>
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Content Split View */}
        <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-slate-800">
          
          {/* Document Preview Pane */}
          <div className="lg:col-span-7 p-6 flex flex-col items-center justify-center bg-slate-950/40 min-h-[350px]">
            {url ? (
              isPdf ? (
                <div className="w-full h-full min-h-[420px] flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl bg-slate-900/40">
                  <FileText className="w-16 h-16 text-brand-400 mb-3" />
                  <p className="text-sm font-medium text-slate-200">PDF Document Stream</p>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm">
                    Secure GCS signed PDF stream. Click below to view in browser PDF reader.
                  </p>
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-lg shadow-brand-500/20 transition-all"
                  >
                    <Download className="w-4 h-4" /> View / Download PDF
                  </a>
                </div>
              ) : (
                <div className="relative group max-h-[480px] overflow-hidden rounded-xl border border-slate-800 shadow-inner bg-slate-950 flex items-center justify-center">
                  <img
                    src={url}
                    alt={title}
                    className="max-h-[460px] w-auto object-contain transition-transform duration-300 group-hover:scale-105"
                    onError={(e) => {
                      // Fallback if signed url expired or image failed
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                </div>
              )
            ) : (
              <div className="text-center p-8 text-slate-500">
                <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No preview URL available for this record.</p>
              </div>
            )}
          </div>

          {/* Validation & Extracted Data Pane */}
          <div className="lg:col-span-5 p-6 bg-slate-900/60 overflow-y-auto">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
              Gemini Vision Analysis
            </h4>

            {/* Validation Badge */}
            {isValid !== undefined && (
              <div
                className={`p-3 rounded-xl mb-4 flex items-start gap-2.5 text-xs ${
                  isValid
                    ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
                }`}
              >
                {isValid ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                )}
                <div>
                  <p className="font-semibold">{isValid ? 'Validated Successfully' : 'Validation Failed'}</p>
                  <p className="opacity-80 mt-0.5">
                    {isValid
                      ? 'Meets agency eligibility criteria and clarity standards.'
                      : 'Quality or requirement issues detected during AI vision scan.'}
                  </p>
                </div>
              </div>
            )}

            {/* Issues List */}
            {issues && issues.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-medium text-rose-400 mb-2">Detected Issues:</p>
                <div className="space-y-1.5">
                  {issues.map((issue, idx) => (
                    <div
                      key={idx}
                      className="px-2.5 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                      <span>{issue}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extracted Structured Fields */}
            <div>
              <p className="text-xs font-medium text-slate-300 mb-2">Extracted Fields:</p>
              {extractedFields && Object.keys(extractedFields).length > 0 ? (
                <div className="space-y-2 bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
                  {Object.entries(extractedFields).map(([key, val]) => (
                    <div key={key} className="flex flex-col text-xs pb-1.5 border-b border-slate-800/50 last:border-0 last:pb-0">
                      <span className="text-slate-400 font-mono text-[11px] capitalize">{key.replace(/_/g, ' ')}:</span>
                      <span className="text-slate-100 font-medium mt-0.5 break-words">
                        {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic bg-slate-950/40 p-3 rounded-xl border border-slate-800/50">
                  No structured fields extracted yet.
                </p>
              )}
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
