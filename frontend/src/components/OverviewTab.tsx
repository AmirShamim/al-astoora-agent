import React from 'react';
import { 
  Users, 
  FileCheck, 
  ScanEye, 
  CalendarCheck, 
  Clock, 
  ShieldCheck,
  ArrowRight,
  Cpu
} from 'lucide-react';
import { DashboardStats, ClientProfile, Lead, Booking } from '../types/dashboard';
import { StatsCard } from './StatsCard';

interface OverviewTabProps {
  stats: DashboardStats;
  clients: ClientProfile[];
  leads: Lead[];
  bookings: Booking[];
  setActiveTab: (tab: string) => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  stats,
  clients,
  leads,
  bookings,
  setActiveTab,
}) => {
  const completionRate = stats.total_clients > 0 
    ? Math.round((stats.completed_clients / stats.total_clients) * 100) 
    : 0;

  const validationRate = stats.total_submissions > 0 
    ? Math.round((stats.validated_submissions / stats.total_submissions) * 100) 
    : 0;

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* Top Hero Banner */}
      <div className="relative overflow-hidden glass-card p-6 sm:p-8 bg-gradient-to-r from-brand-900/30 via-slate-900/60 to-emerald-950/20 border border-brand-500/20">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/20 text-brand-300 border border-brand-500/30 mb-3">
              <Cpu className="w-3.5 h-3.5 text-brand-400" />
              <span>Autonomous Infrastructure Active</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
              Al Astoora WhatsApp Agency Command Center
            </h2>
            <p className="text-slate-400 text-xs sm:text-sm mt-2 leading-relaxed">
              Powered by <span className="text-slate-200 font-semibold">Gemini 3.7 Flash</span> with multimodal vision, Firestore state synchronization, and GCS document vaulting. Managing lead generation, appointment booking, and eligibility verification 24/7.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setActiveTab('clients')}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-lg shadow-brand-500/25 transition-all"
            >
              <span>View Onboarding Queue</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setActiveTab('transcripts')}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium transition-all"
            >
              <span>Live Audit Logs</span>
            </button>
          </div>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <StatsCard
          title="Captured Leads"
          value={stats.total_leads}
          subtitle="Real-time prospect CRM"
          icon={Users}
          color="brand"
          trend="+100% automated"
        />
        <StatsCard
          title="Active Clients"
          value={stats.total_clients}
          subtitle={`${stats.completed_clients} completed (${completionRate}%)`}
          icon={FileCheck}
          color="emerald"
          trend={`${stats.in_progress_clients} in progress`}
        />
        <StatsCard
          title="Vision Validations"
          value={stats.total_submissions}
          subtitle={`${validationRate}% pass rate`}
          icon={ScanEye}
          color="violet"
          trend={`${stats.validated_submissions} verified`}
        />
        <StatsCard
          title="Discovery Calls"
          value={stats.total_bookings}
          subtitle={`${stats.confirmed_bookings} confirmed slots`}
          icon={CalendarCheck}
          color="amber"
          trend="Collision protected"
        />
      </div>

      {/* Client Acquisition & Onboarding Funnel */}
      <div className="glass-card p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-brand-400" />
            <span>Autonomous Client Conversion Funnel</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">End-to-End Pipeline</span>
        </div>
        <p className="text-xs text-slate-400 mb-4">
          Visualizing the real-time transition from WhatsApp outreach inquiry to verified client onboarding:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-center">
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-brand-500/30">
            <span className="text-[11px] text-brand-300 font-medium block">1. Top-of-Funnel</span>
            <span className="text-xl font-extrabold text-white my-1 block">{stats.total_leads} Leads</span>
            <span className="text-[10px] text-slate-400">Captured on first contact</span>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-amber-500/30">
            <span className="text-[11px] text-amber-300 font-medium block">2. Discovery Call</span>
            <span className="text-xl font-extrabold text-white my-1 block">{stats.total_bookings} Bookings</span>
            <span className="text-[10px] text-slate-400">Interactive slot reservation</span>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-emerald-500/30">
            <span className="text-[11px] text-emerald-300 font-medium block">3. Active Onboarding</span>
            <span className="text-xl font-extrabold text-white my-1 block">{stats.total_clients} Clients</span>
            <span className="text-[10px] text-slate-400">Document intake started</span>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-violet-500/30">
            <span className="text-[11px] text-violet-300 font-medium block">4. Verified / Complete</span>
            <span className="text-xl font-extrabold text-white my-1 block">{stats.completed_clients} Verified</span>
            <span className="text-[10px] text-slate-400">Gemini Vision approved</span>
          </div>
        </div>
      </div>

      {/* Middle Two-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left: Service Track Distribution & System Capabilities */}
        <div className="lg:col-span-7 glass-card p-6 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <span>Configured Automation Tracks</span>
              </h3>
              <span className="text-xs text-slate-400 font-mono">Firestore Native</span>
            </div>

            <p className="text-xs text-slate-400 mb-6">
              Autonomous workflows configured with multimodal document verification checklists:
            </p>

            <div className="space-y-4">
              {/* Track 1: Client Onboarding Automation */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                <div className="flex items-center justify-between text-xs font-semibold mb-2">
                  <span className="text-slate-200">Client Onboarding Automation</span>
                  <span className="badge-brand">3 Documents</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                  <span>Checklist: Passport, Proof of Address, Director Resolution</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-gradient-to-r from-brand-500 to-emerald-400 h-full rounded-full w-4/5"></div>
                </div>
              </div>

              {/* Track 2: Financial Compliance Automation */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                <div className="flex items-center justify-between text-xs font-semibold mb-2">
                  <span className="text-slate-200">Financial Compliance Automation</span>
                  <span className="badge-emerald">3 Documents</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                  <span>Checklist: Trade License, Bank Statement, Tax Assessment</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full w-3/5"></div>
                </div>
              </div>

              {/* Track 3: WhatsApp AI & Workflow Automation */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                <div className="flex items-center justify-between text-xs font-semibold mb-2">
                  <span className="text-slate-200">WhatsApp AI & Workflow Scheduling</span>
                  <span className="badge-amber">Direct Discovery</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span>Interactive slot booking, collision protection, and lead CRM sync</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              Gemini 3.7 Vision Live
            </span>
            <span>Cloud Run Service: asia-south1</span>
          </div>
        </div>

        {/* Right: Recent Stream Activity */}
        <div className="lg:col-span-5 glass-card p-6 border border-slate-800 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Clock className="w-5 h-5 text-brand-400" />
              <span>Recent Pipeline Activity</span>
            </h3>
            <span className="badge-slate">Live</span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[380px] pr-1">
            {leads.slice(0, 3).map((lead, i) => (
              <div key={`lead-${i}`} className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 text-xs">
                <div className="flex items-center justify-between font-medium">
                  <span className="text-brand-300 font-semibold">Lead Captured</span>
                  <span className="text-slate-500 font-mono text-[11px]">
                    {lead.created_at ? new Date(lead.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent'}
                  </span>
                </div>
                <p className="text-slate-200 mt-1">{lead.name || 'New Prospect'} ({lead.phone})</p>
                <p className="text-slate-400 text-[11px] mt-0.5">Interest: {lead.interest || 'General'}</p>
              </div>
            ))}

            {bookings.slice(0, 2).map((booking, i) => (
              <div key={`booking-${i}`} className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 text-xs">
                <div className="flex items-center justify-between font-medium">
                  <span className="text-amber-400 font-semibold">Consultation Booked</span>
                  <span className="text-slate-500 font-mono text-[11px]">{booking.time}</span>
                </div>
                <p className="text-slate-200 mt-1">{booking.name || 'Client'} ({booking.phone})</p>
                <p className="text-slate-400 text-[11px] mt-0.5">Date: {booking.date} at {booking.time}</p>
              </div>
            ))}

            {clients.slice(0, 2).map((client, i) => (
              <div key={`client-${i}`} className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 text-xs">
                <div className="flex items-center justify-between font-medium">
                  <span className="text-emerald-400 font-semibold">Onboarding Updated</span>
                  <span className="text-slate-500 font-mono text-[11px]">{client.onboarding_status}</span>
                </div>
                <p className="text-slate-200 mt-1">{client.name || client.phone}</p>
                <p className="text-slate-400 text-[11px] mt-0.5">Track: {client.service_type || 'sg_company_registration'}</p>
              </div>
            ))}

            {leads.length === 0 && bookings.length === 0 && clients.length === 0 && (
              <div className="text-center py-10 text-slate-500 text-xs">
                No recent activity recorded yet. Waiting for WhatsApp events.
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800/80">
            <button
              onClick={() => setActiveTab('leads')}
              className="w-full py-2 text-center text-xs font-medium text-brand-400 hover:text-brand-300 transition-colors"
            >
              View all pipeline records →
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};
