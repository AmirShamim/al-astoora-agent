import React, { useState } from 'react';
import { 
  FileCheck2, 
  Search, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  FileText, 
  ExternalLink, 
  Eye,
  ShieldCheck
} from 'lucide-react';
import { ClientProfile, DocumentItem } from '../types/dashboard';
import { DocumentModal } from './DocumentModal';

interface ClientsTabProps {
  clients: ClientProfile[];
}

export const ClientsTab: React.FC<ClientsTabProps> = ({ clients }) => {
  const [search, setSearch] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<{
    title: string;
    url?: string;
    docType?: string;
    isValid?: boolean;
  } | null>(null);

  const filteredClients = clients.filter((client) => {
    if (!client) return false;
    const name = client.name || '';
    const phone = client.phone || '';
    const serviceType = client.service_type || '';
    return (
      name.toLowerCase().includes(search.toLowerCase()) ||
      phone.includes(search) ||
      serviceType.toLowerCase().includes(search.toLowerCase())
    );
  });

  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'complete':
        return (
          <span className="badge-emerald">
            <CheckCircle2 className="w-3 h-3" />
            Complete
          </span>
        );
      case 'in_progress':
        return (
          <span className="badge-brand">
            <Clock className="w-3 h-3" />
            In Progress
          </span>
        );
      default:
        return (
          <span className="badge-amber">
            <Clock className="w-3 h-3" />
            Pending Intake
          </span>
        );
    }
  };

  const getDocStatusPill = (doc: DocumentItem) => {
    switch (doc.status?.toLowerCase()) {
      case 'validated':
        return (
          <span className="badge-emerald text-[11px] py-0.5">
            <CheckCircle2 className="w-3 h-3" /> Validated
          </span>
        );
      case 'submitted':
        return (
          <span className="badge-brand text-[11px] py-0.5">
            <Clock className="w-3 h-3" /> Under Review
          </span>
        );
      case 'rejected':
        return (
          <span className="badge-rose text-[11px] py-0.5">
            <AlertCircle className="w-3 h-3" /> Needs Re-upload
          </span>
        );
      default:
        return (
          <span className="badge-slate text-[11px] py-0.5">
            <Clock className="w-3 h-3" /> Awaiting Upload
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Top Header */}
      <div className="card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-slate-700" />
            <span>Client Onboarding & Checklists</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Checklist progression synchronized with Firestore <code className="font-mono text-slate-700">clients/{'{phone}'}/documents</code>.
          </p>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
          <input
            type="text"
            placeholder="Search client name or phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field pl-8 w-56 text-xs"
          />
        </div>
      </div>

      {/* Clients Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredClients.length > 0 ? (
          filteredClients.map((client, idx) => {
            const docs = client.documents || [];
            const validatedDocs = docs.filter((d) => d.status === 'validated').length;
            const totalDocs = docs.length || 3;
            const progressPercent = totalDocs > 0 ? Math.round((validatedDocs / totalDocs) * 100) : 0;

            return (
              <div key={client.id || idx} className="card p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
                <div>
                  
                  {/* Client Card Header */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <h3 className="font-semibold text-sm text-slate-900">{client.name || 'Client Intake'}</h3>
                      <p className="text-xs font-mono text-slate-500">{client.phone}</p>
                    </div>
                    {getStatusBadge(client.onboarding_status)}
                  </div>

                  {/* Service Track Tag */}
                  <div className="mb-3">
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                      {client.service_type || 'client_onboarding'}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-4">
                    <div className="flex justify-between text-xs mb-1 font-medium">
                      <span className="text-slate-500">Document Verification</span>
                      <span className="text-slate-900 font-mono text-[11px]">{validatedDocs} / {totalDocs} ({progressPercent}%)</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden border border-slate-200">
                      <div
                        className="bg-slate-900 h-full rounded-full transition-all duration-300"
                        style={{ width: `${progressPercent}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Document Checklist Items */}
                  <div className="space-y-1.5 mb-3">
                    <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Required Documents</p>
                    {docs.length > 0 ? (
                      docs.map((doc, docIdx) => (
                        <div
                          key={docIdx}
                          className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs"
                        >
                          <div className="flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5 text-slate-400" />
                            <span className="text-slate-800 capitalize font-medium text-[11px]">
                              {(doc.doc_type || '').replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {getDocStatusPill(doc)}
                            {doc.signed_url && (
                              <button
                                onClick={() =>
                                  setSelectedDoc({
                                    title: `${client.name || client.phone} — ${doc.doc_type}`,
                                    url: doc.signed_url,
                                    docType: doc.doc_type,
                                    isValid: doc.status === 'validated',
                                  })
                                }
                                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
                                title="View Document File"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-400 italic p-2 bg-slate-50 rounded-lg border border-slate-200">
                        Checklist initialization pending first WhatsApp prompt.
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Synced in real-time</span>
                  <a
                    href={`https://wa.me/${(client.phone || '').replace(/[^0-9]/g, '')}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-700 hover:text-slate-900 flex items-center gap-1 font-medium"
                  >
                    <span>WhatsApp</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            );
          })
        ) : (
          <div className="col-span-full card p-10 text-center text-slate-500">
            <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-slate-400" />
            <p className="text-sm font-medium text-slate-700">No active onboarding clients found.</p>
            <p className="text-xs text-slate-400 mt-0.5">Clients will appear automatically as prospects start onboarding on WhatsApp.</p>
          </div>
        )}
      </div>

      {/* Document Inspector Modal */}
      {selectedDoc && (
        <DocumentModal
          isOpen={true}
          onClose={() => setSelectedDoc(null)}
          title={selectedDoc.title}
          url={selectedDoc.url}
          docType={selectedDoc.docType}
          isValid={selectedDoc.isValid}
        />
      )}

    </div>
  );
};
