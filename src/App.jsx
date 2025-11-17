import React, { useState, useEffect } from 'react';
import { TopNavigation } from './components';
import Dashboard from './pages/Dashboard';
import Alerts from './pages/Alerts';
import Settings from './pages/Settings';
import wsService from './services/WebSocketService';

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

  useEffect(() => {
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

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'alerts':
        return <Alerts />;
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
      <div className="flex-1 overflow-auto bg-gradient-to-br from-slate-50 via-white to-primary-50">
        {renderCurrentPage()}
      </div>
    </div>
  );
}

export default App;

