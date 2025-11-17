import React from 'react';

/**
 * ActivityItem Component - Displays activity log entries
 */
function ActivityItem({ activity }) {
  const getActivityIcon = () => {
    switch (activity.type) {
      case 'sleep':
        return '😴';
      case 'wake':
        return '👶';
      case 'cry':
        return '😢';
      case 'feed':
        return '🍼';
      case 'adult':
        return '👤';
      default:
        return '📝';
    }
  };

  const getActivityStyles = () => {
    switch (activity.type) {
      case 'sleep':
        return {
          icon: 'bg-gradient-to-br from-indigo-400 to-purple-500 text-white border-indigo-300',
          badge: 'bg-indigo-500 text-white'
        };
      case 'wake':
        return {
          icon: 'bg-gradient-to-br from-emerald-400 to-teal-500 text-white border-emerald-300',
          badge: 'bg-emerald-500 text-white'
        };
      case 'cry':
        return {
          icon: 'bg-gradient-to-br from-red-400 to-pink-500 text-white border-red-300',
          badge: 'bg-red-500 text-white'
        };
      case 'feed':
        return {
          icon: 'bg-gradient-to-br from-orange-400 to-yellow-500 text-white border-orange-300',
          badge: 'bg-orange-500 text-white'
        };
      case 'adult':
        return {
          icon: 'bg-gradient-to-br from-blue-400 to-cyan-500 text-white border-blue-300',
          badge: 'bg-blue-500 text-white'
        };
      default:
        return {
          icon: 'bg-gradient-to-br from-slate-400 to-slate-500 text-white border-slate-300',
          badge: 'bg-slate-500 text-white'
        };
    }
  };

  const styles = getActivityStyles();

  return (
    <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors duration-200 fade-in">
      <div
        className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg shadow-sm ${styles.icon}`}
      >
        {getActivityIcon()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-800 text-sm truncate">
          {activity.description}
        </p>
        <p className="text-xs text-slate-500 mt-0.5">
          {activity.time}
        </p>
      </div>
      <div
        className={`text-xs font-semibold px-2.5 py-1 rounded-full ${styles.badge}`}
      >
        {activity.duration}
      </div>
    </div>
  );
}

export default ActivityItem;

