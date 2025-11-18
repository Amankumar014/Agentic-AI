import React, { useState, useEffect } from 'react';
import wsService from '../services/WebSocketService';

/**
 * SleepLogs Page - Sleep tracking and analytics
 */
function SleepLogs() {
  const [selectedPeriod, setSelectedPeriod] = useState('today'); // today, week, month
  const [sleepData, setSleepData] = useState({
    today: {
      totalSleep: '8.5h',
      averageSession: '2.1h',
      wakeUps: 3,
      longestSession: '3.5h',
      sleepQuality: 85
    },
    week: {
      totalSleep: '58.2h',
      averageSession: '2.0h',
      wakeUps: 18,
      longestSession: '4.2h',
      sleepQuality: 82
    },
    month: {
      totalSleep: '245.5h',
      averageSession: '2.1h',
      wakeUps: 78,
      longestSession: '5.1h',
      sleepQuality: 80
    }
  });

  // Mock sleep sessions data
  const [sleepSessions] = useState([
    {
      id: 1,
      startTime: '10:30 PM',
      endTime: '2:15 AM',
      duration: '3h 45m',
      date: 'Today',
      quality: 'excellent',
      wakeUps: 0
    },
    {
      id: 2,
      startTime: '2:45 AM',
      endTime: '6:30 AM',
      duration: '3h 45m',
      date: 'Today',
      quality: 'good',
      wakeUps: 1
    },
    {
      id: 3,
      startTime: '7:00 AM',
      endTime: '9:15 AM',
      duration: '2h 15m',
      date: 'Today',
      quality: 'excellent',
      wakeUps: 0
    },
    {
      id: 4,
      startTime: '10:00 PM',
      endTime: '1:30 AM',
      duration: '3h 30m',
      date: 'Yesterday',
      quality: 'good',
      wakeUps: 2
    },
    {
      id: 5,
      startTime: '2:00 AM',
      endTime: '6:00 AM',
      duration: '4h 0m',
      date: 'Yesterday',
      quality: 'excellent',
      wakeUps: 0
    }
  ]);

  useEffect(() => {
    // Subscribe to sleep data updates
    const handleSleepUpdate = (data) => {
      // Handle real-time sleep data updates
      console.log('Sleep data update:', data);
    };

    wsService.subscribe('sleep_update', handleSleepUpdate);

    return () => {
      wsService.unsubscribe('sleep_update', handleSleepUpdate);
    };
  }, []);

  const currentData = sleepData[selectedPeriod];

  const getQualityColor = (quality) => {
    if (quality === 'excellent') return 'bg-green-500';
    if (quality === 'good') return 'bg-blue-500';
    if (quality === 'fair') return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getQualityBadge = (quality) => {
    if (quality === 'excellent') return 'bg-green-100 text-green-700';
    if (quality === 'good') return 'bg-blue-100 text-blue-700';
    if (quality === 'fair') return 'bg-yellow-100 text-yellow-700';
    return 'bg-red-100 text-red-700';
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6 min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Sleep Logs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track and analyze your baby's sleep patterns
          </p>
        </div>

        {/* Period Selector */}
        <div className="flex items-center space-x-2 bg-white rounded-xl p-1 shadow-soft">
          {['today', 'week', 'month'].map((period) => (
            <button
              key={period}
              onClick={() => setSelectedPeriod(period)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all capitalize ${
                selectedPeriod === period
                  ? 'bg-primary-500 text-white'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">😴</span>
            <span className="text-xs font-semibold text-green-600 bg-green-100 px-2 py-1 rounded-full">
              +5%
            </span>
          </div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            Total Sleep
          </h3>
          <p className="text-2xl font-bold text-slate-800">{currentData.totalSleep}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">⏱</span>
          </div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            Avg Session
          </h3>
          <p className="text-2xl font-bold text-slate-800">{currentData.averageSession}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">👶</span>
            <span className="text-xs font-semibold text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
              -2
            </span>
          </div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            Wake Ups
          </h3>
          <p className="text-2xl font-bold text-slate-800">{currentData.wakeUps}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">⭐</span>
          </div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            Longest Session
          </h3>
          <p className="text-2xl font-bold text-slate-800">{currentData.longestSession}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">💤</span>
            <span className="text-xs font-semibold text-purple-600 bg-purple-100 px-2 py-1 rounded-full">
              {currentData.sleepQuality}%
            </span>
          </div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            Sleep Quality
          </h3>
          <div className="mt-2">
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div
                className="bg-gradient-to-r from-purple-400 to-indigo-500 h-2 rounded-full"
                style={{ width: `${currentData.sleepQuality}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sleep Chart */}
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 shadow-soft">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
            Sleep Pattern - {selectedPeriod.charAt(0).toUpperCase() + selectedPeriod.slice(1)}
          </h3>
          <div className="h-64 flex items-end justify-between space-x-2">
            {[...Array(24)].map((_, hour) => {
              const height = Math.random() * 100;
              const isActive = hour >= 22 || hour <= 6; // Night hours
              return (
                <div key={hour} className="flex-1 flex flex-col items-center">
                  <div
                    className={`w-full rounded-t transition-all ${
                      isActive
                        ? 'bg-gradient-to-t from-indigo-500 to-purple-400'
                        : 'bg-slate-200'
                    }`}
                    style={{ height: `${height}%` }}
                  ></div>
                  {hour % 4 === 0 && (
                    <span className="text-xs text-slate-500 mt-2">
                      {hour.toString().padStart(2, '0')}:00
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          <div className="mt-4 flex items-center justify-center space-x-6 text-xs text-slate-500">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-indigo-500 rounded"></div>
              <span>Sleeping</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-slate-200 rounded"></div>
              <span>Awake</span>
            </div>
          </div>
        </div>

        {/* Sleep Quality Indicator */}
        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
            Sleep Quality Score
          </h3>
          <div className="flex flex-col items-center justify-center h-64">
            <div className="relative w-48 h-48">
              <svg className="transform -rotate-90 w-48 h-48">
                <circle
                  cx="96"
                  cy="96"
                  r="88"
                  stroke="currentColor"
                  strokeWidth="16"
                  fill="none"
                  className="text-slate-200"
                />
                <circle
                  cx="96"
                  cy="96"
                  r="88"
                  stroke="currentColor"
                  strokeWidth="16"
                  fill="none"
                  strokeDasharray={`${(currentData.sleepQuality / 100) * 552.92} 552.92`}
                  className="text-purple-500"
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-5xl font-bold text-slate-800">
                    {currentData.sleepQuality}
                  </div>
                  <div className="text-sm text-slate-500 mt-1">out of 100</div>
                </div>
              </div>
            </div>
            <p className="text-sm text-slate-600 mt-4 text-center">
              Based on sleep duration, wake-ups, and consistency
            </p>
          </div>
        </div>
      </div>

      {/* Sleep Sessions List */}
      <div className="bg-white rounded-2xl p-6 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Recent Sleep Sessions
          </h3>
          <button className="text-xs font-semibold text-primary-600 hover:text-primary-700">
            View All →
          </button>
        </div>
        <div className="space-y-3">
          {sleepSessions.map((session) => (
            <div
              key={session.id}
              className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors"
            >
              <div className="flex items-center space-x-4">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-xl ${getQualityColor(session.quality)}`}>
                  😴
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <p className="font-semibold text-slate-800">
                      {session.startTime} - {session.endTime}
                    </p>
                    <span className={`text-xs font-semibold px-2 py-1 rounded-full ${getQualityBadge(session.quality)}`}>
                      {session.quality}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {session.date} • {session.duration}
                    {session.wakeUps > 0 && ` • ${session.wakeUps} wake-up${session.wakeUps > 1 ? 's' : ''}`}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-slate-800">{session.duration}</p>
                <p className="text-xs text-slate-500">Duration</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SleepLogs;

