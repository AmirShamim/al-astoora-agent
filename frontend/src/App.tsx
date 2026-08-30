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

const FALLBACK_STATS: DashboardStats = {
  total_leads: 3,
  total_clients: 2,
  completed_clients: 1,
  in_progress_clients: 1,
  total_submissions: 4,
  validated_submissions: 3,
  rejected_submissions: 1,
  total_bookings: 2,
  confirmed_bookings: 2,
  total_sessions: 8,
};

const FALLBACK_LEADS: Lead[] = [
  {
    id: 'lead-1',
    name: 'Ahmed Khan',
    phone: '971501234567',
    interest: 'Corporate Secretarial & Compliance',
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
    interest: 'Document Verification Engine',
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
      { doc_type: 'director_resolution', status: 'rejected', attempts: 1 },
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

const FALLBACK_SUBMISSIONS: DocumentSubmission[] = [
  {
    id: 'sub-1',
    phone: '971501234567',
    document_type: 'passport',
    is_valid: true,
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    extracted_fields: {
      full_name: 'AHMED ALI KHAN',
      passport_number: 'N8204918B',
      nationality: 'UNITED ARAB EMIRATES',
      date_of_birth: '1988-11-23',
      expiry_date: '2031-10-15',
    },
    issues: []
  },
  {
    id: 'sub-2',
    phone: '6591234567',
    document_type: 'trade_license',
    is_valid: true,
    created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
    extracted_fields: {
      entity_name: 'AL ASTOORA VENTURES PTE LTD',
      license_number: 'UEN 202401829K',
      jurisdiction: 'ACRA Singapore',
      status: 'Live / Registered',
      expiry_date: '2027-06-30'
    },
    issues: []
  },
  {
    id: 'sub-3',
    phone: '6591234567',
    document_type: 'proof_of_address',
    is_valid: true,
    created_at: new Date(Date.now() - 3600000 * 6).toISOString(),
    extracted_fields: {
      issuer: 'SP Services Singapore',
      recipient_name: 'Sarah Lim',
      service_address: '12 Marina Boulevard, #28-01, Singapore 018982',
      statement_date: '2026-08-01'
    },
    issues: []
  },
  {
    id: 'sub-4',
    phone: '6587654321',
    document_type: 'director_resolution',
    is_valid: false,
    created_at: new Date(Date.now() - 3600000 * 1).toISOString(),
    extracted_fields: {
      document_title: 'Board of Directors Written Resolution',
      signatories_found: '1 of 2 signatures',
    },
    issues: [
      'Missing authorized director signature on page 2',
      'Resolution date exceeds 90-day statutory validity window'
    ]
  }
];

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [refreshInterval, setRefreshInterval] = useState<number>(30);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const [stats, setStats] = useState<DashboardStats>(FALLBACK_STATS);
  const [clients, setClients] = useState<ClientProfile[]>(FALLBACK_CLIENTS);
  const [leads, setLeads] = useState<Lead[]>(FALLBACK_LEADS);
  const [bookings, setBookings] = useState<Booking[]>(FALLBACK_BOOKINGS);
  const [submissions, setSubmissions] = useState<DocumentSubmission[]>(FALLBACK_SUBMISSIONS);

  const loadAllData = useCallback(async () => {
    setIsLoading(true);
    try {
      const results = await Promise.allSettled([
        fetchStats(),
        fetchClients(),
        fetchLeads(),
        fetchBookings(),
        fetchSubmissions(),
      ]);

      const [statsRes, clientsRes, leadsRes, bookingsRes, submissionsRes] = results;

      if (statsRes.status === 'fulfilled' && statsRes.value) {
        setStats(statsRes.value);
      }
      if (clientsRes.status === 'fulfilled' && Array.isArray(clientsRes.value) && clientsRes.value.length > 0) {
        setClients(clientsRes.value);
      }
      if (leadsRes.status === 'fulfilled' && Array.isArray(leadsRes.value) && leadsRes.value.length > 0) {
        setLeads(leadsRes.value);
      }
      if (bookingsRes.status === 'fulfilled' && Array.isArray(bookingsRes.value) && bookingsRes.value.length > 0) {
        setBookings(bookingsRes.value);
      }
      if (submissionsRes.status === 'fulfilled' && Array.isArray(submissionsRes.value) && submissionsRes.value.length > 0) {
        setSubmissions(submissionsRes.value);
      }
    } catch (err) {
      console.warn('Dashboard data fetch:', err);
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
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      
      {/* Navigation Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isLoading={isLoading}
        onRefresh={loadAllData}
        refreshInterval={refreshInterval}
        setRefreshInterval={setRefreshInterval}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        
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

        {activeTab === 'submissions' && (
          <SubmissionsTab submissions={submissions} />
        )}

        {activeTab === 'bookings' && (
          <BookingsTab bookings={bookings} leads={leads} clients={clients} />
        )}

        {activeTab === 'transcripts' && <TranscriptsTab leads={leads} clients={clients} />}

      </main>

      {/* Clean Minimal Footer */}
      <footer className="w-full border-t border-slate-200 bg-white py-4 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-slate-600 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>Al Astoora Document Collector Agent</span>
            <span>•</span>
            <span className="text-slate-400 font-normal">Google All Things Agentic Hackathon 2026</span>
          </div>

          <div className="flex items-center gap-3 text-slate-400 text-[11px] font-mono">
            <span>FastAPI</span>
            <span>•</span>
            <span>Gemini 3.7 Flash</span>
            <span>•</span>
            <span>Cloud Run</span>
            <span>•</span>
            <span>Firestore</span>
          </div>
        </div>
      </footer>

    </div>
  );
};
