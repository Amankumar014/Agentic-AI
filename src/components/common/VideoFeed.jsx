import React, { useState } from 'react';

/**
 * VideoFeed Component - Displays live MJPEG camera feed
 */
function VideoFeed({ cameraUrl, label }) {
  const [streamError, setStreamError] = useState(false);
  const [streamLoading, setStreamLoading] = useState(true);

  const handleImageLoad = () => {
    setStreamLoading(false);
    setStreamError(false);
  };

  const handleImageError = (e) => {
    console.error('Video stream error:', e);
    setStreamError(true);
    setStreamLoading(false);
  };

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-soft">
      <div className="bg-slate-100 px-4 py-3 border-b border-slate-200">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-slate-200 rounded-lg flex items-center justify-center text-lg">
            📹
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-700">{label}</h3>
            <div className="flex items-center space-x-1">
              {!streamError && cameraUrl ? (
                <>
                  <div className="w-2 h-2 bg-accent-500 rounded-full pulse-animation"></div>
                  <p className="text-xs text-slate-500">LIVE STREAM</p>
                </>
              ) : (
                <>
                  <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                  <p className="text-xs text-slate-500">OFFLINE</p>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="aspect-video bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center relative">
        {cameraUrl && (
          <img
            src={cameraUrl}
            alt="Live camera feed"
            className={`w-full h-full object-cover ${streamError ? 'hidden' : ''}`}
            onLoad={handleImageLoad}
            onError={handleImageError}
          />
        )}
        
        {/* Loading/Error State Overlay */}
        {(!cameraUrl || streamLoading || streamError) && (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
            <div className="text-slate-400 text-center">
              <div className="text-6xl mb-4 opacity-40">
                {streamError ? '⚠️' : '📹'}
              </div>
              <p className="text-lg font-semibold mb-1">
                {streamError ? 'Stream Unavailable' : 'Camera Feed'}
              </p>
              <p className="text-sm opacity-75">
                {streamError 
                  ? 'Unable to connect to camera stream. Please ensure the backend is running.'
                  : 'Establishing Connection...'
                }
              </p>
              {!streamError && (
                <div className="mt-4 flex justify-center space-x-1.5">
                  <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-primary-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0.1s' }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-primary-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0.2s' }}
                  ></div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default VideoFeed;

