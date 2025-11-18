import React, { useState, useEffect } from 'react';
import { VideoFeed, StatusCard } from '../components';
import wsService from '../services/WebSocketService';

/**
 * LiveFeed Page - Dedicated live camera feed monitoring
 */
function LiveFeed({ config }) {
  const [status, setStatus] = useState({
    babyDetected: false,
    adultDetected: false,
    babyState: 'unknown',
    crying: false,
    lastUpdate: null
  });

  const [cameraControls, setCameraControls] = useState({
    zoom: 1,
    brightness: 100,
    nightMode: false,
    recording: false
  });

  useEffect(() => {
    const handleStatusUpdate = (data) => {
      setStatus((prev) => ({
        ...prev,
        ...data.status,
        lastUpdate: new Date().toLocaleTimeString()
      }));
    };

    wsService.subscribe('status_update', handleStatusUpdate);

    return () => {
      wsService.unsubscribe('status_update', handleStatusUpdate);
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Live Camera Feed</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time monitoring of {config?.camera_label || 'Nursery Camera'}
          </p>
        </div>
        {status.lastUpdate && (
          <div className="flex items-center space-x-2 bg-white px-4 py-2 rounded-full shadow-soft">
            <div className="w-2 h-2 bg-primary-500 rounded-full pulse-animation"></div>
            <p className="text-xs font-medium text-slate-600">
              Last update: {status.lastUpdate}
            </p>
          </div>
        )}
      </div>

      {/* Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Video Feed - Takes 3 columns */}
        <div className="lg:col-span-3 space-y-6">
          {/* Enhanced Video Feed */}
          <div className="bg-white rounded-2xl overflow-hidden shadow-soft">
            <VideoFeed
              cameraUrl=""
              label={config?.camera_label || 'Nursery Camera'}
            />
            
            {/* Camera Controls Overlay */}
            <div className="bg-slate-50 px-6 py-4 border-t border-slate-200">
              <div className="flex items-center justify-between flex-wrap gap-4">
                {/* Zoom Control */}
                <div className="flex items-center space-x-3">
                  <span className="text-sm font-semibold text-slate-700">Zoom:</span>
                  <input
                    type="range"
                    min="1"
                    max="3"
                    step="0.1"
                    value={cameraControls.zoom}
                    onChange={(e) => setCameraControls(prev => ({ ...prev, zoom: parseFloat(e.target.value) }))}
                    className="w-24 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="text-xs text-slate-600 w-8">{cameraControls.zoom}x</span>
                </div>

                {/* Brightness Control */}
                <div className="flex items-center space-x-3">
                  <span className="text-sm font-semibold text-slate-700">Brightness:</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={cameraControls.brightness}
                    onChange={(e) => setCameraControls(prev => ({ ...prev, brightness: parseInt(e.target.value) }))}
                    className="w-24 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="text-xs text-slate-600 w-8">{cameraControls.brightness}%</span>
                </div>

                {/* Night Mode Toggle */}
                <button
                  onClick={() => setCameraControls(prev => ({ ...prev, nightMode: !prev.nightMode }))}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                    cameraControls.nightMode
                      ? 'bg-indigo-500 text-white'
                      : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <span>🌙</span>
                  <span className="text-sm font-semibold">Night Mode</span>
                </button>

                {/* Recording Toggle */}
                <button
                  onClick={() => setCameraControls(prev => ({ ...prev, recording: !prev.recording }))}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                    cameraControls.recording
                      ? 'bg-red-500 text-white'
                      : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${cameraControls.recording ? 'bg-white animate-pulse' : 'bg-slate-400'}`}></span>
                  <span className="text-sm font-semibold">
                    {cameraControls.recording ? 'Recording' : 'Record'}
                  </span>
                </button>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
              Quick Actions
            </h3>
            <div className="flex flex-wrap gap-3">
              <button className="flex items-center space-x-2 px-6 py-3 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all shadow-soft">
                <span className="text-lg">📸</span>
                <span className="text-sm font-semibold text-slate-700">Capture Snapshot</span>
              </button>
              <button className="flex items-center space-x-2 px-6 py-3 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all shadow-soft">
                <span className="text-lg">🔊</span>
                <span className="text-sm font-semibold text-slate-700">Two-Way Audio</span>
              </button>
              <button className="flex items-center space-x-2 px-6 py-3 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all shadow-soft">
                <span className="text-lg">💡</span>
                <span className="text-sm font-semibold text-slate-700">Night Light</span>
              </button>
              <button className="flex items-center space-x-2 px-6 py-3 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all shadow-soft">
                <span className="text-lg">🎵</span>
                <span className="text-sm font-semibold text-slate-700">Play Lullaby</span>
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar - Status Cards */}
        <div className="space-y-6">
          {/* Baby Status */}
          <StatusCard
            title="Baby Status"
            status={getBabyStateText()}
            isActive={status.babyDetected}
            severity={getBabyStateSeverity()}
            icon="👶"
          />

          {/* Adult Detection */}
          <StatusCard
            title="Adult Present"
            status={status.adultDetected ? 'Yes' : 'No'}
            isActive={status.adultDetected}
            severity={status.adultDetected ? 'info' : 'info'}
            icon="👤"
          />

          {/* Crying Detection */}
          <StatusCard
            title="Crying Detection"
            status={status.crying ? 'Detected' : 'None'}
            isActive={status.crying}
            severity={status.crying ? 'critical' : 'success'}
            icon="😢"
          />

          {/* Connection Status */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
              Connection Status
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Camera</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full pulse-animation"></div>
                  <span className="text-xs font-semibold text-green-600">Connected</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Audio</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full pulse-animation"></div>
                  <span className="text-xs font-semibold text-green-600">Active</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">WebSocket</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full pulse-animation"></div>
                  <span className="text-xs font-semibold text-green-600">Live</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LiveFeed;

