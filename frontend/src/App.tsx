import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { OverviewTab } from './components/OverviewTab';
import { LeadsTab } from './components/LeadsTab';
import { ClientsTab } from './components/ClientsTab';
import { SubmissionsTab } from './components/SubmissionsTab';
import { BookingsTab } from './components/BookingsTab';
import { TranscriptsTab } from './components/TranscriptsTab';
import { 
  fetchStats, 
  fetchClients, 
  fetchLeads, 
  fetchBookings, 
  fetchSubmissions 
} from './api/client';
import { 
  DashboardStats, 
  ClientProfile, 
  Lead, 
  Booking, 
  DocumentSubmission 
} from './types/dashboard';
import { AlertCircle } from 'lucide-react';

const FALLBACK_STATS: DashboardStats = {
  total_leads: 12,
  total_clients: 8,
  completed_clients: 5,
  in_progress_clients: 3,
  total_submissions: 24,
  validated_submissions: 21,
  rejected_submissions: 3,
  total_bookings: 7,
  confirmed_bookings: 7,
  total_sessions: 15,
};

const FALLBACK_LEADS: Lead[] = [
  {
    id: 'lead-1',
    name: 'Ahmed Khan',
    phone: '971501234567',
    interest: 'Corporate Secretarial',
    status: 'Active Qualified',
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
  },
  {
    id: 'lead-2',
    name: 'Sarah Lim',
    phone: '6591234567',
    interest: 'Singapore Company Registration',
    status: 'Active Qualified',
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
  },
  {
    id: 'lead-3',
    name: 'Marcus Chen',
    phone: '6587654321',
    interest: 'Document Collection Engine',
    status: 'Active Qualified',
    created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
  }
];

const FALLBACK_CLIENTS: ClientProfile[] = [
  {
    id: 'c-1',
    phone: '6591234567',
    name: 'Sarah Lim',
    service_type: 'sg_company_registration',
    onboarding_status: 'in_progress',
    documents: [
      { doc_type: 'passport', status: 'validated', attempts: 1 },
      { doc_type: 'proof_of_address', status: 'validated', attempts: 1 },
      { doc_type: 'director_resolution', status: 'pending', attempts: 0 },
    ],
  },
  {
    id: 'c-2',
    phone: '971501234567',
    name: 'Ahmed Khan',
    service_type: 'uae_corporate_onboarding',
    onboarding_status: 'complete',
    documents: [
      { doc_type: 'passport', status: 'validated', attempts: 1 },
      { doc_type: 'trade_license', status: 'validated', attempts: 1 },
      { doc_type: 'moa_document', status: 'validated', attempts: 1 },
    ],
  }
];

const FALLBACK_BOOKINGS: Booking[] = [
  {
    id: 'b-1',
    name: 'Ahmed Khan',
    phone: '971501234567',
    date: 'Tomorrow',
    time: '12:00 PM',
    status: 'confirmed',
  },
  {
    id: 'b-2',
    name: 'Sarah Lim',
    phone: '6591234567',
    date: 'Friday',
    time: '03:00 PM',
    status: 'confirmed',
  }
];

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [refreshInterval, setRefreshInterval] = useState<number>(30);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [apiOnline, setApiOnline] = useState<boolean>(true);

  const [stats, setStats] = useState<DashboardStats>(FALLBACK_STATS);
  const [clients, setClients] = useState<ClientProfile[]>(FALLBACK_CLIENTS);
  const [leads, setLeads] = useState<Lead[]>(FALLBACK_LEADS);
  const [bookings, setBookings] = useState<Booking[]>(FALLBACK_BOOKINGS);
  const [submissions, setSubmissions] = useState<DocumentSubmission[]>([]);

  const loadAllData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [s, c, l, b, sub] = await Promise.all([
        fetchStats(),
        fetchClients(),
        fetchLeads(),
        fetchBookings(),
        fetchSubmissions(),
      ]);

      setStats(s);
      if (c && c.length > 0) setClients(c);
      if (l && l.length > 0) setLeads(l);
      if (b && b.length > 0) setBookings(b);
      if (sub && sub.length > 0) setSubmissions(sub);
      setApiOnline(true);
    } catch (err) {
      console.warn('Dashboard using cached/demo snapshot (Backend offline or local test mode):', err);
      setApiOnline(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Polling Interval
  useEffect(() => {
    if (refreshInterval <= 0) return;
    const interval = setInterval(() => {
      loadAllData();
    }, refreshInterval * 1000);
    return () => clearInterval(interval);
  }, [refreshInterval, loadAllData]);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col selection:bg-brand-500/30 selection:text-brand-100">
      
      {/* Top Sticky Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isLoading={isLoading}
        onRefresh={loadAllData}
        refreshInterval={refreshInterval}
        setRefreshInterval={setRefreshInterval}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Connection status alert if in standalone demo mode */}
        {!apiOnline && (
          <div className="mb-6 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>Demo Mode Active:</strong> Live backend REST endpoint is currently unreachable. Displaying cached snapshots.
              </span>
            </div>
            <button
              onClick={loadAllData}
              className="px-3 py-1 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 font-semibold text-xs"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Tab Router Switch */}
        {activeTab === 'overview' && (
          <OverviewTab
            stats={stats}
            clients={clients}
            leads={leads}
            bookings={bookings}
            setActiveTab={setActiveTab}
          />
        )}

        {activeTab === 'leads' && <LeadsTab leads={leads} />}

        {activeTab === 'clients' && <ClientsTab clients={clients} />}

        {activeTab === 'submissions' && <SubmissionsTab submissions={submissions} />}

        {activeTab === 'bookings' && <BookingsTab bookings={bookings} />}

        {activeTab === 'transcripts' && <TranscriptsTab leads={leads} clients={clients} />}

      </main>

      {/* Footer */}
      <footer className="w-full border-t border-slate-800/80 bg-slate-950/60 py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
            <span>Al Astoora Document Collector Agent</span>
            <span>•</span>
            <span className="text-slate-400">Google All Things Agentic Hackathon 2026</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
            <span>FastAPI</span>
            <span>•</span>
            <span>Gemini 3.7 Flash</span>
            <span>•</span>
            <span>Google Cloud Run</span>
            <span>•</span>
            <span>Firestore</span>
          </div>
        </div>
      </footer>

    </div>
  );
};
