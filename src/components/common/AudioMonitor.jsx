import React, { useState, useEffect, useRef } from 'react';
import wsService from '../../services/WebSocketService';
import { getDetectionWebSocketUrl, getAudioStreamUrl } from '../../services/ApiService';

/**
 * AudioMonitor Component - Real-time audio monitoring with live stream playback
 * Displays audio detection metrics and provides live audio streaming from baby monitor
 */
function AudioMonitor({ enablePollingFallback = true, autoConnect = true }) {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [audioData, setAudioData] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [audioError, setAudioError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const mountedRef = useRef(true);
  const audioRef = useRef(null);

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
      } else if (data.status === 'failed') {
        setError(data.message || 'Connection failed');
      }
    };

    // Subscribe to detection data updates - extract audio field
    const handleDetection = (data) => {
      if (!mountedRef.current) return;
      
      // Extract audio data from detection message
      if (data.audio) {
        console.log('🎤 Audio Data Received:', data.audio);
        setAudioData(data.audio);
        setLastUpdate(new Date());
        setError(null);
        setIsLoading(false);
      }
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

  // Handle audio playback events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleError = (e) => {
      console.error('Audio stream error:', e);
      setAudioError('Failed to load audio stream. Check if backend is running.');
      setIsPlaying(false);
    };
    const handleCanPlay = () => {
      setAudioError(null);
    };

    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('error', handleError);
    audio.addEventListener('canplay', handleCanPlay);

    return () => {
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('canplay', handleCanPlay);
    };
  }, []);

  // Helper to format timestamp
  const formatTime = (date) => {
    if (!date) return '--:--:--';
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  // Get status color based on audio state
  const getAudioStatusColor = () => {
    if (!audioData) return 'gray';
    if (!audioData.enabled) return 'gray';
    if (!audioData.available) return 'gray';
    if (audioData.is_crying) return 'red';
    if (audioData.is_awakening) return 'orange';
    if (audioData.audio_detected) return 'green';
    return 'gray';
  };

  // Get status text and emoji
  const getAudioStatusText = () => {
    if (!audioData) return { emoji: '🎤', text: 'Waiting for audio data...' };
    if (!audioData.enabled) return { emoji: '🔇', text: 'Audio monitoring disabled' };
    if (!audioData.available) return { emoji: '⚠️', text: 'Audio device not available' };
    if (audioData.is_crying) return { emoji: '🚨', text: 'Baby crying detected!' };
    if (audioData.is_awakening) return { emoji: '⚠️', text: 'Baby awakening detected' };
    if (audioData.audio_detected) return { emoji: '🎤', text: 'Audio monitoring active - Sound detected' };
    return { emoji: '🎤', text: 'Audio monitoring active - Quiet' };
  };

  // Format noise level
  const formatNoiseLevel = (level) => {
    if (level === null || level === undefined) return 'N/A';
    return `${level.toFixed(1)} dB`;
  };

  // Format sound type
  const formatSoundType = (type) => {
    if (!type) return 'Unknown';
    const typeMap = {
      'crying': '😢 Crying',
      'laughing': '😄 Laughing',
      'normal': '👶 Normal',
      'other_voice': '👤 Other Voice',
      'silence': '🤫 Silence'
    };
    return typeMap[type] || type;
  };

  // Connection status badge
  const ConnectionBadge = () => {
    const statusConfig = {
      connected: { color: 'green', text: 'Connected', pulse: true },
      polling: { color: 'blue', text: 'Polling', pulse: true },
      reconnecting: { color: 'yellow', text: 'Reconnecting', pulse: true },
      disconnected: { color: 'gray', text: 'Disconnected', pulse: false },
      failed: { color: 'red', text: 'Connection Failed', pulse: false },
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

  // Audio Status Banner
  const AudioStatusBanner = () => {
    const status = getAudioStatusText();
    const color = getAudioStatusColor();

    return (
      <div className={`p-4 rounded-xl border-2 ${
        color === 'red' ? 'bg-red-100 border-red-500 text-red-900 animate-pulse-slow' :
        color === 'orange' ? 'bg-orange-100 border-orange-500 text-orange-900' :
        color === 'green' ? 'bg-green-100 border-green-500 text-green-900' :
        'bg-gray-100 border-gray-300 text-gray-700'
      }`}>
        <div className="flex items-center space-x-3">
          <span className="text-3xl">{status.emoji}</span>
          <div className="flex-1">
            <p className="font-bold text-lg">{status.text}</p>
            {audioData && audioData.enabled && audioData.available && (
              <p className="text-sm mt-1">
                {formatSoundType(audioData.sound_type)} • {formatNoiseLevel(audioData.noise_level)}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Audio Player Section
  const AudioPlayerSection = () => {
    const audioStreamUrl = getAudioStreamUrl();

    return (
      <div className="p-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl border-2 border-purple-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <span className="text-2xl">🔊</span>
            <h4 className="text-sm font-bold text-purple-900 uppercase tracking-wide">
              Live Audio Stream
            </h4>
          </div>
          <div className={`px-2 py-1 rounded-full text-xs font-semibold ${
            isPlaying ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
          }`}>
            {isPlaying ? '▶ Playing' : '⏸ Paused'}
          </div>
        </div>

        <audio
          ref={audioRef}
          controls
          autoPlay
          className="w-full"
          src={audioStreamUrl}
          preload="auto"
        >
          Your browser does not support the audio element.
        </audio>

        {audioError && (
          <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded text-xs text-red-700">
            ⚠️ {audioError}
          </div>
        )}

        <p className="text-xs text-purple-600 mt-2 text-center">
          Real-time audio from baby monitor microphone
        </p>
      </div>
    );
  };

  // Audio Metrics Grid
  const AudioMetrics = () => {
    if (!audioData || !audioData.enabled || !audioData.available) {
      return null;
    }

    return (
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
          Audio Detection Metrics
        </h4>

        {/* Main Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          <MetricCard
            label="Sound Type"
            value={formatSoundType(audioData.sound_type)}
            color={audioData.is_crying ? 'red' : audioData.audio_detected ? 'green' : 'gray'}
          />
          <MetricCard
            label="Noise Level"
            value={formatNoiseLevel(audioData.noise_level)}
            color={audioData.audio_detected ? 'green' : 'gray'}
          />
        </div>

        {/* Detection States */}
        <div className="grid grid-cols-3 gap-2">
          <StateIndicator
            emoji={audioData.is_crying ? '😢' : '😊'}
            label="Crying"
            active={audioData.is_crying}
            color="red"
          />
          <StateIndicator
            emoji={audioData.is_awakening ? '⚡' : '😴'}
            label="Awakening"
            active={audioData.is_awakening}
            color="orange"
          />
          <StateIndicator
            emoji={audioData.other_voice_detected ? '👤' : '👶'}
            label="Other Voice"
            active={audioData.other_voice_detected}
            color="blue"
          />
        </div>

        {/* Crying Confidence */}
        {audioData.is_crying && audioData.crying_confidence !== undefined && (
          <div className="p-3 bg-red-50 rounded-lg border border-red-200">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-red-700">Crying Confidence</span>
              <span className="text-sm font-bold text-red-900">
                {Math.round(audioData.crying_confidence * 100)}%
              </span>
            </div>
            <div className="w-full bg-red-200 rounded-full h-2">
              <div
                className="bg-red-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${audioData.crying_confidence * 100}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Silence Duration */}
        {audioData.silence_duration > 0 && (
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="text-xs text-blue-600 mb-1">Silence Duration</div>
            <div className="text-lg font-bold text-blue-900">
              {audioData.silence_duration.toFixed(1)}s
            </div>
          </div>
        )}
      </div>
    );
  };

  // Metric Card Component
  const MetricCard = ({ label, value, color }) => (
    <div className={`p-3 rounded-xl border-2 ${
      color === 'green' ? 'bg-green-50 border-green-200' :
      color === 'red' ? 'bg-red-50 border-red-200' :
      color === 'orange' ? 'bg-orange-50 border-orange-200' :
      'bg-gray-50 border-gray-200'
    }`}>
      <div className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className={`text-lg font-bold ${
        color === 'green' ? 'text-green-700' :
        color === 'red' ? 'text-red-700' :
        color === 'orange' ? 'text-orange-700' :
        'text-gray-700'
      }`}>
        {value}
      </div>
    </div>
  );

  // State Indicator Component
  const StateIndicator = ({ emoji, label, active, color }) => (
    <div className={`p-2 rounded-lg text-center ${
      active
        ? color === 'red' ? 'bg-red-100 text-red-700' :
          color === 'orange' ? 'bg-orange-100 text-orange-700' :
          color === 'blue' ? 'bg-blue-100 text-blue-700' :
          'bg-green-100 text-green-700'
        : 'bg-gray-100 text-gray-600'
    }`}>
      <div className="text-lg mb-1">{emoji}</div>
      <div className="text-xs font-semibold">{label}</div>
      <div className="text-xs mt-0.5">{active ? 'Yes' : 'No'}</div>
    </div>
  );

  // Loading state
  if (isLoading && !audioData) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            🎤 AUDIO MONITORING
          </h3>
          <ConnectionBadge />
        </div>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="text-6xl mb-4 opacity-40">🔊</div>
          <p className="text-lg font-semibold text-slate-700 mb-2">Waiting for Audio Data</p>
          <p className="text-sm text-slate-500">Connecting to audio monitoring system...</p>
          <div className="mt-4 flex space-x-1.5">
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
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
            🎤 AUDIO MONITORING
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Last update: {formatTime(lastUpdate)}
          </p>
        </div>
        <ConnectionBadge />
      </div>

      {/* Audio Player */}
      <div className="mb-4">
        <AudioPlayerSection />
      </div>

      {/* Status Banner */}
      <div className="mb-4">
        <AudioStatusBanner />
      </div>

      {/* Audio Metrics */}
      <AudioMetrics />

      {/* Error Display */}
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-xs text-red-700">⚠️ {error}</p>
        </div>
      )}
    </div>
  );
}

export default AudioMonitor;
