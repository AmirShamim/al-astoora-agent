import { DashboardStats, Lead, ClientProfile, DocumentSubmission, Booking, TranscriptResponse } from '../types/dashboard';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export async function fetchStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/api/dashboard/stats`);
  if (!res.ok) throw new Error(`Stats HTTP error: ${res.status}`);
  return res.json();
}

export async function fetchClients(): Promise<ClientProfile[]> {
  const res = await fetch(`${API_BASE}/api/dashboard/clients`);
  if (!res.ok) throw new Error(`Clients HTTP error: ${res.status}`);
  const data = await res.json();
  return data.clients || [];
}

export async function fetchLeads(): Promise<Lead[]> {
  const res = await fetch(`${API_BASE}/api/dashboard/leads`);
  if (!res.ok) throw new Error(`Leads HTTP error: ${res.status}`);
  const data = await res.json();
  return data.leads || [];
}

export async function fetchBookings(): Promise<Booking[]> {
  const res = await fetch(`${API_BASE}/api/dashboard/bookings`);
  if (!res.ok) throw new Error(`Bookings HTTP error: ${res.status}`);
  const data = await res.json();
  return data.bookings || [];
}

export async function fetchSubmissions(): Promise<DocumentSubmission[]> {
  const res = await fetch(`${API_BASE}/api/dashboard/submissions`);
  if (!res.ok) throw new Error(`Submissions HTTP error: ${res.status}`);
  const data = await res.json();
  return data.submissions || [];
}

export async function fetchTranscript(phone: string): Promise<TranscriptResponse> {
  const res = await fetch(`${API_BASE}/api/dashboard/transcripts/${encodeURIComponent(phone)}`);
  if (!res.ok) throw new Error(`Transcript HTTP error: ${res.status}`);
  return res.json();
}
