import React from 'react';

/**
 * DailySummaryCard Component - Displays daily statistics with trend indicators
 */
function DailySummaryCard({ title, value, change, icon, variant = 'primary' }) {
  const isPositive = change > 0;

  const variants = {
    primary:
      'bg-white border border-primary-100 text-primary-700 shadow-soft',
    secondary: 'bg-white border border-secondary-100 text-secondary-700 shadow-soft',
    accent: 'bg-white border border-primary-100 text-primary-600 shadow-soft',
    warning: 'bg-white border border-accent-100 text-accent-600 shadow-soft'
  };

  return (
    <div
      className={`${variants[variant]} p-6 rounded-2xl transition-all duration-300 hover:shadow-soft-lg fade-in`}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide mb-2 opacity-70">
            {title}
          </p>
          <p className="text-3xl font-bold mb-3">{value}</p>
          <div className="flex items-center">
            <span
              className={`text-xs px-3 py-1.5 rounded-full font-semibold ${
                isPositive
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              {isPositive ? '↗' : '↘'} {Math.abs(change)}%
            </span>
          </div>
        </div>
        <div className="text-5xl opacity-60">{icon}</div>
      </div>
    </div>
  );
}

export default DailySummaryCard;

