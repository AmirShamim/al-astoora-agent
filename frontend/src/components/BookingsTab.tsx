import React, { useState, useMemo } from 'react';
import { 
  CalendarDays, 
  Search, 
  Clock, 
  CheckCircle2, 
  Calendar as CalendarIcon,
  ExternalLink,
  MessageCircle,
  Copy,
  Check,
  List,
  LayoutGrid,
  CalendarRange,
  Phone,
  CheckCheck
} from 'lucide-react';
import { Booking, Lead, ClientProfile } from '../types/dashboard';

interface BookingsTabProps {
  bookings: Booking[];
  leads?: Lead[];
  clients?: ClientProfile[];
}

export const BookingsTab: React.FC<BookingsTabProps> = ({ 
  bookings = [], 
  leads = [], 
  clients = [] 
}) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'upcoming' | 'completed'>('all');
  const [viewMode, setViewMode] = useState<'cards' | 'timeline' | 'table'>('cards');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Clean phone number formatting (e.g. 917011190158 -> +91 70111 90158)
  const formatPhoneNumber = (phoneStr: string): string => {
    if (!phoneStr) return '';
    const clean = phoneStr.replace(/[^0-9]/g, '');
    if (clean.length === 12 && clean.startsWith('91')) {
      return `+91 ${clean.slice(2, 7)} ${clean.slice(7)}`;
    }
    if (clean.length === 12 && clean.startsWith('971')) {
      return `+971 ${clean.slice(3, 5)} ${clean.slice(5, 8)} ${clean.slice(8)}`;
    }
    if (clean.length === 10 && clean.startsWith('65')) {
      return `+65 ${clean.slice(2, 6)} ${clean.slice(6)}`;
    }
    if (clean.length === 10) {
      return `+91 ${clean.slice(0, 5)} ${clean.slice(5)}`;
    }
    return phoneStr.startsWith('+') ? phoneStr : `+${phoneStr}`;
  };

  // Resolves human name rather than placeholders like "Valued Client" or "..."
  const resolveClientName = (booking: Booking): { displayName: string; hasRealName: boolean; formattedPhone: string } => {
    const phone = (booking.phone || '').trim();
    const cleanPhone = phone.replace(/[^0-9]/g, '');
    const rawName = (booking.name || '').trim();
    
    const isPlaceholder = 
      !rawName || 
      rawName === '...' || 
      rawName.toLowerCase().includes('valued client') || 
      rawName.toLowerCase() === 'client' ||
      rawName.toLowerCase() === 'anonymous prospect';

    if (!isPlaceholder) {
      return { 
        displayName: rawName, 
        hasRealName: true, 
        formattedPhone: formatPhoneNumber(phone) 
      };
    }

    // Try finding in CRM Leads
    const matchingLead = leads.find((l) => l.phone.replace(/[^0-9]/g, '') === cleanPhone);
    if (matchingLead?.name && matchingLead.name !== '...' && !matchingLead.name.toLowerCase().includes('valued client')) {
      return { 
        displayName: matchingLead.name, 
        hasRealName: true, 
        formattedPhone: formatPhoneNumber(phone) 
      };
    }

    // Try finding in Client Profiles
    const matchingClient = clients.find((c) => c.phone.replace(/[^0-9]/g, '') === cleanPhone);
    if (matchingClient?.name && matchingClient.name !== '...' && !matchingClient.name.toLowerCase().includes('valued client')) {
      return { 
        displayName: matchingClient.name, 
        hasRealName: true, 
        formattedPhone: formatPhoneNumber(phone) 
      };
    }

    // Default to clean phone number representation
    const formatted = formatPhoneNumber(phone);
    return { 
      displayName: formatted || 'WhatsApp Client', 
      hasRealName: false, 
      formattedPhone: formatted 
    };
  };

  // Converts 24-hr time '14:00' to user-friendly IST string '02:00 PM IST (02:00 - 02:30 PM)'
  const formatTimeIST = (timeStr: string, compact = false): string => {
    if (!timeStr) return 'TBD IST';
    const parts = timeStr.split(':');
    if (parts.length >= 2) {
      const hours = parseInt(parts[0], 10);
      const mins = parseInt(parts[1], 10);
      if (!isNaN(hours) && !isNaN(mins)) {
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const h12 = hours % 12 || 12;
        const formattedH = h12 < 10 ? `0${h12}` : `${h12}`;
        const formattedM = mins < 10 ? `0${mins}` : `${mins}`;

        if (compact) {
          return `${formattedH}:${formattedM} ${ampm} IST`;
        }

        const endMinsTotal = hours * 60 + mins + 30;
        const endHours = Math.floor(endMinsTotal / 60) % 24;
        const endMins = endMinsTotal % 60;
        const endAmpm = endHours >= 12 ? 'PM' : 'AM';
        const endH12 = endHours % 12 || 12;
        const endFormattedH = endH12 < 10 ? `0${endH12}` : `${endH12}`;
        const endFormattedM = endMins < 10 ? `0${endMins}` : `${endMins}`;

        return `${formattedH}:${formattedM} ${ampm} IST (${formattedH}:${formattedM} – ${endFormattedH}:${endFormattedM} ${endAmpm})`;
      }
    }
    return `${timeStr} IST`;
  };

  // Converts date '2026-08-28' to 'Fri, 28 Aug 2026'
  const formatDateIST = (dateStr: string): string => {
    if (!dateStr) return 'Scheduled Date';
    try {
      if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
        const [y, m, d] = dateStr.split('-').map(Number);
        const dt = new Date(y, m - 1, d);
        const dayName = dt.toLocaleDateString('en-IN', { weekday: 'short' });
        const monthName = dt.toLocaleDateString('en-IN', { month: 'short' });
        return `${dayName}, ${d} ${monthName} ${y}`;
      }
      const dt = new Date(dateStr);
      if (!isNaN(dt.getTime())) {
        return dt.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
      }
    } catch {}
    return dateStr;
  };

  // Checks whether the booking's scheduled slot has already occurred in IST
  const isBookingInPast = (dateStr: string, timeStr?: string): boolean => {
    if (!dateStr) return false;
    const nowMs = Date.now();

    try {
      let year = 0, month = 0, day = 0;
      if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
        const parts = dateStr.split('-').map(Number);
        year = parts[0];
        month = parts[1] - 1;
        day = parts[2];
      } else {
        const d = new Date(dateStr);
        if (!isNaN(d.getTime())) {
          year = d.getFullYear();
          month = d.getMonth();
          day = d.getDate();
        } else {
          return false;
        }
      }

      let hours = 23, minutes = 59;
      if (timeStr && timeStr.includes(':')) {
        const [h, m] = timeStr.split(':').map(Number);
        if (!isNaN(h) && !isNaN(m)) {
          hours = h;
          minutes = m;
        }
      }

      // Slot end time is 30 mins after start time
      const slotEndMinutesTotal = hours * 60 + minutes + 30;
      const slotEndH = Math.floor(slotEndMinutesTotal / 60);
      const slotEndM = slotEndMinutesTotal % 60;

      // IST is UTC + 5:30 (330 minutes)
      const istOffsetMs = 5.5 * 60 * 60 * 1000;
      const slotUtcMs = Date.UTC(year, month, day, slotEndH, slotEndM) - istOffsetMs;

      return nowMs >= slotUtcMs;
    } catch {
      return false;
    }
  };

  // Status computation: past appointments are automatically "Completed", future are "Confirmed"
  const getBookingStatus = (booking: Booking) => {
    const rawStatus = (booking.status || 'confirmed').toLowerCase();
    if (rawStatus === 'cancelled') {
      return { label: 'Cancelled', isPast: true, badgeClass: 'badge-rose' };
    }
    if (rawStatus === 'rescheduled') {
      return { label: 'Rescheduled', isPast: false, badgeClass: 'badge-amber' };
    }
    if (rawStatus === 'completed' || isBookingInPast(booking.date, booking.time)) {
      return { label: 'Completed', isPast: true, badgeClass: 'badge-slate' };
    }
    return { label: 'Confirmed', isPast: false, badgeClass: 'badge-emerald' };
  };

  // Generate Google Calendar Link strictly in IST (+05:30 offset)
  const generateGCalUrl = (b: Booking) => {
    const { displayName } = resolveClientName(b);
    const title = encodeURIComponent(`Al Astoora Consultation — ${displayName}`);
    const details = encodeURIComponent(
      `Al Astoora Discovery Consultation\n` +
      `Client: ${displayName}\n` +
      `Phone: ${formatPhoneNumber(b.phone)}\n` +
      `Timezone: Indian Standard Time (IST, UTC+05:30)\n` +
      `Slot: ${formatTimeIST(b.time)}\n` +
      `Booked via WhatsApp Autonomous Agent`
    );
    const cleanDate = (b.date || '').replace(/[^0-9]/g, '');
    const cleanTime = (b.time || '').replace(/[^0-9]/g, '').padEnd(4, '0');
    const startIso = `${cleanDate || '20260901'}T${cleanTime || '120000'}Z`;
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&details=${details}&dates=${startIso}/${startIso}`;
  };

  // Pre-filled WhatsApp message in IST
  const getWhatsAppMessageUrl = (b: Booking, isCompleted: boolean) => {
    const { displayName } = resolveClientName(b);
    const cleanPhone = (b.phone || '').replace(/[^0-9]/g, '');
    const formattedDate = formatDateIST(b.date);
    const formattedTime = formatTimeIST(b.time, true);
    
    let messageText = '';
    if (isCompleted) {
      messageText = 
        `Hello ${displayName},\n\n` +
        `Thank you for participating in our scheduled consultation on *${formattedDate}* at *${formattedTime}*.\n\n` +
        `Please let us know if you need any follow-up documents or assistance.\n\n` +
        `Best regards,\nAl Astoora Client Team`;
    } else {
      messageText = 
        `Hello ${displayName},\n\n` +
        `This is a reminder for your upcoming consultation with Al Astoora on *${formattedDate}* at *${formattedTime}*.\n\n` +
        `Please let us know if you have any questions before the session.\n\n` +
        `Best regards,\nAl Astoora Client Team`;
    }

    return `https://wa.me/${cleanPhone}?text=${encodeURIComponent(messageText)}`;
  };

  // Copy appointment summary to clipboard
  const handleCopyDetails = (b: Booking, id: string, statusLabel: string) => {
    const { displayName, formattedPhone } = resolveClientName(b);
    const text = 
      `📋 Consultation Booking (Al Astoora)\n` +
      `• Client: ${displayName}\n` +
      `• Phone: ${formattedPhone}\n` +
      `• Date: ${formatDateIST(b.date)}\n` +
      `• Time: ${formatTimeIST(b.time)}\n` +
      `• Status: ${statusLabel}`;
    
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filter & Sort Bookings
  const filteredBookings = useMemo(() => {
    return bookings
      .filter((b) => {
        if (!b) return false;
        const { displayName, formattedPhone } = resolveClientName(b);
        const { isPast } = getBookingStatus(b);
        const date = b.date || '';
        const time = b.time || '';
        
        const matchesSearch =
          displayName.toLowerCase().includes(search.toLowerCase()) ||
          formattedPhone.includes(search) ||
          b.phone.includes(search) ||
          date.includes(search) ||
          time.includes(search);

        const matchesFilter =
          statusFilter === 'all' ||
          (statusFilter === 'upcoming' && !isPast) ||
          (statusFilter === 'completed' && isPast);

        return matchesSearch && matchesFilter;
      })
      .sort((a, b) => {
        const dateA = `${a.date || ''} ${a.time || ''}`;
        const dateB = `${b.date || ''} ${b.time || ''}`;
        return dateB.localeCompare(dateA);
      });
  }, [bookings, search, statusFilter, leads, clients]);

  // Group by Date for Timeline View
  const groupedByDate = useMemo(() => {
    const groups: Record<string, Booking[]> = {};
    filteredBookings.forEach((b) => {
      const d = b.date || 'Unscheduled';
      if (!groups[d]) groups[d] = [];
      groups[d].push(b);
    });
    return groups;
  }, [filteredBookings]);

  // Metrics counts
  const upcomingCount = bookings.filter((b) => !isBookingInPast(b.date || '', b.time)).length;
  const completedCount = bookings.filter((b) => isBookingInPast(b.date || '', b.time)).length;
  const uniquePhones = new Set(bookings.map((b) => b.phone)).size;

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Header with Metrics Overview */}
      <div className="card p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <CalendarDays className="w-5 h-5 text-slate-700" />
                <span>Consultations & Bookings</span>
              </h2>
              <span className="badge-brand font-mono text-[11px]">
                IST (UTC+05:30)
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Appointments booked over WhatsApp with conflict-free slot reservation via <code className="font-mono text-slate-700 font-medium">book_appointment</code>.
            </p>
          </div>

          {/* Quick Metrics Chips */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs flex items-center gap-2">
              <span className="text-slate-500">Total Bookings:</span>
              <span className="font-bold text-slate-900">{bookings.length}</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs flex items-center gap-2 text-emerald-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Upcoming:</span>
              <span className="font-bold text-emerald-900">{upcomingCount}</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs flex items-center gap-2 text-slate-700">
              <CheckCheck className="w-3.5 h-3.5 text-slate-500" />
              <span>Completed:</span>
              <span className="font-bold text-slate-900">{completedCount}</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs flex items-center gap-2">
              <span className="text-slate-500">Unique Clients:</span>
              <span className="font-bold text-slate-900">{uniquePhones}</span>
            </div>
          </div>
        </div>

        {/* Controls Bar: Filters, Search, and View Switcher */}
        <div className="pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          
          {/* Status Filter Pills */}
          <div className="flex items-center bg-slate-100 border border-slate-200 rounded-lg p-0.5 text-xs">
            <button
              onClick={() => setStatusFilter('all')}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                statusFilter === 'all' ? 'bg-white text-slate-900 shadow-2xs font-semibold' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              All ({bookings.length})
            </button>
            <button
              onClick={() => setStatusFilter('upcoming')}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                statusFilter === 'upcoming' ? 'bg-white text-emerald-700 shadow-2xs font-semibold' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Upcoming ({upcomingCount})
            </button>
            <button
              onClick={() => setStatusFilter('completed')}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                statusFilter === 'completed' ? 'bg-white text-slate-900 shadow-2xs font-semibold' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Completed ({completedCount})
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
              <input
                type="text"
                placeholder="Search name, phone, date, slot..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input-field pl-8 w-56 text-xs"
              />
            </div>

            {/* View Switcher */}
            <div className="flex items-center bg-slate-100 border border-slate-200 rounded-lg p-0.5 text-xs">
              <button
                onClick={() => setViewMode('cards')}
                className={`p-1.5 rounded transition-all ${
                  viewMode === 'cards' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-400 hover:text-slate-700'
                }`}
                title="Grid Cards View"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('timeline')}
                className={`p-1.5 rounded transition-all ${
                  viewMode === 'timeline' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-400 hover:text-slate-700'
                }`}
                title="Agenda / Timeline View"
              >
                <CalendarRange className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded transition-all ${
                  viewMode === 'table' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-400 hover:text-slate-700'
                }`}
                title="Table View"
              >
                <List className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main View Display */}
      {filteredBookings.length > 0 ? (
        <>
          {/* 1. CARDS GRID VIEW */}
          {viewMode === 'cards' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredBookings.map((booking, idx) => {
                const bookingId = booking.id || `${booking.phone}-${booking.date}-${booking.time}-${idx}`;
                const { displayName, hasRealName, formattedPhone } = resolveClientName(booking);
                const { label: statusLabel, isPast, badgeClass } = getBookingStatus(booking);

                return (
                  <div
                    key={bookingId}
                    className="card p-4 flex flex-col justify-between hover:border-slate-300 transition-all"
                  >
                    <div>
                      {/* Card Header: Client & Status */}
                      <div className="flex items-start justify-between gap-2 mb-3">
                        <div className="flex items-start gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 border border-slate-200 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                            {hasRealName ? displayName[0].toUpperCase() : <Phone className="w-3.5 h-3.5 text-slate-500" />}
                          </div>
                          <div>
                            <h3 className="font-semibold text-sm text-slate-900 leading-snug">
                              {displayName}
                            </h3>
                            <p className="text-xs font-mono text-slate-500 mt-0.5">
                              {formattedPhone}
                            </p>
                          </div>
                        </div>

                        <span className={badgeClass}>
                          {isPast ? <CheckCheck className="w-3 h-3 text-slate-500" /> : <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                          {statusLabel}
                        </span>
                      </div>

                      {/* IST Date & Time Schedule Box */}
                      <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 mb-3 space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-500 flex items-center gap-1.5">
                            <CalendarIcon className="w-3.5 h-3.5 text-slate-400" />
                            Date:
                          </span>
                          <span className="text-slate-900 font-semibold">
                            {formatDateIST(booking.date)}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-500 flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                            Slot Time (IST):
                          </span>
                          <span className="text-slate-900 font-semibold font-mono text-[11px]">
                            {formatTimeIST(booking.time)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Action Bar */}
                    <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-1.5">
                      <div className="flex items-center gap-1">
                        {/* WhatsApp Action */}
                        <a
                          href={getWhatsAppMessageUrl(booking, isPast)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 text-xs font-medium transition-colors"
                          title={isPast ? 'Send follow-up message on WhatsApp' : 'Send appointment reminder on WhatsApp'}
                        >
                          <MessageCircle className="w-3 h-3 text-emerald-600" />
                          <span>{isPast ? 'Follow-up' : 'WhatsApp'}</span>
                        </a>

                        {/* Copy Details */}
                        <button
                          onClick={() => handleCopyDetails(booking, bookingId, statusLabel)}
                          className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors border border-transparent hover:border-slate-200"
                          title="Copy Consultation Details"
                        >
                          {copiedId === bookingId ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>

                      {/* Google Calendar Action for Upcoming */}
                      {!isPast && (
                        <a
                          href={generateGCalUrl(booking)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-colors shadow-2xs"
                          title="Add event to Google Calendar in Indian Standard Time"
                        >
                          <ExternalLink className="w-3 h-3" />
                          <span>Add to GCal</span>
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* 2. TIMELINE / AGENDA VIEW */}
          {viewMode === 'timeline' && (
            <div className="space-y-4">
              {Object.entries(groupedByDate).map(([dateKey, dateBookings]) => {
                const isGroupPast = isBookingInPast(dateKey);
                return (
                  <div key={dateKey} className="card p-5">
                    <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 rounded-md bg-slate-100 text-slate-700">
                          <CalendarIcon className="w-4 h-4" />
                        </div>
                        <h3 className="font-bold text-sm text-slate-900">
                          {formatDateIST(dateKey)}
                        </h3>
                        <span className={isGroupPast ? 'badge-slate text-[11px]' : 'badge-emerald text-[11px]'}>
                          {isGroupPast ? 'Concluded' : 'Active'}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400 font-mono">
                        {dateBookings.length} {dateBookings.length === 1 ? 'Slot' : 'Slots'}
                      </span>
                    </div>

                    <div className="divide-y divide-slate-100">
                      {dateBookings.map((b, idx) => {
                        const bId = b.id || `${b.phone}-${b.date}-${b.time}-${idx}`;
                        const { displayName, formattedPhone } = resolveClientName(b);
                        const { label: statusLabel, isPast, badgeClass } = getBookingStatus(b);

                        return (
                          <div key={bId} className="py-3 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div className="flex items-center gap-3">
                              <div className={`px-2.5 py-1 rounded-md font-mono text-xs font-medium whitespace-nowrap ${
                                isPast ? 'bg-slate-100 text-slate-600 border border-slate-200' : 'bg-slate-900 text-white'
                              }`}>
                                {formatTimeIST(b.time, true)}
                              </div>
                              <div>
                                <h4 className="font-semibold text-xs text-slate-900">{displayName}</h4>
                                <p className="font-mono text-[11px] text-slate-500">{formattedPhone}</p>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <span className={badgeClass}>
                                {isPast ? <CheckCheck className="w-3 h-3 text-slate-500" /> : <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                                {statusLabel}
                              </span>
                              <a
                                href={getWhatsAppMessageUrl(b, isPast)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 text-xs font-medium"
                              >
                                <MessageCircle className="w-3 h-3 text-emerald-600" />
                                <span>{isPast ? 'Follow-up' : 'Reminder'}</span>
                              </a>
                              {!isPast && (
                                <a
                                  href={generateGCalUrl(b)}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  <span>GCal</span>
                                </a>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* 3. TABLE VIEW */}
          {viewMode === 'table' && (
            <div className="card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-700">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                    <tr>
                      <th className="px-5 py-3">Client Contact</th>
                      <th className="px-5 py-3">Phone</th>
                      <th className="px-5 py-3">Date (IST)</th>
                      <th className="px-5 py-3">Slot Time (IST)</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredBookings.map((b, idx) => {
                      const bId = b.id || `${b.phone}-${b.date}-${b.time}-${idx}`;
                      const { displayName, formattedPhone } = resolveClientName(b);
                      const { label: statusLabel, isPast, badgeClass } = getBookingStatus(b);

                      return (
                        <tr key={bId} className="hover:bg-slate-50/70 transition-colors">
                          <td className="px-5 py-3 font-medium text-slate-900">
                            {displayName}
                          </td>
                          <td className="px-5 py-3 font-mono text-slate-600">
                            {formattedPhone}
                          </td>
                          <td className="px-5 py-3 font-medium text-slate-900">
                            {formatDateIST(b.date)}
                          </td>
                          <td className="px-5 py-3 font-mono text-slate-800">
                            {formatTimeIST(b.time, true)}
                          </td>
                          <td className="px-5 py-3">
                            <span className={badgeClass}>
                              {isPast ? <CheckCheck className="w-3 h-3 text-slate-500" /> : <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                              {statusLabel}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-right">
                            <div className="inline-flex items-center gap-1.5">
                              <a
                                href={getWhatsAppMessageUrl(b, isPast)}
                                target="_blank"
                                rel="noreferrer"
                                className="p-1 rounded text-emerald-700 hover:bg-emerald-50"
                                title={isPast ? 'WhatsApp Follow-up' : 'WhatsApp Reminder'}
                              >
                                <MessageCircle className="w-4 h-4" />
                              </a>
                              {!isPast && (
                                <a
                                  href={generateGCalUrl(b)}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="p-1 rounded text-slate-700 hover:bg-slate-100"
                                  title="Add to Google Calendar"
                                >
                                  <ExternalLink className="w-4 h-4" />
                                </a>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="card p-10 text-center text-slate-500">
          <CalendarDays className="w-8 h-8 mx-auto mb-2 text-slate-400" />
          <p className="text-sm font-medium text-slate-700">No consultation appointments found for this filter.</p>
          <p className="text-xs text-slate-400 mt-0.5">Appointments booked via WhatsApp interactive slots will appear here automatically.</p>
        </div>
      )}

    </div>
  );
};
