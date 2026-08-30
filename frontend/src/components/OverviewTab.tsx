import React from 'react';
import { 
  Users, 
  FileCheck, 
  ScanEye, 
  CalendarCheck, 
  Clock, 
  ShieldCheck,
  ArrowRight,
  Activity
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
    <div className="space-y-6 animate-fade-in">
      
      {/* Clean Minimal Hero Header */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700 mb-2 border border-slate-200">
            <Activity className="w-3.5 h-3.5 text-emerald-600" />
            <span>Autonomous Service Active</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Al Astoora Agency Intelligence Hub
          </h2>
          <p className="text-slate-500 text-xs sm:text-sm mt-1 leading-relaxed">
            WhatsApp-native document intake and client verification powered by Gemini 3.7 Flash. Managing lead qualification, automated booking, and multimodal document verification.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setActiveTab('clients')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-colors shadow-2xs"
          >
            <span>Onboarding Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setActiveTab('transcripts')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium transition-colors shadow-2xs"
          >
            <span>Conversation Logs</span>
          </button>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Captured Leads"
          value={stats.total_leads}
          subtitle="Real-time prospects"
          icon={Users}
          trend="100% automated"
        />
        <StatsCard
          title="Active Clients"
          value={stats.total_clients}
          subtitle={`${stats.completed_clients} completed (${completionRate}%)`}
          icon={FileCheck}
          trend={`${stats.in_progress_clients} in progress`}
        />
        <StatsCard
          title="Vision Validations"
          value={stats.total_submissions}
          subtitle={`${validationRate}% pass rate`}
          icon={ScanEye}
          trend={`${stats.validated_submissions} verified`}
        />
        <StatsCard
          title="Discovery Calls"
          value={stats.total_bookings}
          subtitle={`${stats.confirmed_bookings} confirmed`}
          icon={CalendarCheck}
          trend="Conflict protected"
        />
      </div>

      {/* Client Onboarding Funnel */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-slate-700" />
            <span>Client Conversion Pipeline</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">Real-time</span>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Tracking the end-to-end journey from initial WhatsApp message to verified document completion:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-[11px] text-slate-500 font-medium block">1. Prospect Contact</span>
            <span className="text-lg font-bold text-slate-900 my-0.5 block">{stats.total_leads} Leads</span>
            <span className="text-[11px] text-slate-400">Captured silently</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-[11px] text-slate-500 font-medium block">2. Discovery Call</span>
            <span className="text-lg font-bold text-slate-900 my-0.5 block">{stats.total_bookings} Bookings</span>
            <span className="text-[11px] text-slate-400">Interactive slot reserved</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-[11px] text-slate-500 font-medium block">3. Document Intake</span>
            <span className="text-lg font-bold text-slate-900 my-0.5 block">{stats.total_clients} Clients</span>
            <span className="text-[11px] text-slate-400">Checklist in progress</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-[11px] text-slate-500 font-medium block">4. Verified Complete</span>
            <span className="text-lg font-bold text-slate-900 my-0.5 block">{stats.completed_clients} Verified</span>
            <span className="text-[11px] text-slate-400">Gemini Vision approved</span>
          </div>
        </div>
      </div>

      {/* Two-Column Grid: Automation Tracks + Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left: Configured Service Tracks */}
        <div className="lg:col-span-7 card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-slate-700" />
                <span>Configured Intake Checklists</span>
              </h3>
              <span className="badge-slate text-[11px]">Firestore Schema</span>
            </div>

            <p className="text-xs text-slate-500 mb-4">
              Pre-configured service workflows with multimodal document verification rules:
            </p>

            <div className="space-y-3">
              {/* Track 1 */}
              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between text-xs font-medium mb-1.5">
                  <span className="text-slate-900 font-semibold">Singapore Company Registration</span>
                  <span className="badge-brand">3 Documents</span>
                </div>
                <div className="text-xs text-slate-500 mb-2">
                  <span>Required: Passport, Proof of Address, Director Resolution</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-slate-900 h-full rounded-full w-4/5"></div>
                </div>
              </div>

              {/* Track 2 */}
              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between text-xs font-medium mb-1.5">
                  <span className="text-slate-900 font-semibold">UAE Corporate Onboarding</span>
                  <span className="badge-emerald">3 Documents</span>
                </div>
                <div className="text-xs text-slate-500 mb-2">
                  <span>Required: Passport, Trade License, MOA Document</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-600 h-full rounded-full w-3/5"></div>
                </div>
              </div>

              {/* Track 3 */}
              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between text-xs font-medium mb-1">
                  <span className="text-slate-900 font-semibold">Discovery Call Scheduling</span>
                  <span className="badge-amber">Direct Interactive</span>
                </div>
                <div className="text-xs text-slate-500">
                  <span>Interactive slot reservation with double-booking collision protection.</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Gemini 3.7 Vision Engine
            </span>
            <span className="font-mono text-[11px]">Region: asia-south1</span>
          </div>
        </div>

        {/* Right: Recent Stream Activity */}
        <div className="lg:col-span-5 card p-5 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-700" />
              <span>Recent Pipeline Activity</span>
            </h3>
            <span className="badge-slate text-[11px]">Live</span>
          </div>

          <div className="space-y-2.5 flex-1 overflow-y-auto max-h-[340px] pr-1">
            {leads.slice(0, 3).map((lead, i) => (
              <div key={`lead-${i}`} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                <div className="flex items-center justify-between font-medium">
                  <span className="text-slate-900 font-semibold">Lead Qualified</span>
                  <span className="text-slate-400 font-mono text-[11px]">
                    {lead.created_at ? new Date(lead.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent'}
                  </span>
                </div>
                <p className="text-slate-700 mt-0.5">{lead.name || 'New Prospect'} ({lead.phone})</p>
                <p className="text-slate-500 text-[11px]">Interest: {lead.interest || 'Corporate Services'}</p>
              </div>
            ))}

            {bookings.slice(0, 2).map((booking, i) => (
              <div key={`booking-${i}`} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                <div className="flex items-center justify-between font-medium">
                  <span className="text-amber-700 font-semibold">Consultation Booked</span>
                  <span className="text-slate-400 font-mono text-[11px]">{booking.time}</span>
                </div>
                <p className="text-slate-700 mt-0.5">{booking.name || 'Client'} ({booking.phone})</p>
                <p className="text-slate-500 text-[11px]">Date: {booking.date} at {booking.time}</p>
              </div>
            ))}

            {clients.slice(0, 2).map((client, i) => (
              <div key={`client-${i}`} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                <div className="flex items-center justify-between font-medium">
                  <span className="text-emerald-700 font-semibold">Onboarding Updated</span>
                  <span className="text-slate-400 font-mono text-[11px] capitalize">{client.onboarding_status}</span>
                </div>
                <p className="text-slate-700 mt-0.5">{client.name || client.phone}</p>
                <p className="text-slate-500 text-[11px]">Track: {client.service_type || 'sg_company_registration'}</p>
              </div>
            ))}
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100">
            <button
              onClick={() => setActiveTab('leads')}
              className="w-full py-1.5 text-center text-xs font-medium text-slate-700 hover:text-slate-900 transition-colors"
            >
              View all pipeline records →
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};
