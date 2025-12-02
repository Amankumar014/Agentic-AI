import React, { useState } from 'react';

/**
 * DetectionLegend Component - Explains detection visualization overlays
 */
function DetectionLegend() {
  const [isExpanded, setIsExpanded] = useState(false);

  const detectionTypes = [
    {
      name: 'Pose Skeleton',
      color: 'rgb(34, 197, 94)', // green-500
      description: '33 body keypoints connected with lines showing posture',
      icon: '🦴'
    },
    {
      name: 'Face Mesh',
      color: 'rgb(236, 72, 153)', // magenta/pink-500
      description: '468 facial landmarks tracking face contour, eyes, nose, mouth',
      icon: '😊'
    },
    {
      name: 'Iris Tracking',
      color: 'rgb(6, 182, 212)', // cyan-500
      description: 'Circular markers showing precise eye tracking',
      icon: '👁️'
    },
    {
      name: 'Baby Detection',
      color: 'rgb(234, 179, 8)', // yellow-500
      description: 'Bounding box with confidence score',
      icon: '👶'
    },
    {
      name: 'Adult Detection',
      color: 'rgb(249, 115, 22)', // orange-500
      description: 'Bounding box with confidence score',
      icon: '👤'
    }
  ];

  const statusColors = [
    { name: 'Critical Alert', color: 'rgb(239, 68, 68)', description: 'Immediate attention required' },
    { name: 'Warning', color: 'rgb(249, 115, 22)', description: 'Monitor closely' },
    { name: 'Safe State', color: 'rgb(34, 197, 94)', description: 'All systems normal' }
  ];

  return (
    <div className="bg-white rounded-2xl shadow-soft overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
      >
        <div className="flex items-center space-x-3">
          <span className="text-2xl">🎨</span>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Detection Legend
            </h3>
            <p className="text-xs text-slate-500">
              {isExpanded ? 'Click to collapse' : 'Click to view detection overlays'}
            </p>
          </div>
        </div>
        <div className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
          <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-6 space-y-6">
          {/* Detection Visualizations */}
          <div>
            <h4 className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wide">
              Visual Overlays
            </h4>
            <div className="space-y-3">
              {detectionTypes.map((type) => (
                <div key={type.name} className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <span className="text-lg">{type.icon}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: type.color }}
                      ></div>
                      <span className="text-sm font-semibold text-slate-700">{type.name}</span>
                    </div>
                    <p className="text-xs text-slate-500">{type.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Status Colors */}
          <div className="pt-4 border-t border-slate-200">
            <h4 className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wide">
              Status Indicators
            </h4>
            <div className="space-y-2">
              {statusColors.map((status) => (
                <div key={status.name} className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: status.color }}
                    ></div>
                    <span className="text-sm text-slate-700">{status.name}</span>
                  </div>
                  <span className="text-xs text-slate-500">{status.description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Additional Info */}
          <div className="pt-4 border-t border-slate-200">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-start space-x-2">
                <span className="text-lg">ℹ️</span>
                <div>
                  <p className="text-xs font-semibold text-blue-900 mb-1">Real-Time Processing</p>
                  <p className="text-xs text-blue-700">
                    All detections are processed at ~10 FPS with overlays drawn server-side. 
                    Status bar at the top shows current alerts, baby state, emotion, and pose.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DetectionLegend;

