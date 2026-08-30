import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'brand' | 'emerald' | 'amber' | 'rose' | 'violet';
  trend?: string;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
}) => {
  return (
    <div className="card p-4 hover:border-slate-300 transition-colors">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500">{title}</p>
          <h3 className="text-2xl font-bold text-slate-900 mt-1 tracking-tight">
            {value}
          </h3>
        </div>
        <div className="p-2 rounded-lg bg-slate-50 text-slate-600 border border-slate-200/80">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      
      {(subtitle || trend) && (
        <div className="mt-2.5 flex items-center gap-1.5 text-xs text-slate-500 pt-2 border-t border-slate-100">
          {trend && (
            <span className="font-medium text-slate-700">
              {trend}
            </span>
          )}
          {trend && subtitle && <span>•</span>}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
