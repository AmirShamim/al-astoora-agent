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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in">
      <div className="relative w-full max-w-4xl bg-white border border-slate-200 rounded-xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-slate-200 text-slate-700">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
              <p className="text-xs text-slate-500 font-mono">{docType || 'Document Inspection'}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {url && (
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition-colors shadow-2xs"
              >
                <ExternalLink className="w-3 h-3" />
                <span>Open File</span>
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Content Split View */}
        <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-slate-200">
          
          {/* Document Preview Pane */}
          <div className="lg:col-span-7 p-5 flex flex-col items-center justify-center bg-slate-50/50 min-h-[320px]">
            {url ? (
              isPdf ? (
                <div className="w-full h-full min-h-[360px] flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-200 rounded-lg bg-white">
                  <FileText className="w-12 h-12 text-slate-400 mb-2" />
                  <p className="text-sm font-semibold text-slate-800">PDF Document</p>
                  <p className="text-xs text-slate-500 mt-0.5 max-w-sm">
                    Secure GCS signed PDF stream. Click below to view in browser.
                  </p>
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-colors shadow-2xs"
                  >
                    <Download className="w-3.5 h-3.5" /> View / Download PDF
                  </a>
                </div>
              ) : (
                <div className="relative group max-h-[440px] overflow-hidden rounded-lg border border-slate-200 shadow-2xs bg-white flex items-center justify-center p-2">
                  <img
                    src={url}
                    alt={title}
                    className="max-h-[420px] w-auto object-contain rounded"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                </div>
              )
            ) : (
              <div className="text-center p-6 text-slate-400">
                <FileText className="w-10 h-10 mx-auto mb-1.5 opacity-50" />
                <p className="text-xs font-medium text-slate-600">Sample inspection record</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Preview URL is populated when live files are received from WhatsApp.</p>
              </div>
            )}
          </div>

          {/* Validation & Extracted Data Pane */}
          <div className="lg:col-span-5 p-5 bg-white overflow-y-auto">
            <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Gemini Vision Verification
            </h4>

            {/* Validation Badge */}
            {isValid !== undefined && (
              <div
                className={`p-3 rounded-lg mb-3 flex items-start gap-2 text-xs ${
                  isValid
                    ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                    : 'bg-rose-50 border border-rose-200 text-rose-800'
                }`}
              >
                {isValid ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
                )}
                <div>
                  <p className="font-semibold">{isValid ? 'Approved (Passed Vision Audit)' : 'Rejected (Defects Detected)'}</p>
                  <p className="opacity-90 mt-0.5 text-[11px]">
                    {isValid
                      ? 'Meets agency eligibility criteria and clarity standards.'
                      : 'Quality or compliance defects detected during AI vision audit.'}
                  </p>
                </div>
              </div>
            )}

            {/* Issues List */}
            {issues && issues.length > 0 && (
              <div className="mb-3">
                <p className="text-xs font-semibold text-rose-800 mb-1.5">Detected Issues:</p>
                <div className="space-y-1">
                  {issues.map((issue, idx) => (
                    <div
                      key={idx}
                      className="px-2.5 py-1 rounded bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-1.5"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                      <span className="text-[11px]">{issue}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extracted Structured Fields */}
            <div>
              <p className="text-xs font-semibold text-slate-700 mb-1.5">Extracted Fields:</p>
              {extractedFields && Object.keys(extractedFields).length > 0 ? (
                <div className="space-y-1.5 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  {Object.entries(extractedFields).map(([key, val]) => (
                    <div key={key} className="flex flex-col text-xs pb-1 border-b border-slate-200 last:border-0 last:pb-0">
                      <span className="text-slate-500 font-mono text-[10px] uppercase">{key.replace(/_/g, ' ')}:</span>
                      <span className="text-slate-800 font-medium text-xs break-words">
                        {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  No OCR fields extracted.
                </p>
              )}
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-colors shadow-2xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
