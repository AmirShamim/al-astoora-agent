import React from 'react';
import { 
  LayoutDashboard, 
  Users, 
  FileCheck2, 
  ScanEye, 
  CalendarDays, 
  MessageSquareCode, 
  RefreshCw, 
  Sparkles,
  Zap
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isLoading: boolean;
  onRefresh: () => void;
  refreshInterval: number;
  setRefreshInterval: (interval: number) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isLoading,
  onRefresh,
  refreshInterval,
  setRefreshInterval,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'leads', label: 'Leads CRM', icon: Users },
    { id: 'clients', label: 'Client Onboarding', icon: FileCheck2 },
    { id: 'submissions', label: 'Gemini Vision Audit', icon: ScanEye },
    { id: 'bookings', label: 'Bookings Calendar', icon: CalendarDays },
    { id: 'transcripts', label: 'Audit Transcripts', icon: MessageSquareCode },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo & Status */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-600 via-brand-500 to-emerald-400 p-0.5 shadow-lg shadow-brand-500/20 flex items-center justify-center">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Zap className="w-5 h-5 text-emerald-400 fill-emerald-400/20" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-lg text-slate-100 tracking-tight flex items-center gap-1.5">
                  Al Astoora <span className="text-xs px-2 py-0.5 rounded-md bg-brand-500/20 text-brand-300 font-mono border border-brand-500/30">AGENT</span>
                </h1>
                <span className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  Gemini 3.7 Flash
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                WhatsApp Autonomous Client Intake & Document Engine
              </p>
            </div>
          </div>

          {/* Right Action Controls */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Auto Refresh Selector */}
            <div className="hidden lg:flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 text-xs">
              <span className="text-slate-400 px-2 text-[11px]">Sync:</span>
              {[
                { label: 'Off', val: 0 },
                { label: '10s', val: 10 },
                { label: '30s', val: 30 },
              ].map((item) => (
                <button
                  key={item.val}
                  onClick={() => setRefreshInterval(item.val)}
                  className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                    refreshInterval === item.val
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {/* Manual Refresh Button */}
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium transition-all disabled:opacity-50"
              title="Refresh Data"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-brand-400' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            {/* Hackathon Badge */}
            <div className="hidden xl:flex items-center gap-1.5 px-3 py-1 rounded-xl bg-gradient-to-r from-amber-500/10 to-brand-500/10 border border-amber-500/20 text-amber-300 text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Google Agentic 2026</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="flex space-x-1 overflow-x-auto py-2 scrollbar-none border-t border-slate-800/40">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-medium whitespace-nowrap transition-all duration-200 ${
                  isActive
                    ? 'bg-brand-500/15 text-brand-300 border border-brand-500/30 shadow-sm shadow-brand-500/10 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-brand-400' : 'text-slate-500'}`} />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
