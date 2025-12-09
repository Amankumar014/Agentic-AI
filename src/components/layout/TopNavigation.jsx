import React from 'react';

/**
 * TopNavigation Component - Horizontal tab navigation (Lalla Care style)
 */
function TopNavigation({ currentPage, onPageChange, appTitle }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '⏱' },
    { id: 'live', label: 'Live Feed', icon: '📹' },
    { id: 'sleep', label: 'Sleep Logs', icon: '😴' },
    { id: 'activity', label: 'Activity', icon: '📊' },
    { id: 'payment', label: 'Payment', icon: '💳' },
    { id: 'settings', label: 'Settings', icon: '⚙' }
  ];

  return (
    <div className="bg-white border-b border-slate-100 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-20">
          {/* Logo */}
          <div className="flex items-center space-x-3 flex-shrink-0">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-secondary-300 to-primary-400 rounded-full flex items-center justify-center shadow-soft">
              <span className="text-white text-xl sm:text-2xl">🌙</span>
            </div>
            <div className="flex flex-col leading-tight">
              <h1 className="text-base sm:text-lg font-bold text-secondary-600 tracking-wide">LALLA</h1>
              <h2 className="text-base sm:text-lg font-bold text-primary-500 tracking-wide">CARE</h2>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center h-full ml-8 lg:ml-12 overflow-x-auto scrollbar-hide">
            {menuItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id)}
                className={`flex flex-col items-center justify-center px-4 sm:px-6 h-full transition-all duration-200 relative flex-shrink-0 ${
                  currentPage === item.id
                    ? 'text-primary-500'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                <span className="text-lg sm:text-xl mb-1">{item.icon}</span>
                <span className="text-xs sm:text-sm font-semibold whitespace-nowrap">{item.label}</span>
                {currentPage === item.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-400 to-primary-600"></div>
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

