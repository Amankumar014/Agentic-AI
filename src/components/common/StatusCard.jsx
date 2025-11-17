import React from 'react';

/**
 * StatusCard Component - Displays status information with visual indicators
 */
function StatusCard({ title, status, isActive, severity = 'info', icon }) {
  const getStatusStyles = () => {
    if (!isActive) {
      return {
        card: 'bg-white text-slate-500 border-slate-100',
        glow: ''
      };
    }

    switch (severity) {
      case 'critical':
        return {
          card: 'bg-white text-accent-600 border-accent-100',
          glow: 'status-glow-red'
        };
      case 'warning':
        return {
          card: 'bg-white text-accent-400 border-accent-100',
          glow: 'status-glow-orange'
        };
      case 'success':
        return {
          card: 'bg-white text-primary-600 border-primary-100',
          glow: 'status-glow-green'
        };
      default:
        return {
          card: 'bg-white text-secondary-600 border-secondary-100',
          glow: 'status-glow-blue'
        };
    }
  };

  const styles = getStatusStyles();

  return (
    <div className={`p-6 rounded-2xl border transition-all duration-300 shadow-soft ${styles.card} ${styles.glow} fade-in`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-xs mb-2 uppercase tracking-wide opacity-70">
            {title}
          </h3>
          <p className="text-xl font-bold">{status}</p>
        </div>
        <div className="flex flex-col items-center space-y-2">
          <div className="text-3xl opacity-70">{icon}</div>
          {isActive && (
            <div
              className={`w-2 h-2 rounded-full ${
                severity === 'critical'
                  ? 'bg-accent-500'
                  : severity === 'warning'
                  ? 'bg-accent-400'
                  : severity === 'success'
                  ? 'bg-primary-500'
                  : 'bg-secondary-500'
              } pulse-animation`}
            ></div>
          )}
        </div>
      </div>
    </div>
  );
}

export default StatusCard;

