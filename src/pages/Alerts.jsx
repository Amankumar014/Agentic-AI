import React, { useState, useEffect } from 'react';
import { AlertCard } from '../components';
import wsService from '../services/WebSocketService';
import { getAlerts, formatErrorMessage } from '../services/ApiService';

/**
 * Alerts Page - Alert history and management
 */
function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(50);
  const [totalCount, setTotalCount] = useState(0);

  // Load alerts from API
  useEffect(() => {
    loadAlerts();
  }, [limit]);

  const loadAlerts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await getAlerts(limit);
      
      if (response.status === 'success') {
        // Format alerts for display
        const formattedAlerts = response.alerts.map(alert => ({
          id: alert.id,
          message: alert.message,
          severity: alert.alert_type === 'high_risk_position' ? 'critical' : 
                    alert.alert_type === 'unusual_behavior' ? 'warning' : 'info',
          timestamp: new Date(alert.timestamp).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          }),
          fullTimestamp: alert.timestamp,
          alertType: alert.alert_type,
          delivered: alert.delivered
        }));
        
        setAlerts(formattedAlerts);
        setTotalCount(response.count);
      }
    } catch (err) {
      console.error('Error loading alerts:', err);
      setError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // Subscribe to real-time alerts via WebSocket
  useEffect(() => {
    const handleAlert = (data) => {
      const newAlert = {
        id: Date.now(),
        message: data.message,
        severity: data.severity || 'info',
        timestamp: new Date().toLocaleTimeString(),
        fullTimestamp: new Date().toISOString(),
        alertType: data.alert_type || 'general',
        delivered: false
      };

      setAlerts((prev) => [newAlert, ...prev]);
      setTotalCount(prev => prev + 1);
    };

    wsService.subscribe('alert', handleAlert);

    return () => {
      wsService.unsubscribe('alert', handleAlert);
    };
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-1">
            Alert History
          </h2>
          <p className="text-slate-500 text-sm">
            Manage and review all system alerts {totalCount > 0 && `(${totalCount} total)`}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {/* Limit Selector */}
          <select
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value))}
            className="px-4 py-2.5 bg-white border border-slate-300 rounded-xl font-semibold text-sm hover:border-slate-400 transition-all"
          >
            <option value={10}>Last 10</option>
            <option value={50}>Last 50</option>
            <option value={100}>Last 100</option>
            <option value={200}>Last 200</option>
          </select>
          
          {/* Refresh Button */}
          <button
            onClick={loadAlerts}
            disabled={loading}
            className="px-6 py-2.5 bg-primary-500 text-white rounded-xl font-semibold hover:bg-primary-600 transition-all duration-200 shadow-soft hover:shadow-soft-lg disabled:bg-slate-300 disabled:cursor-not-allowed"
          >
            {loading ? '⏳ Loading...' : '🔄 Refresh'}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <p className="font-semibold">❌ Error loading alerts</p>
          <p className="text-sm mt-1">{error}</p>
          <button 
            onClick={loadAlerts}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Alerts List */}
      <div className="bg-white rounded-2xl p-6 shadow-soft">
        {loading ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-slate-600 font-semibold">Loading alerts...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.length > 0 ? (
              alerts.map((alert) => (
                <div key={alert.id} className="relative">
                  <AlertCard alert={alert} />
                  {/* Delivery Status Indicator */}
                  {alert.delivered !== undefined && (
                    <div className="absolute top-4 right-4">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        alert.delivered 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {alert.delivered ? '✓ Delivered' : '⏳ Pending'}
                      </span>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-16">
                <div className="w-20 h-20 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <span className="text-4xl">📋</span>
                </div>
                <p className="text-slate-700 font-semibold text-lg mb-2">
                  No Alerts Found
                </p>
                <p className="text-slate-500 text-sm">
                  Your alert history is currently empty
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Alerts;

