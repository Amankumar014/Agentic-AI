import React, { useState } from 'react';
import wsService from '../services/WebSocketService';
import { rebuildChatbotIndex, formatErrorMessage } from '../services/ApiService';

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
  const [rebuildState, setRebuildState] = useState({
    rebuilding: false,
    result: null,
    error: null
  });
  const [showAdminSection, setShowAdminSection] = useState(false);

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

  const handleRebuildChatbotIndex = async () => {
    if (!window.confirm('Are you sure you want to rebuild the chatbot index? This may take a few minutes.')) {
      return;
    }

    setRebuildState({ rebuilding: true, result: null, error: null });

    try {
      const result = await rebuildChatbotIndex();
      
      if (result.status === 'success') {
        setRebuildState({ 
          rebuilding: false, 
          result: result, 
          error: null 
        });
        showSuccessNotification('Chatbot index rebuilt successfully!');
      }
    } catch (error) {
      console.error('Error rebuilding chatbot index:', error);
      setRebuildState({ 
        rebuilding: false, 
        result: null, 
        error: formatErrorMessage(error) 
      });
    }
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

      {/* Admin Section */}
      <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl p-6 shadow-soft border-2 border-purple-200 mt-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-purple-500 rounded-xl flex items-center justify-center text-xl">
              🔐
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-800">
                Admin Settings
              </h3>
              <p className="text-xs text-slate-600">Advanced features for administrators</p>
            </div>
          </div>
          <button
            onClick={() => setShowAdminSection(!showAdminSection)}
            className="px-4 py-2 bg-purple-500 text-white rounded-lg text-sm font-semibold hover:bg-purple-600 transition-colors"
          >
            {showAdminSection ? '🔼 Hide' : '🔽 Show'}
          </button>
        </div>

        {showAdminSection && (
          <div className="mt-4 space-y-4">
            {/* Chatbot Index Rebuild */}
            <div className="bg-white rounded-xl p-5 border border-purple-200">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-slate-800 mb-1">
                    🤖 Rebuild Chatbot Index
                  </h4>
                  <p className="text-xs text-slate-600 mb-3">
                    Rebuilds the RAG knowledge base index from documents. Use this after updating or adding new documents.
                  </p>

                  {rebuildState.error && (
                    <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                      ❌ {rebuildState.error}
                    </div>
                  )}

                  {rebuildState.result && (
                    <div className="mb-3 p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-700">
                      <p className="font-semibold mb-2">✅ Index rebuilt successfully!</p>
                      <div className="space-y-1">
                        <p>• Documents: {rebuildState.result.num_documents}</p>
                        <p>• Pages: {rebuildState.result.num_pages}</p>
                        <p>• Chunks: {rebuildState.result.num_chunks}</p>
                        <p>• Embedding Dimension: {rebuildState.result.embedding_dimension}</p>
                        <p>• Build Time: {rebuildState.result.build_time_seconds?.toFixed(2)}s</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={handleRebuildChatbotIndex}
                disabled={rebuildState.rebuilding}
                className="w-full px-4 py-3 bg-purple-500 text-white rounded-lg font-semibold hover:bg-purple-600 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
              >
                {rebuildState.rebuilding ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>⏳ Rebuilding Index...</span>
                  </>
                ) : (
                  <>
                    <span>🔨 Rebuild Chatbot Index</span>
                  </>
                )}
              </button>
            </div>

            {/* API Configuration Info */}
            <div className="bg-white rounded-xl p-5 border border-purple-200">
              <h4 className="text-sm font-semibold text-slate-800 mb-2">
                🌐 Backend Configuration
              </h4>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                  <span className="text-slate-600">API Base URL:</span>
                  <code className="font-mono text-purple-600 bg-purple-50 px-2 py-1 rounded">
                    {process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'}
                  </code>
                </div>
                <p className="text-slate-500 italic mt-2">
                  To change the backend URL, update REACT_APP_API_BASE_URL in your .env file and restart the application.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Settings;

