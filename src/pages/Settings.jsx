import React, { useState } from 'react';
import wsService from '../services/WebSocketService';

/**
 * Settings Page - System configuration and monitoring controls
 */
function Settings() {
  const [settings, setSettings] = useState({
    cameraUrl: '',
    alertCooldown: 30,
    monitoringEnabled: false,
    babyDetection: true,
    adultDetection: true,
    cryingDetection: true
  });

  const [isMonitoring, setIsMonitoring] = useState(false);

  const handleInputChange = (field, value) => {
    setSettings((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleStartMonitoring = () => {
    setIsMonitoring(true);
    wsService.send({
      type: 'start_monitoring',
      settings: settings
    });
  };

  const handleStopMonitoring = () => {
    setIsMonitoring(false);
    wsService.send({
      type: 'stop_monitoring'
    });
  };

  const showSuccessNotification = (message) => {
    const successDiv = document.createElement('div');
    successDiv.className =
      'fixed top-8 right-8 glass-effect text-white px-8 py-4 rounded-2xl fade-in shadow-2xl neon-glow z-50';
    successDiv.innerHTML = `<div class="flex items-center space-x-3"><span class="text-2xl">✅</span><span class="font-bold">${message}</span></div>`;
    document.body.appendChild(successDiv);

    setTimeout(() => {
      if (document.body.contains(successDiv)) {
        document.body.removeChild(successDiv);
      }
    }, 3000);
  };

  const handleSaveSettings = () => {
    // Simulate API call
    console.log('Saving settings:', settings);
    showSuccessNotification('Settings saved successfully!');
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-800 mb-1">
          Settings
        </h2>
        <p className="text-slate-500 text-sm">
          Configure your monitoring preferences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Camera Configuration */}
        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-10 h-10 bg-secondary-100 rounded-xl flex items-center justify-center text-xl">
              📹
            </div>
            <h3 className="text-lg font-semibold text-slate-800">
              Camera Configuration
            </h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-2 uppercase tracking-wide">
                Camera URL
              </label>
              <input
                type="url"
                value={settings.cameraUrl}
                onChange={(e) => handleInputChange('cameraUrl', e.target.value)}
                placeholder="http://192.168.1.100:8080/video"
                className="w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-2 uppercase tracking-wide">
                Alert Cooldown (seconds)
              </label>
              <input
                type="number"
                value={settings.alertCooldown}
                onChange={(e) =>
                  handleInputChange('alertCooldown', parseInt(e.target.value))
                }
                min="5"
                max="300"
                className="w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all text-sm"
              />
            </div>
          </div>
        </div>

        {/* Detection Settings */}
        <div className="bg-white rounded-2xl p-6 shadow-soft">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center text-xl">
              🎯
            </div>
            <h3 className="text-lg font-semibold text-slate-800">
              Detection Settings
            </h3>
          </div>

          <div className="space-y-3">
            <label className="flex items-center p-3 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer">
              <input
                type="checkbox"
                checked={settings.babyDetection}
                onChange={(e) =>
                  handleInputChange('babyDetection', e.target.checked)
                }
                className="w-5 h-5 rounded border-2 border-slate-300 text-primary-600 focus:ring-primary-500 focus:ring-2 focus:ring-primary-500/20"
              />
              <span className="ml-3 text-sm font-semibold text-slate-700">
                Baby Detection
              </span>
            </label>
            <label className="flex items-center p-3 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer">
              <input
                type="checkbox"
                checked={settings.adultDetection}
                onChange={(e) =>
                  handleInputChange('adultDetection', e.target.checked)
                }
                className="w-5 h-5 rounded border-2 border-slate-300 text-primary-600 focus:ring-primary-500 focus:ring-2 focus:ring-primary-500/20"
              />
              <span className="ml-3 text-sm font-semibold text-slate-700">
                Adult Detection
              </span>
            </label>
            <label className="flex items-center p-3 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer">
              <input
                type="checkbox"
                checked={settings.cryingDetection}
                onChange={(e) =>
                  handleInputChange('cryingDetection', e.target.checked)
                }
                className="w-5 h-5 rounded border-2 border-slate-300 text-primary-600 focus:ring-primary-500 focus:ring-2 focus:ring-primary-500/20"
              />
              <span className="ml-3 text-sm font-semibold text-slate-700">
                Crying Detection
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Monitoring Control */}
      <div className="bg-white rounded-2xl p-6 shadow-soft">
        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center text-xl">
            ⚡
          </div>
          <h3 className="text-lg font-semibold text-slate-800">
            Monitoring Control
          </h3>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleStartMonitoring}
            disabled={isMonitoring}
            className={`px-6 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200 shadow-soft ${
              isMonitoring
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-primary-500 text-white hover:bg-primary-600 hover:shadow-soft-lg'
            }`}
          >
            {isMonitoring ? '🟢 Monitoring Active' : '▶️ Start Monitoring'}
          </button>
          <button
            onClick={handleStopMonitoring}
            disabled={!isMonitoring}
            className={`px-6 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200 shadow-soft ${
              !isMonitoring
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-accent-500 text-white hover:bg-accent-600 hover:shadow-soft-lg'
            }`}
          >
            ⏹️ Stop Monitoring
          </button>
          <button
            onClick={handleSaveSettings}
            className="px-6 py-2.5 bg-secondary-500 text-white rounded-xl font-semibold text-sm hover:bg-secondary-600 transition-all duration-200 shadow-soft hover:shadow-soft-lg"
          >
            💾 Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}

export default Settings;

