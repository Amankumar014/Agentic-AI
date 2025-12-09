import React, { useState, useEffect } from 'react';
import { TopNavigation, Chatbot } from './components';
import Dashboard from './pages/Dashboard';
import Alerts from './pages/Alerts';
import Settings from './pages/Settings';
import LiveFeed from './pages/LiveFeed';
import SleepLogs from './pages/SleepLogs';
import Activity from './pages/Activity';
import Payment from './pages/Payment';
import wsService from './services/WebSocketService';
import { checkHealth, getBaseUrl } from './services/ApiService';

/**
 * Main App Component
 */
function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [config, setConfig] = useState({
    app_title: 'LALLA CARE',
    camera_label: 'Nursery Camera',
    baby_detected_text: 'Baby Detected',
    adult_detected_text: 'Adult Present'
  });
  const [healthStatus, setHealthStatus] = useState({
    status: 'checking',
    message: 'Connecting to backend...',
    timestamp: null
  });

  useEffect(() => {
    // Check backend health on startup
    performHealthCheck();

    // Connect to WebSocket on app start
    wsService.connect();

    // Listen for config updates
    const handleConfigUpdate = (event) => {
      setConfig((prev) => ({ ...prev, ...event.detail }));
    };

    window.addEventListener('configUpdate', handleConfigUpdate);

    return () => {
      wsService.disconnect();
      window.removeEventListener('configUpdate', handleConfigUpdate);
    };
  }, []);

  const performHealthCheck = async () => {
    try {
      const health = await checkHealth();
      
      if (health.status === 'ok') {
        setHealthStatus({
          status: 'online',
          message: `Backend is online (${health.service} v${health.version})`,
          timestamp: health.time,
          service: health.service,
          version: health.version
        });
        console.log('✅ Backend health check passed:', health);
      } else {
        setHealthStatus({
          status: 'warning',
          message: 'Backend responded but status is not OK',
          timestamp: health.time
        });
        console.warn('⚠️ Backend health check warning:', health);
      }
    } catch (error) {
      console.error('❌ Backend health check failed:', error);
      setHealthStatus({
        status: 'offline',
        message: `Unable to connect to backend at ${getBaseUrl()}. Please check if the backend is running.`,
        timestamp: new Date().toISOString()
      });
    }
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'live':
        return <LiveFeed config={config} />;
      case 'sleep':
        return <SleepLogs />;
      case 'activity':
        return <Activity />;
      case 'alerts':
        return <Alerts />;
      case 'payment':
        return <Payment />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard config={config} />;
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TopNavigation
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        appTitle={config.app_title}
      />
      
      {/* Health Status Banner */}
      {healthStatus.status === 'offline' && (
        <div className="bg-red-500 text-white px-6 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-xl">⚠️</span>
            <div>
              <p className="font-semibold">Backend Offline</p>
              <p className="text-sm opacity-90">{healthStatus.message}</p>
            </div>
          </div>
          <button 
            onClick={performHealthCheck}
            className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-semibold transition-colors"
          >
            Retry Connection
          </button>
        </div>
      )}
      
      {healthStatus.status === 'checking' && (
        <div className="bg-blue-500 text-white px-6 py-2 flex items-center justify-center">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm font-semibold">{healthStatus.message}</span>
          </div>
        </div>
      )}
      
      <div className="flex-1 overflow-auto bg-gradient-to-br from-slate-50 via-white to-primary-50">
        {renderCurrentPage()}
      </div>
      
      {/* Chatbot - Available on all pages */}
      <Chatbot />
    </div>
  );
}

export default App;

