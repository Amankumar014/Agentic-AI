import React, { useState, useEffect, useRef } from 'react';
import { VideoFeed, StatusCard } from '../components';
import wsService from '../services/WebSocketService';
import { uploadFrame, uploadFrameWithAudio, formatErrorMessage, getStreamUrl } from '../services/ApiService';

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

  const [uploadState, setUploadState] = useState({
    uploading: false,
    error: null,
    lastAnalysis: null
  });

  const [alertBanner, setAlertBanner] = useState(null);
  const fileInputRef = useRef(null);
  const audioInputRef = useRef(null);

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

  const handleFrameUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadState({ uploading: true, error: null, lastAnalysis: null });
    setAlertBanner(null);

    try {
      const response = await uploadFrame(file);
      
      setUploadState({ 
        uploading: false, 
        error: null, 
        lastAnalysis: response 
      });

      // Update status from analysis
      if (response.analysis) {
        setStatus(prev => ({
          ...prev,
          babyDetected: response.analysis.baby_detected || false,
          babyState: response.analysis.risk || 'unknown',
          lastUpdate: new Date().toLocaleTimeString()
        }));
      }

      // Show alert banner if alert is triggered
      if (response.alert) {
        setAlertBanner({
          message: response.alert_reason || 'Alert triggered',
          severity: 'critical'
        });
      }
    } catch (error) {
      console.error('Error uploading frame:', error);
      setUploadState({ 
        uploading: false, 
        error: formatErrorMessage(error), 
        lastAnalysis: null 
      });
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFrameWithAudioUpload = async () => {
    const imageFile = fileInputRef.current?.files?.[0];
    const audioFile = audioInputRef.current?.files?.[0];

    if (!imageFile || !audioFile) {
      alert('Please select both an image and audio file');
      return;
    }

    setUploadState({ uploading: true, error: null, lastAnalysis: null });
    setAlertBanner(null);

    try {
      const response = await uploadFrameWithAudio(imageFile, audioFile);
      
      setUploadState({ 
        uploading: false, 
        error: null, 
        lastAnalysis: response 
      });

      // Update status from analysis
      if (response.analysis) {
        setStatus(prev => ({
          ...prev,
          babyDetected: response.analysis.baby_detected || false,
          babyState: response.analysis.risk || 'unknown',
          crying: response.audio?.crying_detected || false,
          lastUpdate: new Date().toLocaleTimeString()
        }));
      }

      // Show alert banner if alert is triggered
      if (response.alert) {
        setAlertBanner({
          message: response.alert_reason || 'Alert triggered',
          severity: 'critical'
        });
      }
    } catch (error) {
      console.error('Error uploading frame with audio:', error);
      setUploadState({ 
        uploading: false, 
        error: formatErrorMessage(error), 
        lastAnalysis: null 
      });
    }

    // Reset file inputs
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (audioInputRef.current) audioInputRef.current.value = '';
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

      {/* Alert Banner */}
      {alertBanner && (
        <div className={`p-4 rounded-xl border-2 ${
          alertBanner.severity === 'critical' 
            ? 'bg-red-50 border-red-300 text-red-800' 
            : 'bg-yellow-50 border-yellow-300 text-yellow-800'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="font-bold">Alert Triggered</p>
                <p className="text-sm">{alertBanner.message}</p>
              </div>
            </div>
            <button 
              onClick={() => setAlertBanner(null)}
              className="text-2xl hover:opacity-70"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Video Feed - Takes 3 columns */}
        <div className="lg:col-span-3 space-y-6">
          {/* Enhanced Video Feed */}
          <div className="bg-white rounded-2xl overflow-hidden shadow-soft">
            <VideoFeed
              cameraUrl={getStreamUrl()}
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

          {/* Frame Upload & Analysis */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
              Upload Frame for Analysis
            </h3>
            
            {uploadState.error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                ❌ {uploadState.error}
              </div>
            )}

            <div className="space-y-4">
              {/* Single Frame Upload */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Upload Image Only
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/jpg"
                  onChange={handleFrameUpload}
                  disabled={uploadState.uploading}
                  className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 disabled:opacity-50"
                />
                <p className="text-xs text-slate-500 mt-1">Max 10 MB (JPEG/PNG)</p>
              </div>

              {/* Frame + Audio Upload */}
              <div className="pt-4 border-t border-slate-200">
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Upload Image + Audio
                </label>
                <div className="space-y-2">
                  <input
                    type="file"
                    accept="audio/*"
                    ref={audioInputRef}
                    disabled={uploadState.uploading}
                    className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-secondary-50 file:text-secondary-700 hover:file:bg-secondary-100 disabled:opacity-50"
                  />
                  <button
                    onClick={handleFrameWithAudioUpload}
                    disabled={uploadState.uploading}
                    className="w-full px-4 py-2 bg-primary-500 text-white rounded-lg font-semibold hover:bg-primary-600 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
                  >
                    {uploadState.uploading ? '⏳ Analyzing...' : '🎤 Analyze with Audio'}
                  </button>
                </div>
                <p className="text-xs text-slate-500 mt-1">Max 10 MB each file</p>
              </div>

              {/* Analysis Result */}
              {uploadState.lastAnalysis && (
                <div className="mt-4 p-4 bg-slate-50 rounded-lg">
                  <h4 className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wide">
                    Analysis Result
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-600">Baby Detected:</span>
                      <span className="font-semibold">
                        {uploadState.lastAnalysis.analysis?.baby_detected ? '✅ Yes' : '❌ No'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">Risk Level:</span>
                      <span className={`font-semibold ${
                        uploadState.lastAnalysis.analysis?.risk === 'high' ? 'text-red-600' :
                        uploadState.lastAnalysis.analysis?.risk === 'medium' ? 'text-yellow-600' :
                        'text-green-600'
                      }`}>
                        {uploadState.lastAnalysis.analysis?.risk || 'Unknown'}
                      </span>
                    </div>
                    {uploadState.lastAnalysis.analysis?.position && (
                      <div className="flex justify-between">
                        <span className="text-slate-600">Position:</span>
                        <span className="font-semibold">{uploadState.lastAnalysis.analysis.position}</span>
                      </div>
                    )}
                    {uploadState.lastAnalysis.audio && (
                      <div className="flex justify-between">
                        <span className="text-slate-600">Crying:</span>
                        <span className="font-semibold">
                          {uploadState.lastAnalysis.audio.crying_detected ? '😢 Yes' : '😊 No'}
                        </span>
                      </div>
                    )}
                    {uploadState.lastAnalysis.log_id && (
                      <div className="mt-2 pt-2 border-t border-slate-200">
                        <span className="text-xs text-slate-500">Log ID: {uploadState.lastAnalysis.log_id}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-2xl p-6 shadow-soft">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">
              Quick Actions
            </h3>
            <div className="flex flex-wrap gap-3">
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center space-x-2 px-6 py-3 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all shadow-soft"
              >
                <span className="text-lg">📸</span>
                <span className="text-sm font-semibold text-slate-700">Upload Snapshot</span>
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

