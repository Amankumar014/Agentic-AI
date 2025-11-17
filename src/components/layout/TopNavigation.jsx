import React from 'react';

/**
 * TopNavigation Component - Horizontal tab navigation (Lalla Care style)
 */
function TopNavigation({ currentPage, onPageChange, appTitle }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '⏱' },
    { id: 'live', label: 'Live Feed', icon: '👶' },
    { id: 'sleep', label: 'Sleep Logs', icon: '🎤' },
    { id: 'activity', label: 'Activity', icon: '😊' },
    { id: 'settings', label: 'Settings', icon: '⚙' }
  ];

  return (
    <div className="bg-white border-b border-slate-100">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-3 py-4">
            <div className="w-12 h-12 bg-gradient-to-br from-secondary-300 to-primary-400 rounded-full flex items-center justify-center shadow-soft">
              <span className="text-white text-2xl">🌙</span>
            </div>
            <div className="flex flex-col leading-tight">
              <h1 className="text-lg font-bold text-secondary-600 tracking-wide">LALLA</h1>
              <h2 className="text-lg font-bold text-primary-500 tracking-wide">CARE</h2>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center">
            {menuItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id)}
                className={`flex flex-col items-center px-5 py-4 transition-all duration-200 relative ${
                  currentPage === item.id
                    ? 'text-primary-500'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                <span className="text-xl mb-1">{item.icon}</span>
                <span className="text-xs font-semibold">{item.label}</span>
                {currentPage === item.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-primary-500"></div>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>
    </div>
  );
}

export default TopNavigation;

