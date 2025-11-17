import React, { useState, useEffect } from 'react';
import { AlertCard } from '../components';
import wsService from '../services/WebSocketService';

/**
 * Alerts Page - Alert history and management
 */
function Alerts() {
  const [alerts, setAlerts] = useState([
    {
      id: 1,
      message: 'Baby crying detected in nursery',
      severity: 'critical',
      timestamp: '2:34 PM'
    },
    {
      id: 2,
      message: 'Adult movement detected',
      severity: 'warning',
      timestamp: '2:15 PM'
    },
    {
      id: 3,
      message: 'Baby woke up from nap',
      severity: 'info',
      timestamp: '1:45 PM'
    }
  ]);

  useEffect(() => {
    const handleAlert = (data) => {
      const newAlert = {
        id: Date.now(),
        message: data.message,
        severity: data.severity || 'info',
        timestamp: new Date().toLocaleTimeString()
      };

      setAlerts((prev) => [newAlert, ...prev]);
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
            Manage and review all system alerts
          </p>
        </div>
        <button
          onClick={() => setAlerts([])}
          className="px-6 py-2.5 bg-accent-500 text-white rounded-xl font-semibold hover:bg-accent-600 transition-all duration-200 shadow-soft hover:shadow-soft-lg"
        >
          Clear All
        </button>
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-soft">
        <div className="space-y-3">
          {alerts.length > 0 ? (
            alerts.map((alert) => <AlertCard key={alert.id} alert={alert} />)
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
      </div>
    </div>
  );
}

export default Alerts;

