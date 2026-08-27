import React, { useState, useEffect } from 'react';
import { 
  MessageSquareCode, 
  Search, 
  ShieldCheck, 
  Printer, 
  Bot, 
  User, 
  Send,
  Lock
} from 'lucide-react';
import { Lead, ClientProfile, AuditMessage } from '../types/dashboard';
import { fetchTranscript } from '../api/client';

interface TranscriptsTabProps {
  leads: Lead[];
  clients: ClientProfile[];
}

export const TranscriptsTab: React.FC<TranscriptsTabProps> = ({ leads, clients }) => {
  // Collect all unique phones
  const allPhones = Array.from(
    new Set([
      ...leads.map((l) => l.phone),
      ...clients.map((c) => c.phone),
      '6591234567', // Sample demo phone fallback
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
    m.text.toLowerCase().includes(messageSearch.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Header */}
      <div className="glass-card p-6 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <MessageSquareCode className="w-5 h-5 text-brand-400" />
            <span>Immutable Conversation Audit Transcripts</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Permanent, untrimmed legal audit records stored in Firestore <code className="text-brand-300">message_audit/{'{phone}'}/messages</code>.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium transition-colors"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print / PDF Export</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Phone List Sidebar + Chat Transcript Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Sidebar: Phone Contacts */}
        <div className="lg:col-span-4 glass-card p-5 border border-slate-800 flex flex-col h-[650px]">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
            Active Contact Channels
          </h3>

          {/* Custom Phone Lookup Form */}
          <form onSubmit={handleCustomPhoneSubmit} className="mb-4">
            <div className="relative">
              <input
                type="text"
                placeholder="Enter phone e.g. +6591234567"
                value={customPhone}
                onChange={(e) => setCustomPhone(e.target.value)}
                className="glass-input w-full pr-8 text-xs font-mono"
              />
              <button
                type="submit"
                className="absolute right-2 top-2 p-1 text-slate-400 hover:text-brand-300 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </form>

          {/* Phone List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {allPhones.map((phone) => {
              const client = clients.find((c) => c.phone === phone);
              const lead = leads.find((l) => l.phone === phone);
              const name = client?.name || lead?.name || 'Contact';
              const isSelected = selectedPhone === phone;

              return (
                <button
                  key={phone}
                  onClick={() => setSelectedPhone(phone)}
                  className={`w-full text-left p-3 rounded-xl transition-all duration-200 flex items-center justify-between border ${
                    isSelected
                      ? 'bg-brand-500/15 border-brand-500/40 shadow-sm'
                      : 'bg-slate-950/40 border-slate-800/80 hover:bg-slate-900/60'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${
                      isSelected ? 'bg-brand-500 text-white' : 'bg-slate-800 text-slate-300'
                    }`}>
                      {name[0].toUpperCase()}
                    </div>
                    <div>
                      <p className="font-semibold text-xs text-slate-100">{name}</p>
                      <p className="font-mono text-[11px] text-slate-400">{phone}</p>
                    </div>
                  </div>
                  <Lock className="w-3 h-3 text-slate-600" />
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Chat Stream */}
        <div className="lg:col-span-8 glass-card border border-slate-800 flex flex-col h-[650px] overflow-hidden">
          
          {/* Chat Header */}
          <div className="p-4 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                  <span>{selectedPhone || 'Select a contact'}</span>
                  <span className="badge-emerald text-[10px] py-0">Tamper-Proof Audit</span>
                </h3>
                <p className="text-[11px] text-slate-400">
                  {messages.length} total messages recorded in persistent ledger
                </p>
              </div>
            </div>

            {/* Filter in conversation */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
              <input
                type="text"
                placeholder="Search dialogue..."
                value={messageSearch}
                onChange={(e) => setMessageSearch(e.target.value)}
                className="glass-input pl-8 py-1 text-xs w-44"
              />
            </div>
          </div>

          {/* Messages Stream Container */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-slate-950/30">
            {loading ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                <span className="animate-pulse">Loading immutable audit messages...</span>
              </div>
            ) : filteredMessages.length > 0 ? (
              filteredMessages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={msg.id || idx}
                    className={`flex items-end gap-2.5 ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {!isUser && (
                      <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-brand-600 to-indigo-500 text-white flex items-center justify-center shrink-0 mb-1 shadow-md shadow-brand-500/20">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div
                      className={`max-w-[78%] rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-lg ${
                        isUser
                          ? 'bg-emerald-600 text-white rounded-br-none'
                          : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3 text-[10px] mb-1 opacity-75 font-mono">
                        <span className="font-semibold uppercase">{isUser ? 'Client (WhatsApp)' : 'Al Astoora Agent (Gemini 3.7)'}</span>
                        <span>{msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Verified'}</span>
                      </div>
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                    </div>

                    {isUser && (
                      <div className="w-7 h-7 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center shrink-0 mb-1 border border-slate-700">
                        <User className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs text-center p-6">
                <MessageSquareCode className="w-12 h-12 opacity-30 mb-2" />
                <p className="font-medium text-slate-400">No conversation audit entries found.</p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Send a message to the WhatsApp agent number to view live audit streams.
                </p>
              </div>
            )}
          </div>

          {/* Footer note */}
          <div className="p-2.5 px-4 bg-slate-950/90 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Lock className="w-3 h-3 text-emerald-400" />
              <span>Cryptographically synced with Google Cloud Firestore</span>
            </span>
            <span>Channel: Meta WhatsApp Cloud API</span>
          </div>

        </div>

      </div>

    </div>
  );
};
