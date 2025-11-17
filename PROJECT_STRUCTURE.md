# Baby Monitor Dashboard - Project Structure

## 📁 Directory Overview

```
baby_frontend/
├── public/                      # Static files
│   ├── index.html              # HTML template
│   ├── manifest.json           # PWA manifest
│   └── robots.txt              # SEO configuration
│
├── src/                        # Source code
│   ├── components/             # Reusable React components
│   │   ├── common/            # Common UI components
│   │   │   ├── ActivityItem.jsx
│   │   │   ├── AlertCard.jsx
│   │   │   ├── DailySummaryCard.jsx
│   │   │   ├── StatusCard.jsx
│   │   │   └── VideoFeed.jsx
│   │   ├── layout/            # Layout components
│   │   │   └── NavSidebar.jsx
│   │   └── index.js           # Component exports
│   │
│   ├── pages/                 # Page components
│   │   ├── Dashboard.jsx      # Main dashboard page
│   │   ├── Alerts.jsx         # Alerts history page
│   │   └── Settings.jsx       # Settings page
│   │
│   ├── services/              # Business logic & external services
│   │   └── WebSocketService.js # WebSocket communication
│   │
│   ├── styles/                # Styling files
│   │   ├── animations.css     # Custom animations
│   │   └── index.css          # Main stylesheet (Tailwind)
│   │
│   ├── App.jsx                # Main app component
│   └── index.js               # Application entry point
│
├── .gitignore                 # Git ignore rules
├── package.json               # Dependencies & scripts
├── postcss.config.js          # PostCSS configuration
├── tailwind.config.js         # Tailwind CSS configuration
└── README.md                  # Project documentation
```

## 🎯 Component Hierarchy

```
App
├── NavSidebar
└── Pages
    ├── Dashboard
    │   ├── VideoFeed
    │   ├── StatusCard (x4)
    │   ├── DailySummaryCard (x4)
    │   ├── AlertCard (dynamic)
    │   └── ActivityItem (dynamic)
    │
    ├── Alerts
    │   └── AlertCard (dynamic)
    │
    └── Settings
        └── (Form components)
```

## 🧩 Component Description

### Common Components

- **StatusCard**: Displays real-time status information with visual indicators
- **AlertCard**: Shows alert messages with severity-based styling
- **VideoFeed**: Displays live camera feed with placeholder
- **DailySummaryCard**: Shows daily statistics with trend indicators
- **ActivityItem**: Displays activity log entries with icons

### Layout Components

- **NavSidebar**: Main navigation sidebar with page switching

### Pages

- **Dashboard**: Main monitoring interface with live updates
- **Alerts**: Alert history and management
- **Settings**: System configuration and monitoring controls

### Services

- **WebSocketService**: Manages WebSocket connections and real-time communication

## 🎨 Styling Architecture

### Tailwind CSS
- Utility-first CSS framework
- Configured in `tailwind.config.js`
- Extended with custom animations and colors

### Custom Styles
- **animations.css**: Custom animations and effects
  - Glass morphism effects
  - Glow effects
  - Hover animations
  - Float/pulse animations
  
- **index.css**: Global styles and imports
  - Font imports (Inter)
  - Custom scrollbar
  - Base styles

## 🔄 Data Flow

```
WebSocket Server
      ↓
WebSocketService (Singleton)
      ↓
Component Subscriptions
      ↓
State Updates (useState)
      ↓
UI Re-render
```

## 📦 Key Dependencies

- **react**: UI library (v18.2.0)
- **react-dom**: React renderer (v18.2.0)
- **tailwindcss**: Utility-first CSS framework (v3.3.6)
- **postcss**: CSS transformation tool
- **autoprefixer**: CSS vendor prefixing

## 🚀 Getting Started

### Installation
```bash
npm install
```

### Development
```bash
npm start
```
Runs on http://localhost:3000

### Production Build
```bash
npm build
```
Creates optimized production build in `/build`

## 🔌 WebSocket Integration

The app connects to a WebSocket server for real-time updates:

- **Default URL**: `ws://localhost:8000/ws`
- **Event Types**:
  - `status_update`: Baby/adult detection status
  - `alert`: Critical alerts and notifications
  - `connection`: Connection status updates

## 📱 Responsive Design

The application is fully responsive with breakpoints:
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

Key responsive features:
- Collapsible sidebar on mobile
- Adaptive grid layouts
- Touch-friendly controls
- Optimized animations

## 🎨 Design Features

- **Glass Morphism**: Modern translucent UI elements
- **Gradient Backgrounds**: Eye-catching color schemes
- **Smooth Animations**: Professional transitions and effects
- **Dark/Light Accents**: Balanced color palette
- **Status Indicators**: Visual feedback with glow effects
- **Interactive Elements**: Hover and click animations

## 🔧 Configuration

The app supports dynamic configuration through:
- WebSocket events
- Custom event system
- State management

## 📝 Best Practices

1. **Component Organization**: Separated by function (common, layout, pages)
2. **Service Layer**: Isolated business logic
3. **Reusability**: Modular, reusable components
4. **Performance**: Optimized re-renders with proper hooks
5. **Maintainability**: Clear file structure and naming
6. **Responsiveness**: Mobile-first approach
7. **Accessibility**: Semantic HTML and ARIA labels

## 🐛 Development Tips

- Use React DevTools for debugging
- Check WebSocket connection in Network tab
- Tailwind classes are sorted for readability
- Custom animations defined in animations.css
- All colors use Tailwind's color palette

## 📄 License

MIT

