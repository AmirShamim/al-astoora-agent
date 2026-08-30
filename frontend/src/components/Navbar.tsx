import React from 'react';
import { 
  LayoutDashboard, 
  Users, 
  FileCheck2, 
  ScanEye, 
  CalendarDays, 
  MessageSquareCode, 
  RefreshCw
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
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/95 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-sm">
              A
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-slate-900 tracking-tight text-base">
                  Al Astoora
                </h1>
                <span className="text-[11px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-mono font-medium border border-slate-200">
                  Agent
                </span>
                <span className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  Gemini 3.7 Flash
                </span>
              </div>
            </div>
          </div>

          {/* Right Action Controls */}
          <div className="flex items-center gap-2">
            {/* Auto Refresh Selector */}
            <div className="hidden sm:flex items-center bg-slate-50 border border-slate-200 rounded-lg p-0.5 text-xs">
              <span className="text-slate-400 px-2 text-[11px]">Sync:</span>
              {[
                { label: 'Off', val: 0 },
                { label: '10s', val: 10 },
                { label: '30s', val: 30 },
              ].map((item) => (
                <button
                  key={item.val}
                  onClick={() => setRefreshInterval(item.val)}
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-all ${
                    refreshInterval === item.val
                      ? 'bg-white text-slate-900 shadow-2xs border border-slate-200 font-semibold'
                      : 'text-slate-500 hover:text-slate-800'
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
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium transition-all disabled:opacity-50 shadow-2xs"
              title="Refresh Data"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${isLoading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="flex space-x-1 overflow-x-auto py-1.5 border-t border-slate-100">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-slate-900 text-white font-semibold shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
