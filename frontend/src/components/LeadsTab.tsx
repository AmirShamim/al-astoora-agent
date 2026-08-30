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
    if (!lead) return false;
    const name = lead.name || '';
    const phone = lead.phone || '';
    const interest = lead.interest || '';

    const matchesSearch =
      name.toLowerCase().includes(search.toLowerCase()) ||
      phone.includes(search) ||
      interest.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      interestFilter === 'all' ||
      interest.toLowerCase().includes(interestFilter.toLowerCase());

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Header & Controls */}
      <div className="card p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-slate-700" />
            <span>Captured Prospects CRM</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Prospects captured silently during WhatsApp conversations via Gemini <code className="font-mono text-slate-700">capture_lead</code> tool.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
            <input
              type="text"
              placeholder="Search name, phone, interest..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field pl-8 w-52 text-xs"
            />
          </div>

          {/* Interest Filter */}
          <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-700">
            <Filter className="w-3 h-3 text-slate-400" />
            <select
              value={interestFilter}
              onChange={(e) => setInterestFilter(e.target.value)}
              className="bg-transparent border-0 text-xs text-slate-700 outline-none cursor-pointer"
            >
              <option value="all">All Interests</option>
              <option value="corporate">Corp Sec</option>
              <option value="document">Document Engine</option>
              <option value="company">Registration</option>
            </select>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-5 py-3">Prospect Name</th>
                <th className="px-5 py-3">WhatsApp Phone</th>
                <th className="px-5 py-3">Expressed Interest</th>
                <th className="px-5 py-3">Lead Status</th>
                <th className="px-5 py-3">Captured Date</th>
                <th className="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLeads.length > 0 ? (
                filteredLeads.map((lead, idx) => (
                  <tr key={lead.id || idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-5 py-3 font-medium text-slate-900 flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs border border-slate-200">
                        {(lead.name || 'P')[0].toUpperCase()}
                      </div>
                      <span>{lead.name || 'Anonymous Prospect'}</span>
                    </td>
                    <td className="px-5 py-3 font-mono text-slate-600">
                      {lead.phone}
                    </td>
                    <td className="px-5 py-3">
                      <span className="badge-brand">
                        {lead.interest || 'General Ingestion'}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span className="badge-emerald">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        {lead.status || 'Active Qualified'}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-500">
                      {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : 'Recent'}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <a
                        href={`https://wa.me/${(lead.phone || '').replace(/[^0-9]/g, '')}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 text-xs font-medium transition-colors"
                      >
                        <MessageCircle className="w-3 h-3 text-emerald-600" />
                        <span>Chat</span>
                        <ArrowUpRight className="w-2.5 h-2.5 opacity-60" />
                      </a>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400">
                    No prospects match the filter criteria.
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
