import React, { useState, useEffect } from 'react';
import { 
  MessageSquareCode, 
  Search, 
  ShieldCheck, 
  Printer, 
  Bot, 
  User, 
  Send
} from 'lucide-react';
import { Lead, ClientProfile, AuditMessage } from '../types/dashboard';
import { fetchTranscript } from '../api/client';

interface TranscriptsTabProps {
  leads: Lead[];
  clients: ClientProfile[];
}

export const TranscriptsTab: React.FC<TranscriptsTabProps> = ({ leads, clients }) => {
  const allPhones = Array.from(
    new Set([
      ...leads.map((l) => l.phone),
      ...clients.map((c) => c.phone),
      '6591234567',
    ])
  ).filter(Boolean);

  const [selectedPhone, setSelectedPhone] = useState<string>(allPhones[0] || '');
  const [customPhone, setCustomPhone] = useState<string>('');
  const [messages, setMessages] = useState<AuditMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [messageSearch, setMessageSearch] = useState('');

  const loadTranscript = async (phone: string) => {
    if (!phone) return;
    setLoading(true);
    try {
      const data = await fetchTranscript(phone);
      setMessages(data.messages || []);
    } catch (err) {
      console.error('Error fetching transcript:', err);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedPhone) {
      loadTranscript(selectedPhone);
    }
  }, [selectedPhone]);

  const handleCustomPhoneSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customPhone.trim()) {
      setSelectedPhone(customPhone.trim());
      setCustomPhone('');
    }
  };

  const filteredMessages = messages.filter((m) =>
    (m.text || '').toLowerCase().includes(messageSearch.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Header */}
      <div className="card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <MessageSquareCode className="w-5 h-5 text-slate-700" />
            <span>Conversation Audit Transcripts</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Untrimmed legal audit records stored in Firestore <code className="font-mono text-slate-700">message_audit/{'{phone}'}/messages</code>.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium transition-colors shadow-2xs"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print / Export</span>
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Sidebar: Phone Contacts */}
        <div className="lg:col-span-4 card p-4 flex flex-col h-[600px]">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Contacts Ledger
          </h3>

          {/* Custom Phone Lookup */}
          <form onSubmit={handleCustomPhoneSubmit} className="mb-3">
            <div className="relative">
              <input
                type="text"
                placeholder="Enter phone e.g. 6591234567"
                value={customPhone}
                onChange={(e) => setCustomPhone(e.target.value)}
                className="input-field w-full pr-8 text-xs font-mono"
              />
              <button
                type="submit"
                className="absolute right-2 top-2 p-0.5 text-slate-400 hover:text-slate-700 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </form>

          {/* Phone List */}
          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {allPhones.map((phone) => {
              const client = clients.find((c) => c.phone === phone);
              const lead = leads.find((l) => l.phone === phone);
              const name = client?.name || lead?.name || 'Contact';
              const isSelected = selectedPhone === phone;

              return (
                <button
                  key={phone}
                  onClick={() => setSelectedPhone(phone)}
                  className={`w-full text-left p-2.5 rounded-lg transition-all flex items-center justify-between border ${
                    isSelected
                      ? 'bg-slate-900 text-white border-slate-900 shadow-2xs'
                      : 'bg-slate-50 border-slate-200 text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
                      isSelected ? 'bg-slate-800 text-white' : 'bg-white text-slate-700 border border-slate-200'
                    }`}>
                      {name[0].toUpperCase()}
                    </div>
                    <div>
                      <p className={`font-medium text-xs ${isSelected ? 'text-white' : 'text-slate-900'}`}>{name}</p>
                      <p className={`font-mono text-[11px] ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>{phone}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Chat Stream */}
        <div className="lg:col-span-8 card flex flex-col h-[600px] overflow-hidden">
          
          {/* Chat Header */}
          <div className="p-3.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-semibold text-xs sm:text-sm text-slate-900 flex items-center gap-2">
                  <span>{selectedPhone || 'Select a contact'}</span>
                  <span className="badge-emerald text-[10px] py-0">Tamper-Proof</span>
                </h3>
                <p className="text-[11px] text-slate-500">
                  {messages.length} immutable messages logged in Firestore
                </p>
              </div>
            </div>

            {/* Search within messages */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
              <input
                type="text"
                placeholder="Search dialogue..."
                value={messageSearch}
                onChange={(e) => setMessageSearch(e.target.value)}
                className="input-field pl-8 py-1 text-xs w-36 sm:w-44"
              />
            </div>
          </div>

          {/* Messages Stream Container */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50/50">
            {loading ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                <span>Loading audit trail...</span>
              </div>
            ) : filteredMessages.length > 0 ? (
              filteredMessages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={msg.id || idx}
                    className={`flex items-end gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {!isUser && (
                      <div className="w-6 h-6 rounded bg-slate-900 text-white flex items-center justify-center shrink-0 mb-1 text-xs">
                        <Bot className="w-3.5 h-3.5" />
                      </div>
                    )}

                    <div
                      className={`max-w-[80%] rounded-xl px-3.5 py-2.5 text-xs leading-relaxed ${
                        isUser
                          ? 'bg-emerald-600 text-white rounded-br-none'
                          : 'bg-white border border-slate-200 text-slate-800 shadow-2xs rounded-bl-none'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 text-[10px] mb-1 opacity-70 font-mono">
                        <span className="font-semibold uppercase">{isUser ? 'Client (WhatsApp)' : 'Al Astoora Agent (Gemini 3.7)'}</span>
                        <span>{msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Logged'}</span>
                      </div>
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                    </div>

                    {isUser && (
                      <div className="w-6 h-6 rounded bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mb-1 text-xs">
                        <User className="w-3.5 h-3.5" />
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-xs text-center p-6">
                <MessageSquareCode className="w-8 h-8 opacity-40 mb-2" />
                <p className="font-medium text-slate-600">No conversation audit records for this number.</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Send a WhatsApp message to initialize live session records.
                </p>
              </div>
            )}
          </div>

          {/* Footer note */}
          <div className="p-2 px-4 bg-white border-t border-slate-200 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Verified audit record</span>
            <span>Channel: WhatsApp Cloud API</span>
          </div>

        </div>

      </div>

    </div>
  );
};
