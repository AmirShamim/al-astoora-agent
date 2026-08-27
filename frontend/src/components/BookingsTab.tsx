import React, { useState } from 'react';
import { 
  CalendarDays, 
  Search, 
  Clock, 
  CheckCircle2, 
  Calendar as CalendarIcon,
  ExternalLink,
  MessageCircle
} from 'lucide-react';
import { Booking } from '../types/dashboard';

interface BookingsTabProps {
  bookings: Booking[];
}

export const BookingsTab: React.FC<BookingsTabProps> = ({ bookings }) => {
  const [search, setSearch] = useState('');

  const filteredBookings = bookings.filter((b) => {
    return (
      (b.name?.toLowerCase() || '').includes(search.toLowerCase()) ||
      b.phone.includes(search) ||
      b.date.includes(search) ||
      b.time.includes(search)
    );
  });

  const generateGCalUrl = (b: Booking) => {
    const title = encodeURIComponent(`Al Astoora Discovery Consultation — ${b.name || b.phone}`);
    const details = encodeURIComponent(`Client: ${b.name || 'Prospect'}\nPhone: ${b.phone}\nBooked automatically via Al Astoora WhatsApp AI Agent`);
    const cleanDate = b.date.replace(/[^0-9]/g, '');
    const cleanTime = b.time.replace(/[^0-9]/g, '').padEnd(4, '0');
    const startIso = `${cleanDate}T${cleanTime}00Z`;
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&details=${details}&dates=${startIso}/${startIso}`;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Header */}
      <div className="glass-card p-6 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <CalendarDays className="w-5 h-5 text-amber-400" />
            <span>Discovery Consultations & Bookings</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Appointments booked autonomously over WhatsApp with collision prevention via <code className="text-brand-300">book_appointment</code>.
          </p>
        </div>

        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search booking or client..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="glass-input pl-9 w-64 text-xs"
          />
        </div>
      </div>

      {/* Bookings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredBookings.length > 0 ? (
          filteredBookings.map((booking, idx) => (
            <div
              key={booking.id || idx}
              className="glass-card p-6 border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition-all"
            >
              <div>
                
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      <CalendarIcon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-base text-slate-100">
                        {booking.name || 'Discovery Consultation'}
                      </h3>
                      <p className="text-xs font-mono text-slate-400 mt-0.5">{booking.phone}</p>
                    </div>
                  </div>

                  <span className="badge-emerald">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {booking.status || 'Confirmed'}
                  </span>
                </div>

                {/* Time Details Banner */}
                <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 mb-4 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 flex items-center gap-1.5">
                      <CalendarIcon className="w-3.5 h-3.5 text-brand-400" />
                      Date:
                    </span>
                    <span className="text-slate-100 font-semibold">{booking.date}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-amber-400" />
                      Time:
                    </span>
                    <span className="text-slate-100 font-semibold">{booking.time}</span>
                  </div>
                </div>

              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                <a
                  href={`https://wa.me/${booking.phone.replace(/[^0-9]/g, '')}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium transition-colors"
                >
                  <MessageCircle className="w-3.5 h-3.5 text-emerald-400" />
                  <span>WhatsApp</span>
                </a>

                <a
                  href={generateGCalUrl(booking)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-600/20 hover:bg-brand-600/30 text-brand-300 border border-brand-500/30 text-xs font-semibold transition-all"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Add to GCal</span>
                </a>
              </div>

            </div>
          ))
        ) : (
          <div className="col-span-full glass-card p-12 text-center text-slate-500">
            <CalendarDays className="w-12 h-12 mx-auto mb-3 opacity-40 text-slate-400" />
            <p className="text-sm font-medium text-slate-300">No appointments scheduled yet.</p>
            <p className="text-xs text-slate-500 mt-1">Bookings confirmed via WhatsApp interactive buttons will appear here.</p>
          </div>
        )}
      </div>

    </div>
  );
};
