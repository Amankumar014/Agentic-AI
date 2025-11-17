import React, { useState, useEffect } from 'react';
import {
  StatusCard,
  VideoFeed,
  AlertCard,
  DailySummaryCard,
  ActivityItem
} from '../components';
import wsService from '../services/WebSocketService';

/**
 * Dashboard Page - Main monitoring dashboard with real-time updates
 */
function Dashboard({ config }) {
  const [status, setStatus] = useState({
    babyDetected: false,
    adultDetected: false,
    babyState: 'unknown',
    crying: false,
    lastUpdate: null
  });

  const [recentAlerts, setRecentAlerts] = useState([]);

  const [dailySummary] = useState({
    sleepHours: { value: '8.5h', change: 12 },
    wakePeriods: { value: '6', change: -8 },
    cryingTime: { value: '45m', change: -15 },
    adultVisits: { value: '12', change: 5 }
  });

  const [recentActivity] = useState([
    {
      id: 1,
      type: 'sleep',
      description: 'Baby fell asleep peacefully',
      time: '2:30 PM',
      duration: '2h ago'
    },
    {
      id: 2,
      type: 'adult',
      description: 'Parent entered nursery',
      time: '1:15 PM',
      duration: '3h ago'
    },
    {
      id: 3,
      type: 'wake',
      description: 'Baby woke up naturally',
      time: '12:45 PM',
      duration: '4h ago'
    },
    {
      id: 4,
      type: 'cry',
      description: 'Brief crying episode',
      time: '11:30 AM',
      duration: '5h ago'
    },
    {
      id: 5,
      type: 'feed',
      description: 'Feeding session completed',
      time: '10:00 AM',
      duration: '6h ago'
    }
  ]);

  useEffect(() => {
    const handleStatusUpdate = (data) => {
      setStatus((prev) => ({
        ...prev,
        ...data.status,
        lastUpdate: new Date().toLocaleTimeString()
      }));
    };

    const handleAlert = (data) => {
      const newAlert = {
        id: Date.now(),
        message: data.message,
        severity: data.severity || 'info',
        timestamp: new Date().toLocaleTimeString()
      };

      setRecentAlerts((prev) => [newAlert, ...prev.slice(0, 4)]);
    };

    wsService.subscribe('status_update', handleStatusUpdate);
    wsService.subscribe('alert', handleAlert);

    return () => {
      wsService.unsubscribe('status_update', handleStatusUpdate);
      wsService.unsubscribe('alert', handleAlert);
    };
  }, []);

  const getBabyStateText = () => {
    switch (status.babyState) {
      case 'sleeping':
        return 'Sleeping';
      case 'awake':
        return 'Awake';
      case 'distressed':
        return 'Distressed';
      default:
        return 'Unknown';
    }
  };

  const getBabyStateSeverity = () => {
    switch (status.babyState) {
      case 'sleeping':
        return 'success';
      case 'awake':
        return 'info';
      case 'distressed':
        return 'critical';
      default:
        return 'info';
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6 min-h-full">
      {/* Last Update Indicator */}
      {status.lastUpdate && (
        <div className="flex justify-end">
          <div className="flex items-center space-x-2 bg-white px-4 py-2 rounded-full shadow-soft">
            <div className="w-2 h-2 bg-primary-500 rounded-full pulse-animation"></div>
            <p className="text-xs font-medium text-slate-600">
              Last update: {status.lastUpdate}
            </p>
          </div>
        </div>
      )}

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Camera and Summary */}
        <div className="lg:col-span-2 space-y-6">
          {/* Video Feed */}
          <VideoFeed
            cameraUrl=""
            label={config.camera_label || 'Nursery Camera'}
          />

          {/* Daily Summary */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
              DAILY SUMMARY
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <DailySummaryCard
                title="Sleep"
                value={dailySummary.sleepHours.value}
                change={dailySummary.sleepHours.change}
                icon="😴"
                variant="primary"
              />
              <DailySummaryCard
                title="Feed"
                value={dailySummary.wakePeriods.value}
                change={dailySummary.wakePeriods.change}
                icon="🍼"
                variant="secondary"
              />
              <DailySummaryCard
                title="Diaper"
                value={dailySummary.cryingTime.value}
                change={dailySummary.cryingTime.change}
                icon="👶"
                variant="warning"
              />
              <DailySummaryCard
                title="Total Sleep"
                value={dailySummary.adultVisits.value}
                change={dailySummary.adultVisits.change}
                icon="💤"
                variant="accent"
              />
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex flex-wrap gap-3">
            <button className="flex items-center space-x-2 px-6 py-3 bg-white rounded-xl shadow-soft hover:shadow-soft-lg transition-all">
              <span className="text-lg">💡</span>
              <span className="text-sm font-semibold text-slate-700">NIGHT LIGHT</span>
              <div className="w-10 h-6 bg-primary-500 rounded-full relative">
                <div className="w-4 h-4 bg-white rounded-full absolute top-1 right-1"></div>
              </div>
            </button>
            <button className="flex items-center space-x-2 px-6 py-3 bg-white rounded-xl shadow-soft hover:shadow-soft-lg transition-all">
              <span className="text-lg">🎵</span>
              <span className="text-sm font-semibold text-slate-700">LULLABY</span>
            </button>
            <button className="flex items-center space-x-2 px-6 py-3 bg-white rounded-xl shadow-soft hover:shadow-soft-lg transition-all">
              <span className="text-lg">🔔</span>
              <span className="text-sm font-semibold text-slate-700">ALERTS</span>
              <span className="text-xs">→</span>
            </button>
          </div>
        </div>

        {/* Right Column - Monitoring Cards */}
        <div className="space-y-6">
          {/* Audio Monitor Card */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <span className="text-lg">🎤</span>
                <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                  Audio Monitor
                </h3>
              </div>
              <span className="text-lg">💧</span>
            </div>
            <div className="h-20 flex items-center justify-center bg-slate-50 rounded-xl">
              <div className="flex items-center space-x-1">
                {[...Array(20)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1 bg-primary-400 rounded-full"
                    style={{
                      height: `${Math.random() * 40 + 10}px`,
                      opacity: 0.3 + Math.random() * 0.5
                    }}
                  ></div>
                ))}
              </div>
            </div>
          </div>

          {/* Temperature & Humidity */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <span className="text-lg">🌡</span>
                <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                  Temperature & Humidity
                </h3>
              </div>
              <span className="text-lg">💨</span>
            </div>
            <div className="flex items-center justify-center space-x-4 my-6">
              <div className="text-center">
                <div className="text-4xl font-bold text-slate-700">72°F</div>
                <div className="text-xs text-slate-500 mt-1">Temperature</div>
              </div>
              <button className="w-16 h-16 bg-primary-400 hover:bg-primary-500 rounded-full flex items-center justify-center text-white font-semibold text-sm transition-colors">
                LISTEN<br/>IN
              </button>
              <div className="text-center">
                <div className="text-4xl font-bold text-slate-700">45%</div>
                <div className="text-xs text-slate-500 mt-1">Humidity</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-center text-xs text-slate-500">
              <div>
                <div className="h-8 flex items-end justify-around">
                  <div className="w-4 h-4 bg-primary-200 rounded"></div>
                  <div className="w-4 h-5 bg-primary-200 rounded"></div>
                  <div className="w-4 h-6 bg-primary-200 rounded"></div>
                </div>
                <div className="mt-1">10H - 12H - 20H</div>
              </div>
              <div>
                <div className="h-8 flex items-end justify-around">
                  <div className="w-4 h-6 bg-slate-200 rounded"></div>
                  <div className="w-4 h-5 bg-slate-200 rounded"></div>
                  <div className="w-4 h-4 bg-slate-200 rounded"></div>
                </div>
                <div className="mt-1">0H - 5H - 10H</div>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
              RECENT ACTIVITY
            </h3>
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {recentActivity.map((activity) => (
                <ActivityItem key={activity.id} activity={activity} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

