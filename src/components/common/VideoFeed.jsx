import React from 'react';

/**
 * VideoFeed Component - Displays live camera feed
 */
function VideoFeed({ cameraUrl, label }) {
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
              <div className="w-2 h-2 bg-accent-500 rounded-full pulse-animation"></div>
              <p className="text-xs text-slate-500">LIVE CAMERA</p>
            </div>
          </div>
        </div>
      </div>
      <div className="aspect-video bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center relative">
        {cameraUrl ? (
          <img
            src={cameraUrl}
            alt="Live camera feed"
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.style.display = 'none';
              if (e.target.nextSibling) {
                e.target.nextSibling.style.display = 'flex';
              }
            }}
          />
        ) : null}
        <div className="text-slate-400 text-center z-10">
          <div className="text-6xl mb-4 opacity-40">📹</div>
          <p className="text-lg font-semibold mb-1">Camera Feed</p>
          <p className="text-sm opacity-75">
            Establishing Connection...
          </p>
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
        </div>
      </div>
    </div>
  );
}

export default VideoFeed;

