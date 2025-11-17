# 🧩 Components Guide

A comprehensive guide to all components in the Baby Monitor Dashboard.

## Table of Contents

1. [Common Components](#common-components)
2. [Layout Components](#layout-components)
3. [Page Components](#page-components)
4. [Usage Examples](#usage-examples)

---

## Common Components

### 1. StatusCard

**Purpose:** Display real-time status information with visual indicators

**Location:** `src/components/common/StatusCard.jsx`

**Props:**
```javascript
{
  title: string,           // Card title (e.g., "Baby Detected")
  status: string,          // Status text (e.g., "Yes" or "No")
  isActive: boolean,       // Whether status is active
  severity: string,        // 'info' | 'success' | 'warning' | 'critical'
  icon: string            // Emoji icon (e.g., "👶")
}
```

**Example:**
```jsx
<StatusCard
  title="Baby Detected"
  status="Yes"
  isActive={true}
  severity="success"
  icon="👶"
/>
```

**Features:**
- Color-coded severity levels
- Animated pulse indicator when active
- Hover lift effect
- Glass morphism design

---

### 2. AlertCard

**Purpose:** Display alert messages with severity-based styling

**Location:** `src/components/common/AlertCard.jsx`

**Props:**
```javascript
{
  alert: {
    id: number,
    message: string,
    severity: string,     // 'info' | 'warning' | 'critical'
    timestamp: string
  }
}
```

**Example:**
```jsx
<AlertCard
  alert={{
    id: 1,
    message: "Baby crying detected",
    severity: "critical",
    timestamp: "2:34 PM"
  }}
/>
```

**Features:**
- Color-coded left border
- Severity badges
- Fade-in animation
- Hover shadow effect

---

### 3. VideoFeed

**Purpose:** Display live camera feed with placeholder

**Location:** `src/components/common/VideoFeed.jsx`

**Props:**
```javascript
{
  cameraUrl: string,      // URL to camera stream
  label: string           // Camera label (e.g., "Nursery Camera")
}
```

**Example:**
```jsx
<VideoFeed
  cameraUrl="http://192.168.1.100:8080/video"
  label="Nursery Camera"
/>
```

**Features:**
- Animated placeholder when no feed
- Gradient header
- Auto-fallback on error
- Responsive aspect ratio

---

### 4. DailySummaryCard

**Purpose:** Display daily statistics with trend indicators

**Location:** `src/components/common/DailySummaryCard.jsx`

**Props:**
```javascript
{
  title: string,          // Stat title (e.g., "Sleep Duration")
  value: string,          // Stat value (e.g., "8.5h")
  change: number,         // Percentage change (e.g., 12)
  icon: string,          // Emoji icon (e.g., "😴")
  variant: string        // 'primary' | 'secondary' | 'accent' | 'warning'
}
```

**Example:**
```jsx
<DailySummaryCard
  title="Sleep Duration"
  value="8.5h"
  change={12}
  icon="😴"
  variant="primary"
/>
```

**Features:**
- Multiple color variants
- Trend indicators (up/down arrows)
- Hover scale effect
- Float animation on icon

---

### 5. ActivityItem

**Purpose:** Display activity log entries with icons

**Location:** `src/components/common/ActivityItem.jsx`

**Props:**
```javascript
{
  activity: {
    id: number,
    type: string,         // 'sleep' | 'wake' | 'cry' | 'feed' | 'adult'
    description: string,
    time: string,
    duration: string
  }
}
```

**Example:**
```jsx
<ActivityItem
  activity={{
    id: 1,
    type: "sleep",
    description: "Baby fell asleep peacefully",
    time: "2:30 PM",
    duration: "2h ago"
  }}
/>
```

**Features:**
- Type-based color coding
- Icon badges
- Duration tags
- Hover card effect

---

## Layout Components

### 6. NavSidebar

**Purpose:** Main navigation sidebar with page switching

**Location:** `src/components/layout/NavSidebar.jsx`

**Props:**
```javascript
{
  currentPage: string,       // Current active page ID
  onPageChange: function,    // Page change handler
  appTitle: string          // Application title
}
```

**Example:**
```jsx
<NavSidebar
  currentPage="dashboard"
  onPageChange={(page) => setCurrentPage(page)}
  appTitle="Baby Monitor Dashboard"
/>
```

**Features:**
- Animated menu items
- Active state highlighting
- Gradient backgrounds
- System status indicator
- Responsive design

---

## Page Components

### 7. Dashboard

**Purpose:** Main monitoring interface with real-time updates

**Location:** `src/pages/Dashboard.jsx`

**Props:**
```javascript
{
  config: {
    camera_label: string,
    baby_detected_text: string,
    adult_detected_text: string
  }
}
```

**Features:**
- Live status updates via WebSocket
- Daily summary cards
- Recent alerts panel
- Activity log
- Video feed integration

**State Management:**
```javascript
const [status, setStatus] = useState({
  babyDetected: false,
  adultDetected: false,
  babyState: 'unknown',
  crying: false,
  lastUpdate: null
});
```

---

### 8. Alerts

**Purpose:** Alert history and management

**Location:** `src/pages/Alerts.jsx`

**Features:**
- Alert history list
- Clear all functionality
- Real-time alert updates
- Empty state handling

**State Management:**
```javascript
const [alerts, setAlerts] = useState([]);
```

---

### 9. Settings

**Purpose:** System configuration and monitoring controls

**Location:** `src/pages/Settings.jsx`

**Features:**
- Camera URL configuration
- Alert cooldown settings
- Detection toggles
- Monitoring controls
- Settings persistence

**State Management:**
```javascript
const [settings, setSettings] = useState({
  cameraUrl: '',
  alertCooldown: 30,
  babyDetection: true,
  adultDetection: true,
  cryingDetection: true
});
```

---

## Usage Examples

### Basic Component Import

```javascript
import {
  StatusCard,
  AlertCard,
  VideoFeed,
  DailySummaryCard,
  ActivityItem,
  NavSidebar
} from './components';
```

### Complete Dashboard Section

```jsx
function MyCustomSection() {
  return (
    <div className="grid grid-cols-4 gap-6">
      <StatusCard
        title="Baby Detected"
        status="Yes"
        isActive={true}
        severity="success"
        icon="👶"
      />
      <StatusCard
        title="Adult Present"
        status="No"
        isActive={false}
        severity="info"
        icon="👤"
      />
      <StatusCard
        title="Baby State"
        status="Sleeping"
        isActive={true}
        severity="success"
        icon="💤"
      />
      <StatusCard
        title="Crying"
        status="No"
        isActive={false}
        severity="success"
        icon="🔊"
      />
    </div>
  );
}
```

### Alert System

```jsx
function AlertSystem() {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    wsService.subscribe('alert', (data) => {
      setAlerts(prev => [{
        id: Date.now(),
        message: data.message,
        severity: data.severity,
        timestamp: new Date().toLocaleTimeString()
      }, ...prev]);
    });
  }, []);

  return (
    <div className="space-y-4">
      {alerts.map(alert => (
        <AlertCard key={alert.id} alert={alert} />
      ))}
    </div>
  );
}
```

### Daily Summary Grid

```jsx
function DailySummary() {
  return (
    <div className="grid grid-cols-4 gap-8">
      <DailySummaryCard
        title="Sleep Duration"
        value="8.5h"
        change={12}
        icon="😴"
        variant="primary"
      />
      <DailySummaryCard
        title="Wake Periods"
        value="6"
        change={-8}
        icon="👶"
        variant="secondary"
      />
      <DailySummaryCard
        title="Crying Time"
        value="45m"
        change={-15}
        icon="😢"
        variant="warning"
      />
      <DailySummaryCard
        title="Adult Visits"
        value="12"
        change={5}
        icon="👤"
        variant="accent"
      />
    </div>
  );
}
```

### Activity Timeline

```jsx
function ActivityTimeline() {
  const activities = [
    {
      id: 1,
      type: 'sleep',
      description: 'Baby fell asleep',
      time: '2:30 PM',
      duration: '2h ago'
    },
    // ... more activities
  ];

  return (
    <div className="space-y-5">
      {activities.map(activity => (
        <ActivityItem key={activity.id} activity={activity} />
      ))}
    </div>
  );
}
```

---

## Styling Guidelines

### Color Variants

**Severity Colors:**
- `info`: Blue tones
- `success`: Green/Emerald tones
- `warning`: Orange tones
- `critical`: Red/Pink tones

**Card Variants:**
- `primary`: Indigo-Purple gradient
- `secondary`: White with colored border
- `accent`: Emerald-Teal gradient
- `warning`: Orange-Red gradient

### Animation Classes

```css
/* Available in animations.css */
.glass-effect       /* Glassmorphism effect */
.glass-card         /* Card with glass effect */
.neon-glow          /* Neon glow shadow */
.pulse-animation    /* Pulsing opacity */
.float-animation    /* Floating movement */
.fade-in            /* Fade in entrance */
.slide-up           /* Slide up entrance */
.hover-lift         /* Lift on hover */
.card-hover         /* Card hover effect */
```

### Responsive Breakpoints

```javascript
// Tailwind breakpoints
sm:   640px   // Small devices
md:   768px   // Medium devices
lg:   1024px  // Large devices
xl:   1280px  // Extra large
2xl:  1536px  // 2X Extra large
```

---

## Best Practices

### 1. Component Composition

```jsx
// ✅ Good - Composable and reusable
function MonitoringPanel() {
  return (
    <div className="grid grid-cols-2 gap-6">
      <StatusCard {...babyProps} />
      <StatusCard {...adultProps} />
    </div>
  );
}

// ❌ Bad - Hardcoded and inflexible
function MonitoringPanel() {
  return <div>Baby: Yes, Adult: No</div>;
}
```

### 2. State Management

```jsx
// ✅ Good - Centralized state
const [status, setStatus] = useState({
  baby: false,
  adult: false
});

// ❌ Bad - Scattered state
const [baby, setBaby] = useState(false);
const [adult, setAdult] = useState(false);
```

### 3. WebSocket Integration

```jsx
// ✅ Good - Proper cleanup
useEffect(() => {
  const handler = (data) => setStatus(data);
  wsService.subscribe('status', handler);
  return () => wsService.unsubscribe('status', handler);
}, []);

// ❌ Bad - Memory leak
useEffect(() => {
  wsService.subscribe('status', (data) => setStatus(data));
}, []); // No cleanup!
```

---

## Creating Custom Components

### Template Structure

```jsx
import React from 'react';

/**
 * ComponentName - Brief description
 */
function ComponentName({ prop1, prop2 }) {
  // State and hooks
  const [state, setState] = useState(initialState);

  // Event handlers
  const handleEvent = () => {
    // Logic here
  };

  // Render
  return (
    <div className="base-classes">
      {/* Component JSX */}
    </div>
  );
}

export default ComponentName;
```

### Adding to Component Library

1. Create component in `src/components/common/`
2. Add export to `src/components/index.js`:
   ```javascript
   export { default as ComponentName } from './common/ComponentName';
   ```
3. Import where needed:
   ```javascript
   import { ComponentName } from '../components';
   ```

---

## Component Testing

### Manual Testing Checklist

- [ ] Component renders without errors
- [ ] Props are properly typed and validated
- [ ] Responsive on mobile/tablet/desktop
- [ ] Animations work smoothly
- [ ] Hover states are visible
- [ ] Empty states handled gracefully
- [ ] Loading states (if applicable)
- [ ] Error states (if applicable)

---

## Resources

- [React Documentation](https://react.dev)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Component Patterns](https://www.patterns.dev/)

---

**Happy coding! 🚀**

