export interface DashboardStats {
  total_leads: number;
  total_clients: number;
  completed_clients: number;
  in_progress_clients: number;
  total_submissions: number;
  validated_submissions: number;
  rejected_submissions: number;
  total_bookings: number;
  confirmed_bookings: number;
  total_sessions: number;
  error?: string;
}

export interface Lead {
  id?: string;
  name?: string;
  phone: string;
  interest?: string;
  status?: string;
  source?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentItem {
  doc_type: string;
  status: 'pending' | 'submitted' | 'validated' | 'rejected' | string;
  file_url?: string;
  signed_url?: string;
  attempts?: number;
  updated_at?: string;
  validation_notes?: string;
}

export interface ClientProfile {
  id?: string;
  phone: string;
  name?: string;
  service_type?: string;
  onboarding_status?: 'pending' | 'in_progress' | 'complete' | string;
  documents?: DocumentItem[];
  created_at?: string;
  updated_at?: string;
}

export interface DocumentSubmission {
  id?: string;
  phone: string;
  document_type: string;
  is_valid: boolean;
  file_url?: string;
  signed_url?: string;
  extracted_fields?: Record<string, any>;
  issues?: string[];
  confidence?: number;
  created_at?: string;
}

export interface Booking {
  id?: string;
  name?: string;
  phone: string;
  date: string;
  time: string;
  status: string;
  created_at?: string;
}

export interface AuditMessage {
  id?: string;
  role: 'user' | 'model' | 'system' | string;
  text: string;
  phone?: string;
  timestamp?: string;
}

export interface TranscriptResponse {
  success: boolean;
  phone: string;
  messages: AuditMessage[];
  audit_trail_verified?: boolean;
  error?: string;
}
