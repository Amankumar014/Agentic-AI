import React, { useState, useEffect } from 'react';
import {
  StatusCard,
  VideoFeed,
  AlertCard,
  DailySummaryCard,
  ActivityItem,
  DetectionLegend,
  DetectionMonitor,
  AudioMonitor
} from '../components';
import wsService from '../services/WebSocketService';
import { getStats, getAlerts, getStreamUrl, getAnnotatedStreamUrl } from '../services/ApiService';

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
  const [statsData, setStatsData] = useState(null);
  const [statsError, setStatsError] = useState(null);
  const [showAnnotations, setShowAnnotations] = useState(true);

  const [dailySummary, setDailySummary] = useState({
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

  // Load initial stats and alerts from API
  useEffect(() => {
    loadStatsAndAlerts();
    // Refresh stats every 30 seconds
    const interval = setInterval(loadStatsAndAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStatsAndAlerts = async () => {
    // Load stats
    try {
      const stats = await getStats();
      if (stats.status === 'success') {
        setStatsData(stats.stats);
        setStatsError(null);
        
        // Update daily summary with real data
        setDailySummary({
          sleepHours: { 
            value: stats.stats.frames_last_24h || 0, 
            change: 12 
          },
          wakePeriods: { 
            value: stats.stats.baby_detected_count || 0, 
            change: -8 
          },
          cryingTime: { 
            value: stats.stats.alerts_last_24h || 0, 
            change: -15 
          },
          adultVisits: { 
            value: stats.stats.total_frames_analyzed || 0, 
            change: 5 
          }
        });
      }
    } catch (error) {
      console.error('Error loading stats:', error);
      setStatsError(error);
    }

    // Load recent alerts
    try {
      const alertsData = await getAlerts(5);
      if (alertsData.status === 'success' && alertsData.alerts) {
        const formattedAlerts = alertsData.alerts.map(alert => ({
          id: alert.id,
          message: alert.message,
          severity: alert.alert_type === 'high_risk_position' ? 'critical' : 'warning',
          timestamp: new Date(alert.timestamp).toLocaleTimeString(),
          delivered: alert.delivered
        }));
        setRecentAlerts(formattedAlerts);
      }
    } catch (error) {
      console.error('Error loading alerts:', error);
    }
  };

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
            cameraUrl={showAnnotations ? getAnnotatedStreamUrl() : getStreamUrl()}
            label={config.camera_label || 'Nursery Camera'}
            showAnnotations={showAnnotations}
            onToggleAnnotations={() => setShowAnnotations(!showAnnotations)}
          />

          {/* Detection Legend */}
          {showAnnotations && <DetectionLegend />}

          {/* Daily Summary */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                SYSTEM STATISTICS
              </h3>
              {statsError && (
                <span className="text-xs text-red-500">⚠️ Error loading stats</span>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <DailySummaryCard
                title="Frames (24h)"
                value={statsData?.frames_last_24h?.toString() || '0'}
                change={dailySummary.sleepHours.change}
                icon="📸"
                variant="primary"
              />
              <DailySummaryCard
                title="Baby Detected"
                value={statsData?.baby_detected_count?.toString() || '0'}
                change={dailySummary.wakePeriods.change}
                icon="👶"
                variant="secondary"
              />
              <DailySummaryCard
                title="Alerts (24h)"
                value={statsData?.alerts_last_24h?.toString() || '0'}
                change={dailySummary.cryingTime.change}
                icon="🔔"
                variant="warning"
              />
              <DailySummaryCard
                title="Total Analyzed"
                value={statsData?.total_frames_analyzed?.toString() || '0'}
                change={dailySummary.adultVisits.change}
                icon="📊"
                variant="accent"
              />
            </div>
            
            {/* Risk Level Distribution */}
            {statsData && statsData.risk_level_distribution && (
              <div className="mt-4 p-4 bg-slate-50 rounded-xl">
                <h4 className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wide">
                  Risk Level Distribution
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {Object.entries(statsData.risk_level_distribution).map(([level, count]) => (
                    <div key={level} className="text-center">
                      <div className={`text-2xl font-bold ${
                        level === 'high' ? 'text-red-600' :
                        level === 'medium' ? 'text-yellow-600' :
                        level === 'low' ? 'text-green-600' :
                        'text-slate-600'
                      }`}>
                        {count}
                      </div>
                      <div className="text-xs text-slate-500 capitalize mt-1">{level}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
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
          {/* Real-Time Detection Monitor */}
          <DetectionMonitor enablePollingFallback={true} autoConnect={true} />

          {/* Real-Time Audio Monitor */}
          <AudioMonitor enablePollingFallback={true} autoConnect={true} />

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
