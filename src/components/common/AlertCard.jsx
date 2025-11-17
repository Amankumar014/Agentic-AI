import React from 'react';

/**
 * AlertCard Component - Displays alert messages with severity indicators
 */
function AlertCard({ alert }) {
  const getSeverityStyles = () => {
    switch (alert.severity) {
      case 'critical':
        return {
          border: 'border-l-accent-500',
          bg: 'bg-white',
          badge: 'bg-accent-500 text-white'
        };
      case 'warning':
        return {
          border: 'border-l-accent-400',
          bg: 'bg-white',
          badge: 'bg-accent-400 text-white'
        };
      default:
        return {
          border: 'border-l-secondary-400',
          bg: 'bg-white',
          badge: 'bg-secondary-400 text-white'
        };
    }
  };

  const styles = getSeverityStyles();

  return (
    <div
      className={`p-4 border-l-4 rounded-xl ${styles.border} ${styles.bg} fade-in shadow-soft hover:shadow-soft-lg transition-all duration-200`}
    >
      <div className="flex justify-between items-start gap-3">
        <div className="flex-1">
          <h4 className="font-semibold text-slate-800 text-sm leading-snug">{alert.message}</h4>
          <p className="text-xs text-slate-500 mt-1">
            {alert.timestamp}
          </p>
        </div>
        <span
          className={`px-2.5 py-1 text-xs font-semibold rounded-full uppercase tracking-wide ${styles.badge}`}
        >
          {alert.severity}
        </span>
      </div>
    </div>
  );
}

export default AlertCard;

