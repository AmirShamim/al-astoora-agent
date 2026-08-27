import React, { useState } from 'react';
import { Search, Filter, MessageCircle, UserPlus, ArrowUpRight } from 'lucide-react';
import { Lead } from '../types/dashboard';

interface LeadsTabProps {
  leads: Lead[];
}

export const LeadsTab: React.FC<LeadsTabProps> = ({ leads }) => {
  const [search, setSearch] = useState('');
  const [interestFilter, setInterestFilter] = useState('all');

  const filteredLeads = leads.filter((lead) => {
    const matchesSearch =
      (lead.name?.toLowerCase() || '').includes(search.toLowerCase()) ||
      lead.phone.includes(search) ||
      (lead.interest?.toLowerCase() || '').includes(search.toLowerCase());

    const matchesFilter =
      interestFilter === 'all' ||
      (lead.interest?.toLowerCase() || '').includes(interestFilter.toLowerCase());

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Top Header & Search Bar */}
      <div className="glass-card p-6 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-brand-400" />
            <span>Captured Lead Pipeline (CRM)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Prospects captured silently during WhatsApp conversations via Gemini <code className="text-brand-300">capture_lead</code> tool.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search name, phone, interest..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="glass-input pl-9 w-64 text-xs"
            />
          </div>

          {/* Interest Filter */}
          <div className="flex items-center gap-1.5 bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={interestFilter}
              onChange={(e) => setInterestFilter(e.target.value)}
              className="bg-transparent border-0 text-xs text-slate-200 outline-none cursor-pointer"
            >
              <option value="all" className="bg-slate-900">All Interests</option>
              <option value="corporate secretarial" className="bg-slate-900">Corp Sec</option>
              <option value="document" className="bg-slate-900">Document Engine</option>
              <option value="accounting" className="bg-slate-900">Accounting / Tax</option>
            </select>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="glass-card overflow-hidden border border-slate-800 shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-6 py-3.5">Prospect Name</th>
                <th className="px-6 py-3.5">WhatsApp Phone</th>
                <th className="px-6 py-3.5">Expressed Interest</th>
                <th className="px-6 py-3.5">Lead Status</th>
                <th className="px-6 py-3.5">Captured Date</th>
                <th className="px-6 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredLeads.length > 0 ? (
                filteredLeads.map((lead, idx) => (
                  <tr key={lead.id || idx} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-100 flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-brand-500/20 text-brand-300 flex items-center justify-center font-bold text-xs">
                        {(lead.name || 'P')[0].toUpperCase()}
                      </div>
                      <span>{lead.name || 'Anonymous Prospect'}</span>
                    </td>
                    <td className="px-6 py-4 font-mono text-slate-300">
                      {lead.phone}
                    </td>
                    <td className="px-6 py-4">
                      <span className="badge-brand">
                        {lead.interest || 'General Ingestion'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="badge-emerald">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        {lead.status || 'Active Qualified'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                      {lead.created_at ? new Date(lead.created_at).toLocaleString() : 'Recent'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <a
                        href={`https://wa.me/${lead.phone.replace(/[^0-9]/g, '')}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-all"
                      >
                        <MessageCircle className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Chat</span>
                        <ArrowUpRight className="w-3 h-3 opacity-60" />
                      </a>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    No leads match the filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
