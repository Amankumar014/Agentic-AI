import React, { useState, useEffect, useRef } from 'react';
import wsService from '../../services/WebSocketService';
import { getLatestDetection, getDetectionWebSocketUrl } from '../../services/ApiService';

/**
 * DetectionMonitor Component - Real-time baby monitoring detection display
 * Connects to WebSocket and displays all detection metrics with visual indicators
 */
function DetectionMonitor({ enablePollingFallback = true, autoConnect = true }) {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [detectionData, setDetectionData] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const mountedRef = useRef(true);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    mountedRef.current = true;

    // Set up WebSocket connection
    if (autoConnect) {
      wsService.setPollingFallback(enablePollingFallback);
      const wsUrl = getDetectionWebSocketUrl();
      wsService.connect(wsUrl);
      setIsLoading(true);
    }

    // Subscribe to connection status updates
    const handleConnection = (data) => {
      if (!mountedRef.current) return;
      
      setConnectionStatus(data.status);
      
      if (data.status === 'connected') {
        setError(null);
        setReconnectAttempt(0);
      } else if (data.status === 'reconnecting') {
        setReconnectAttempt(data.attempt || 0);
      } else if (data.status === 'failed') {
        setError(data.message || 'Connection failed');
      }
    };

  // Subscribe to detection data updates
  const handleDetection = (data) => {
    if (!mountedRef.current) return;
    
    // Debug: Log detection data to see what backend is sending
    console.log('🔍 Detection Data Received:', {
      summary: data.summary,
      iris_tracking: {
        closure_pattern: data.iris_tracking?.closure_pattern,
        eyes_state: data.iris_tracking?.eyes_state,
        eye_openness: data.iris_tracking?.eye_openness,
        face_detected: data.iris_tracking?.face_detected
      },
      combined_facial_state: data.combined_facial_state
    });
    
    setDetectionData(data);
    setLastUpdate(new Date());
    setError(null);
    setIsLoading(false);
  };

    // Subscribe to errors
    const handleError = (data) => {
      if (!mountedRef.current) return;
      setError(data.error?.message || 'Connection error');
    };

    wsService.subscribe('connection', handleConnection);
    wsService.subscribe('detection', handleDetection);
    wsService.subscribe('error', handleError);
    wsService.subscribe('parse_error', handleError);

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;
      wsService.unsubscribe('connection', handleConnection);
      wsService.unsubscribe('detection', handleDetection);
      wsService.unsubscribe('error', handleError);
      wsService.unsubscribe('parse_error', handleError);
      
      if (autoConnect) {
        wsService.disconnect();
      }
    };
  }, [autoConnect, enablePollingFallback]);

  // Get summary data (most reliable source)
  const summary = detectionData?.summary || {};
  
  // Helper to get eyes state from multiple possible sources
  const getEyesState = () => {
    // Priority 1: summary.eyes_state (if backend provides it)
    if (summary.eyes_state && summary.eyes_state !== 'unknown') {
      return summary.eyes_state;
    }
    
    // Priority 2: iris_tracking.closure_pattern (backend actually sends this!)
    if (detectionData?.iris_tracking?.closure_pattern) {
      const pattern = detectionData.iris_tracking.closure_pattern;
      // Map backend values: "awake", "drowsy", "sleeping"
      return pattern;
    }
    
    // Priority 3: iris_tracking.eyes_state (backend sends "open"/"closed")
    if (detectionData?.iris_tracking?.eyes_state) {
      const eyeState = detectionData.iris_tracking.eyes_state;
      // Map "open" to "awake", "closed" to "sleeping"
      if (eyeState === 'open') return 'awake';
      if (eyeState === 'closed') return 'sleeping';
      return eyeState;
    }
    
    // Priority 4: combined_facial_state.likely_state
    if (detectionData?.combined_facial_state?.likely_state) {
      return detectionData.combined_facial_state.likely_state;
    }
    
    // Priority 5: iris_tracking.eye_openness for basic detection
    if (detectionData?.iris_tracking?.eye_openness?.average !== undefined) {
      const openness = detectionData.iris_tracking.eye_openness.average;
      if (openness > 0.4) return 'awake';
      if (openness > 0.2) return 'drowsy';
      return 'sleeping';
    }
    
    // Priority 6: If face detected but no other data
    if (detectionData?.iris_tracking?.face_detected) {
      return 'awake'; // Face detected, assume awake as fallback
    }
    
    // Default
    return 'Unknown';
  };
  
  // Helper function to get color based on state
  const getStateColor = (state, isAlert = false) => {
    if (isAlert) return 'red';
    
    switch(state) {
      case 'sleeping':
      case 'still':
      case 'awake':
      case 'neutral':
      case 'happy':
        return 'green';
      case 'sitting':
      case 'standing':
      case 'micro_movement':
      case 'active':
      case 'drowsy':
        return 'yellow';
      case 'crying':
      case 'distressed':
      case 'uncomfortable':
      case 'pain':
      case 'major_movement':
      case 'unusual_posture':
        return 'orange';
      default:
        return 'gray';
    }
  };

  // Helper to format timestamp
  const formatTime = (date) => {
    if (!date) return '--:--:--';
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  // Connection status badge
  const ConnectionBadge = () => {
    const statusConfig = {
      connected: { color: 'green', icon: '✓', text: 'Connected', pulse: true },
      polling: { color: 'blue', icon: '↻', text: 'Polling', pulse: true },
      reconnecting: { color: 'yellow', icon: '↻', text: `Reconnecting (${reconnectAttempt}/${wsService.maxReconnectAttempts})`, pulse: true },
      disconnected: { color: 'gray', icon: '○', text: 'Disconnected', pulse: false },
      failed: { color: 'red', icon: '✕', text: 'Connection Failed', pulse: false },
      error: { color: 'red', icon: '⚠', text: 'Error', pulse: false },
    };

    const config = statusConfig[connectionStatus] || statusConfig.disconnected;

    return (
      <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full ${
        config.color === 'green' ? 'bg-green-100 text-green-700' :
        config.color === 'blue' ? 'bg-blue-100 text-blue-700' :
        config.color === 'yellow' ? 'bg-yellow-100 text-yellow-700' :
        config.color === 'red' ? 'bg-red-100 text-red-700' :
        'bg-gray-100 text-gray-700'
      }`}>
        <div className={`w-2 h-2 rounded-full ${
          config.color === 'green' ? 'bg-green-500' :
          config.color === 'blue' ? 'bg-blue-500' :
          config.color === 'yellow' ? 'bg-yellow-500' :
          config.color === 'red' ? 'bg-red-500' :
          'bg-gray-400'
        } ${config.pulse ? 'pulse-animation' : ''}`}></div>
        <span className="text-xs font-semibold">{config.text}</span>
      </div>
    );
  };

  // Critical Alert Banner
  const CriticalAlerts = () => {
    const alerts = [];
    
    if (summary.face_down) {
      alerts.push({
        id: 'face_down',
        icon: '🚨',
        message: 'FACE DOWN DETECTED - CHECK BABY IMMEDIATELY',
        severity: 'critical'
      });
    }
    
    if (summary.crying) {
      alerts.push({
        id: 'crying',
        icon: '😢',
        message: 'BABY IS CRYING',
        severity: 'urgent'
      });
    }
    
    if (summary.sudden_jerk) {
      alerts.push({
        id: 'jerk',
        icon: '⚡',
        message: 'SUDDEN MOVEMENT DETECTED',
        severity: 'warning'
      });
    }

    if (alerts.length === 0) return null;

    return (
      <div className="space-y-2 mb-4">
        {alerts.map(alert => (
          <div 
            key={alert.id}
            className={`p-4 rounded-xl border-2 animate-pulse-slow ${
              alert.severity === 'critical' 
                ? 'bg-red-100 border-red-500 text-red-900' 
                : alert.severity === 'urgent'
                ? 'bg-orange-100 border-orange-500 text-orange-900'
                : 'bg-yellow-100 border-yellow-500 text-yellow-900'
            }`}
          >
            <div className="flex items-center space-x-3">
              <span className="text-3xl">{alert.icon}</span>
              <div className="flex-1">
                <p className="font-bold text-lg">{alert.message}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  // Detection status indicator
  const StatusIndicator = ({ label, value, color, confidence }) => (
    <div className={`p-3 rounded-xl border-2 ${
      color === 'green' ? 'bg-green-50 border-green-200' :
      color === 'yellow' ? 'bg-yellow-50 border-yellow-200' :
      color === 'orange' ? 'bg-orange-50 border-orange-200' :
      color === 'red' ? 'bg-red-50 border-red-200' :
      'bg-gray-50 border-gray-200'
    }`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">{label}</span>
        {confidence !== undefined && (
          <span className="text-xs text-gray-500">{Math.round(confidence * 100)}%</span>
        )}
      </div>
      <div className={`text-lg font-bold ${
        color === 'green' ? 'text-green-700' :
        color === 'yellow' ? 'text-yellow-700' :
        color === 'orange' ? 'text-orange-700' :
        color === 'red' ? 'text-red-700' :
        'text-gray-700'
      }`}>
        {value || 'Unknown'}
      </div>
    </div>
  );

  // Loading state
  if (isLoading && !detectionData) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            🎯 REAL-TIME DETECTION
          </h3>
          <ConnectionBadge />
        </div>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="text-6xl mb-4 opacity-40">👶</div>
          <p className="text-lg font-semibold text-slate-700 mb-2">Waiting for Detection Data</p>
          <p className="text-sm text-slate-500">Connecting to monitoring system...</p>
          <div className="mt-4 flex space-x-1.5">
            <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
        </div>
      </div>
    );
  }

  // No data state
  if (!detectionData) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            🎯 REAL-TIME DETECTION
          </h3>
          <ConnectionBadge />
        </div>
        <div className="flex flex-col items-center justify-center py-8">
          <div className="text-4xl mb-3 opacity-40">📊</div>
          <p className="text-sm text-slate-600 mb-2">No detection data available</p>
          {error && (
            <p className="text-xs text-red-600 mt-2">⚠️ {error}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl p-6 shadow-soft">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            🎯 REAL-TIME DETECTION
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Last update: {formatTime(lastUpdate)}
          </p>
        </div>
        <ConnectionBadge />
      </div>

      {/* Critical Alerts */}
      <CriticalAlerts />

      {/* Primary Detection Status */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <StatusIndicator
          label="Baby Detection"
          value={summary.baby_detected ? 'Detected ✓' : 'Not Detected'}
          color={summary.baby_detected ? 'green' : 'gray'}
        />
        <StatusIndicator
          label="Adult Present"
          value={summary.adult_detected ? 'Yes' : 'No'}
          color={summary.adult_detected ? 'blue' : 'gray'}
        />
      </div>

      {/* Main Detection Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <StatusIndicator
          label="Pose / Posture"
          value={summary.pose?.replace('_', ' ') || 'Unknown'}
          color={getStateColor(summary.pose)}
          confidence={detectionData.pose?.confidence}
        />
        <StatusIndicator
          label="Movement"
          value={summary.movement?.replace('_', ' ') || 'Unknown'}
          color={getStateColor(summary.movement)}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <StatusIndicator
          label="Emotion"
          value={summary.emotion || 'Unknown'}
          color={getStateColor(summary.emotion, summary.crying)}
          confidence={detectionData.emotion?.probability}
        />
        <StatusIndicator
          label="Eyes State"
          value={getEyesState()}
          color={getStateColor(getEyesState())}
        />
      </div>

      {/* Additional Indicators */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className={`p-2 rounded-lg text-center ${
          summary.crying ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
        }`}>
          <div className="text-lg mb-1">{summary.crying ? '😢' : '😊'}</div>
          <div className="text-xs font-semibold">
            {summary.crying ? 'Crying' : 'Not Crying'}
          </div>
        </div>
        
        <div className={`p-2 rounded-lg text-center ${
          summary.sudden_jerk ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'
        }`}>
          <div className="text-lg mb-1">{summary.sudden_jerk ? '⚡' : '😌'}</div>
          <div className="text-xs font-semibold">
            {summary.sudden_jerk ? 'Jerking' : 'Calm'}
          </div>
        </div>
        
        <div className={`p-2 rounded-lg text-center ${
          summary.face_down ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
        }`}>
          <div className="text-lg mb-1">{summary.face_down ? '🚨' : '✓'}</div>
          <div className="text-xs font-semibold">
            {summary.face_down ? 'Face Down' : 'Safe'}
          </div>
        </div>
      </div>

      {/* Movement Details */}
      {detectionData.movement && (
        <div className="p-3 bg-slate-50 rounded-lg">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-slate-600">Movement Score:</span>
              <span className="ml-2 font-semibold">{detectionData.movement.movement_score?.toFixed(2) || 'N/A'}</span>
            </div>
            <div>
              <span className="text-slate-600">Still Duration:</span>
              <span className="ml-2 font-semibold">{detectionData.movement.stillness_duration_s?.toFixed(1) || '0'}s</span>
            </div>
          </div>
        </div>
      )}

      {/* Iris Tracking Details - Show rich eye tracking data */}
      {detectionData.iris_tracking && detectionData.iris_tracking.face_detected && (
        <div className="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
          <div className="text-xs font-semibold text-indigo-800 mb-2">
            👁️ Eye Tracking Details
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-indigo-600">Eye Openness:</span>
              <span className="ml-2 font-semibold text-indigo-800">
                {detectionData.iris_tracking.eye_openness?.average ? 
                  `${(detectionData.iris_tracking.eye_openness.average * 100).toFixed(0)}%` : 
                  'N/A'}
              </span>
            </div>
            <div>
              <span className="text-indigo-600">Closure Pattern:</span>
              <span className="ml-2 font-semibold text-indigo-800 capitalize">
                {detectionData.iris_tracking.closure_pattern || 'N/A'}
              </span>
            </div>
            {detectionData.iris_tracking.blinking && (
              <>
                <div>
                  <span className="text-indigo-600">Blinks/min:</span>
                  <span className="ml-2 font-semibold text-indigo-800">
                    {detectionData.iris_tracking.blinking.frequency_per_minute || 0}
                  </span>
                </div>
                <div>
                  <span className="text-indigo-600">Total Blinks:</span>
                  <span className="ml-2 font-semibold text-indigo-800">
                    {detectionData.iris_tracking.blinking.total_blinks || 0}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Detection Counts */}
      {detectionData.yolo && (
        <div className="mt-3 p-3 bg-slate-50 rounded-lg">
          <div className="text-xs text-slate-600 mb-1">
            <span className="font-semibold">Detection Details:</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-slate-600">Persons:</span>
              <span className="ml-2 font-semibold">{detectionData.yolo.person_count || 0}</span>
            </div>
            <div>
              <span className="text-slate-600">Frame Size:</span>
              <span className="ml-2 font-semibold">
                {detectionData.frame_shape ? `${detectionData.frame_shape[1]}×${detectionData.frame_shape[0]}` : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-xs text-red-700">⚠️ {error}</p>
        </div>
      )}

      {/* Debug Info - Only show when eyes_state is Unknown and in development */}
      {getEyesState() === 'Unknown' && detectionData && (
        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs font-semibold text-blue-800 mb-1">🔍 Debug: Eyes State</p>
          <div className="text-xs text-blue-700 space-y-1">
            <div>summary.eyes_state: <code className="bg-blue-100 px-1 rounded">{JSON.stringify(summary.eyes_state)}</code></div>
            <div>iris_tracking.closure_pattern: <code className="bg-blue-100 px-1 rounded">{JSON.stringify(detectionData.iris_tracking?.closure_pattern)}</code></div>
            <div>iris_tracking.eyes_state: <code className="bg-blue-100 px-1 rounded">{JSON.stringify(detectionData.iris_tracking?.eyes_state)}</code></div>
            <div>iris_tracking.eye_openness: <code className="bg-blue-100 px-1 rounded">{JSON.stringify(detectionData.iris_tracking?.eye_openness?.average)}</code></div>
            <div>combined_facial_state: <code className="bg-blue-100 px-1 rounded">{JSON.stringify(detectionData.combined_facial_state?.likely_state)}</code></div>
          </div>
          <p className="text-xs text-blue-600 mt-2">💡 Check browser console for full data or see DEBUG_EYES_STATE.md</p>
        </div>
      )}
    </div>
  );
}

export default DetectionMonitor;
