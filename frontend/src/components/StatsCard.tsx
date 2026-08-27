import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color: 'brand' | 'emerald' | 'amber' | 'rose' | 'violet';
  trend?: string;
}

const colorMap = {
  brand: {
    bg: 'from-brand-500/10 to-brand-500/0',
    border: 'border-brand-500/30',
    text: 'text-brand-400',
    iconBg: 'bg-brand-500/20 text-brand-300',
    glow: 'shadow-brand-500/5',
  },
  emerald: {
    bg: 'from-emerald-500/10 to-emerald-500/0',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    iconBg: 'bg-emerald-500/20 text-emerald-300',
    glow: 'shadow-emerald-500/5',
  },
  amber: {
    bg: 'from-amber-500/10 to-amber-500/0',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    iconBg: 'bg-amber-500/20 text-amber-300',
    glow: 'shadow-amber-500/5',
  },
  rose: {
    bg: 'from-rose-500/10 to-rose-500/0',
    border: 'border-rose-500/30',
    text: 'text-rose-400',
    iconBg: 'bg-rose-500/20 text-rose-300',
    glow: 'shadow-rose-500/5',
  },
  violet: {
    bg: 'from-purple-500/10 to-purple-500/0',
    border: 'border-purple-500/30',
    text: 'text-purple-400',
    iconBg: 'bg-purple-500/20 text-purple-300',
    glow: 'shadow-purple-500/5',
  },
};

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  trend,
}) => {
  const styles = colorMap[color];

  return (
    <div className={`relative overflow-hidden glass-card p-5 border bg-gradient-to-b ${styles.bg} ${styles.border} ${styles.glow} group hover:border-slate-700 transition-all duration-300`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 tracking-wider uppercase">{title}</p>
          <h3 className="text-2xl sm:text-3xl font-extrabold text-slate-100 mt-1 tracking-tight">
            {value}
          </h3>
        </div>
        <div className={`p-3 rounded-xl ${styles.iconBg} transition-transform group-hover:scale-110 duration-300`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      
      {(subtitle || trend) && (
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-400 pt-2 border-t border-slate-800/60">
          {trend && (
            <span className={`font-semibold ${styles.text}`}>
              {trend}
            </span>
          )}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
