import React from 'react';

/**
 * NavSidebar Component - Main navigation sidebar
 */
function NavSidebar({ currentPage, onPageChange, appTitle }) {
  const menuItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: '🏠',
      gradient: 'from-blue-500 to-purple-600'
    },
    {
      id: 'alerts',
      label: 'Alerts',
      icon: '🚨',
      gradient: 'from-red-500 to-pink-600'
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: '⚙️',
      gradient: 'from-green-500 to-teal-600'
    }
  ];

  return (
    <div className="sidebar-gradient text-white w-80 min-h-full p-8 shadow-2xl relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-16 translate-x-16"></div>
      <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-full translate-y-12 -translate-x-12"></div>

      <div className="relative z-10">
        <div className="mb-12">
          <div className="flex items-center space-x-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center text-3xl shadow-xl neon-glow">
              👶
            </div>
            <div>
              <h1 className="text-2xl font-black">{appTitle}</h1>
              <p className="text-slate-300 text-sm font-semibold">
                AI Monitoring System
              </p>
            </div>
          </div>
          <div className="h-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full"></div>
        </div>

        <nav className="space-y-4">
          {menuItems.map((item, index) => (
            <button
              key={item.id}
              onClick={() => onPageChange(item.id)}
              className={`w-full flex items-center space-x-5 px-6 py-5 rounded-2xl transition-all duration-300 group ${
                currentPage === item.id
                  ? 'bg-white text-slate-800 shadow-2xl transform scale-105 neon-glow'
                  : 'text-slate-300 hover:bg-white/10 hover:text-white hover:transform hover:scale-102'
              }`}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div
                className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl transition-all duration-300 ${
                  currentPage === item.id
                    ? `bg-gradient-to-br ${item.gradient} text-white shadow-lg`
                    : 'bg-white/10 group-hover:bg-white/20'
                }`}
              >
                {item.icon}
              </div>
              <span className="font-bold text-lg">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="mt-12 p-6 bg-white/10 rounded-2xl backdrop-blur-sm">
          <div className="flex items-center space-x-3 mb-3">
            <div className="w-3 h-3 bg-emerald-400 rounded-full pulse-animation"></div>
            <span className="text-sm font-bold text-emerald-400">
              SYSTEM STATUS
            </span>
          </div>
          <p className="text-slate-300 text-sm font-medium">
            All systems operational
          </p>
        </div>
      </div>
    </div>
  );
}

export default NavSidebar;

