import React, { useState, useEffect } from 'react';
import { ActivityItem } from '../components';
import wsService from '../services/WebSocketService';

/**
 * Activity Page - Detailed activity logs and history
 */
function Activity() {
  const [filter, setFilter] = useState('all'); // all, sleep, wake, cry, feed, adult
  const [selectedDate, setSelectedDate] = useState('today'); // today, week, month
  const [activities, setActivities] = useState([
    {
      id: 1,
      type: 'sleep',
      description: 'Baby fell asleep peacefully',
      time: '10:30 PM',
      date: 'Today',
      duration: '3h 45m',
      details: 'Deep sleep detected, no disturbances'
    },
    {
      id: 2,
      type: 'wake',
      description: 'Baby woke up naturally',
      time: '2:15 AM',
      date: 'Today',
      duration: '15m',
      details: 'Brief wake period, self-soothed back to sleep'
    },
    {
      id: 3,
      type: 'sleep',
      description: 'Baby fell asleep again',
      time: '2:30 AM',
      date: 'Today',
      duration: '3h 45m',
      details: 'Restful sleep continued'
    },
    {
      id: 4,
      type: 'cry',
      description: 'Brief crying episode detected',
      time: '6:00 AM',
      date: 'Today',
      duration: '5m',
      details: 'Crying intensity: Moderate, resolved quickly'
    },
    {
      id: 5,
      type: 'adult',
      description: 'Parent entered nursery',
      time: '6:05 AM',
      date: 'Today',
      duration: '10m',
      details: 'Adult presence detected, baby calmed'
    },
    {
      id: 6,
      type: 'feed',
      description: 'Feeding session completed',
      time: '6:15 AM',
      date: 'Today',
      duration: '20m',
      details: 'Feeding duration: 20 minutes'
    },
    {
      id: 7,
      type: 'sleep',
      description: 'Baby fell asleep after feeding',
      time: '7:00 AM',
      date: 'Today',
      duration: '2h 15m',
      details: 'Post-feeding nap, peaceful sleep'
    },
    {
      id: 8,
      type: 'wake',
      description: 'Baby woke up naturally',
      time: '9:15 AM',
      date: 'Today',
      duration: '30m',
      details: 'Active wake period, happy and alert'
    },
    {
      id: 9,
      type: 'adult',
      description: 'Parent entered nursery',
      time: '9:45 AM',
      date: 'Today',
      duration: '15m',
      details: 'Playtime and interaction'
    },
    {
      id: 10,
      type: 'sleep',
      description: 'Baby fell asleep for nap',
      time: '10:30 AM',
      date: 'Today',
      duration: '1h 30m',
      details: 'Morning nap, restful sleep'
    },
    {
      id: 11,
      type: 'wake',
      description: 'Baby woke up from nap',
      time: '12:00 PM',
      date: 'Today',
      duration: '45m',
      details: 'Well-rested, active period'
    },
    {
      id: 12,
      type: 'feed',
      description: 'Feeding session completed',
      time: '12:45 PM',
      date: 'Today',
      duration: '25m',
      details: 'Lunch feeding, good appetite'
    }
  ]);

  const [activityStats, setActivityStats] = useState({
    total: 0,
    sleep: 0,
    wake: 0,
    cry: 0,
    feed: 0,
    adult: 0
  });

  useEffect(() => {
    // Calculate stats
    const stats = {
      total: activities.length,
      sleep: activities.filter(a => a.type === 'sleep').length,
      wake: activities.filter(a => a.type === 'wake').length,
      cry: activities.filter(a => a.type === 'cry').length,
      feed: activities.filter(a => a.type === 'feed').length,
      adult: activities.filter(a => a.type === 'adult').length
    };
    setActivityStats(stats);
  }, [activities]);

  useEffect(() => {
    // Subscribe to activity updates
    const handleActivityUpdate = (data) => {
      const newActivity = {
        id: Date.now(),
        type: data.type || 'general',
        description: data.description || 'Activity detected',
        time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        date: 'Today',
        duration: data.duration || '0m',
        details: data.details || ''
      };
      setActivities(prev => [newActivity, ...prev]);
    };

    wsService.subscribe('activity', handleActivityUpdate);

    return () => {
      wsService.unsubscribe('activity', handleActivityUpdate);
    };
  }, []);

  const filteredActivities = filter === 'all' 
    ? activities 
    : activities.filter(a => a.type === filter);

  const filterOptions = [
    { id: 'all', label: 'All Activities', icon: '📋', count: activityStats.total },
    { id: 'sleep', label: 'Sleep', icon: '😴', count: activityStats.sleep },
    { id: 'wake', label: 'Wake', icon: '👶', count: activityStats.wake },
    { id: 'cry', label: 'Crying', icon: '😢', count: activityStats.cry },
    { id: 'feed', label: 'Feeding', icon: '🍼', count: activityStats.feed },
    { id: 'adult', label: 'Adult', icon: '👤', count: activityStats.adult }
  ];

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6 min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Activity Logs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Complete history of all baby monitoring activities
          </p>
        </div>

        {/* Date Selector */}
        <div className="flex items-center space-x-2 bg-white rounded-xl p-1 shadow-soft">
          {['today', 'week', 'month'].map((period) => (
            <button
              key={period}
              onClick={() => setSelectedDate(period)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all capitalize ${
                selectedDate === period
                  ? 'bg-primary-500 text-white'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {/* Activity Statistics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {filterOptions.map((option) => (
          <button
            key={option.id}
            onClick={() => setFilter(option.id)}
            className={`p-4 rounded-2xl transition-all shadow-soft ${
              filter === option.id
                ? 'bg-primary-500 text-white'
                : 'bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            <div className="text-2xl mb-2">{option.icon}</div>
            <div className="text-xs font-semibold uppercase tracking-wide mb-1">
              {option.label}
            </div>
            <div className={`text-xl font-bold ${
              filter === option.id ? 'text-white' : 'text-slate-800'
            }`}>
              {option.count}
            </div>
          </button>
        ))}
      </div>

      {/* Activity Timeline */}
      <div className="bg-white rounded-2xl p-6 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Activity Timeline
          </h3>
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-500">
              Showing {filteredActivities.length} of {activities.length} activities
            </span>
          </div>
        </div>

        {/* Timeline */}
        <div className="relative">
          {/* Timeline Line */}
          <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-slate-200"></div>

          {/* Activities */}
          <div className="space-y-4">
            {filteredActivities.length > 0 ? (
              filteredActivities.map((activity, index) => (
                <div key={activity.id} className="relative flex items-start space-x-4">
                  {/* Timeline Dot */}
                  <div className="relative z-10 flex-shrink-0">
                    <div className="w-16 h-16 rounded-full bg-white border-4 border-slate-200 flex items-center justify-center text-xl shadow-soft">
                      {activity.type === 'sleep' && '😴'}
                      {activity.type === 'wake' && '👶'}
                      {activity.type === 'cry' && '😢'}
                      {activity.type === 'feed' && '🍼'}
                      {activity.type === 'adult' && '👤'}
                    </div>
                  </div>

                  {/* Activity Card */}
                  <div className="flex-1 bg-slate-50 rounded-xl p-4 hover:bg-slate-100 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <p className="font-semibold text-slate-800">
                            {activity.description}
                          </p>
                          <span className="text-xs font-semibold text-primary-600 bg-primary-100 px-2 py-1 rounded-full">
                            {activity.duration}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mb-2">
                          {activity.date} • {activity.time}
                        </p>
                        {activity.details && (
                          <p className="text-sm text-slate-600 bg-white px-3 py-2 rounded-lg mt-2">
                            {activity.details}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12">
                <div className="text-6xl mb-4 opacity-40">📋</div>
                <p className="text-lg font-semibold text-slate-600 mb-1">
                  No activities found
                </p>
                <p className="text-sm text-slate-500">
                  Try selecting a different filter or time period
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Activity Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
            Most Active Hours
          </h3>
          <div className="space-y-2">
            {['6:00 AM - 8:00 AM', '12:00 PM - 2:00 PM', '6:00 PM - 8:00 PM'].map((period, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-slate-50 rounded-lg">
                <span className="text-sm text-slate-700">{period}</span>
                <span className="text-xs font-semibold text-primary-600">
                  {Math.floor(Math.random() * 10) + 5} activities
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
            Activity Distribution
          </h3>
          <div className="space-y-3">
            {[
              { type: 'Sleep', count: activityStats.sleep, color: 'bg-indigo-500' },
              { type: 'Wake', count: activityStats.wake, color: 'bg-emerald-500' },
              { type: 'Feed', count: activityStats.feed, color: 'bg-orange-500' },
              { type: 'Cry', count: activityStats.cry, color: 'bg-red-500' },
              { type: 'Adult', count: activityStats.adult, color: 'bg-blue-500' }
            ].map((item) => {
              const percentage = activityStats.total > 0 
                ? (item.count / activityStats.total) * 100 
                : 0;
              return (
                <div key={item.type}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-slate-600">{item.type}</span>
                    <span className="text-xs font-semibold text-slate-800">{item.count}</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2">
                    <div
                      className={`${item.color} h-2 rounded-full transition-all`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
            Quick Insights
          </h3>
          <div className="space-y-3">
            <div className="p-3 bg-green-50 rounded-lg border border-green-200">
              <p className="text-xs font-semibold text-green-800 mb-1">
                ✓ Sleep Quality
              </p>
              <p className="text-xs text-green-600">
                Excellent sleep patterns detected today
              </p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-xs font-semibold text-blue-800 mb-1">
                ℹ Feeding Schedule
              </p>
              <p className="text-xs text-blue-600">
                Regular feeding intervals maintained
              </p>
            </div>
            <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
              <p className="text-xs font-semibold text-purple-800 mb-1">
                📊 Activity Level
              </p>
              <p className="text-xs text-purple-600">
                Normal activity levels for this period
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Activity;

