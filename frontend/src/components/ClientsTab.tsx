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
    return (
      (client.name?.toLowerCase() || '').includes(search.toLowerCase()) ||
      client.phone.includes(search) ||
      (client.service_type?.toLowerCase() || '').includes(search.toLowerCase())
    );
  });

  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'complete':
        return (
          <span className="badge-emerald">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Complete
          </span>
        );
      case 'in_progress':
        return (
          <span className="badge-brand">
            <Clock className="w-3.5 h-3.5" />
            In Progress
          </span>
        );
      default:
        return (
          <span className="badge-amber">
            <Clock className="w-3.5 h-3.5" />
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
      <div className="glass-card p-6 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-emerald-400" />
            <span>Client Onboarding & Document Checklists</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time checklist progression synchronized with Firestore <code className="text-brand-300">clients/{'{phone}'}/documents</code> subcollections.
          </p>
        </div>

        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search client name or phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="glass-input pl-9 w-64 text-xs"
          />
        </div>
      </div>

      {/* Clients Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredClients.length > 0 ? (
          filteredClients.map((client, idx) => {
            const docs = client.documents || [];
            const validatedDocs = docs.filter((d) => d.status === 'validated').length;
            const totalDocs = docs.length || 3;
            const progressPercent = totalDocs > 0 ? Math.round((validatedDocs / totalDocs) * 100) : 0;

            return (
              <div key={client.id || idx} className="glass-card p-6 border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition-all duration-200">
                <div>
                  
                  {/* Client Card Header */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div>
                      <h3 className="font-bold text-base text-slate-100">{client.name || 'Client Intake'}</h3>
                      <p className="text-xs font-mono text-slate-400 mt-0.5">{client.phone}</p>
                    </div>
                    {getStatusBadge(client.onboarding_status)}
                  </div>

                  {/* Service Track Tag */}
                  <div className="mb-4">
                    <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-slate-950 text-slate-300 border border-slate-800">
                      {client.service_type || 'sg_company_registration'}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-5">
                    <div className="flex justify-between text-xs mb-1.5 font-medium">
                      <span className="text-slate-400">Verification Progress</span>
                      <span className="text-emerald-400 font-mono">{validatedDocs} / {totalDocs} ({progressPercent}%)</span>
                    </div>
                    <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className="bg-gradient-to-r from-brand-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                        style={{ width: `${progressPercent}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Document Checklist Items */}
                  <div className="space-y-2 mb-4">
                    <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Required Documents</p>
                    {docs.length > 0 ? (
                      docs.map((doc, docIdx) => (
                        <div
                          key={docIdx}
                          className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="w-3.5 h-3.5 text-slate-400" />
                            <span className="text-slate-200 capitalize font-medium">
                              {doc.doc_type.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
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
                                className="p-1 rounded-lg text-slate-400 hover:text-brand-300 hover:bg-slate-800 transition-colors"
                                title="View Document File"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-500 italic p-3 bg-slate-950/30 rounded-xl border border-slate-800/50">
                        Checklist initialization pending first WhatsApp document prompt.
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Last sync: Real-time</span>
                  <a
                    href={`https://wa.me/${client.phone.replace(/[^0-9]/g, '')}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-400 hover:text-brand-300 flex items-center gap-1 font-medium"
                  >
                    <span>WhatsApp</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            );
          })
        ) : (
          <div className="col-span-full glass-card p-12 text-center text-slate-500">
            <ShieldCheck className="w-12 h-12 mx-auto mb-3 opacity-40 text-slate-400" />
            <p className="text-sm font-medium text-slate-300">No active onboarding clients found.</p>
            <p className="text-xs text-slate-500 mt-1">Clients will appear automatically as prospects begin onboarding over WhatsApp.</p>
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
