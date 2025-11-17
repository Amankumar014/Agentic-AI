# Baby Monitor Dashboard

AI-powered baby monitoring dashboard with real-time alerts and comprehensive insights.

## Features

- 🎥 Live camera feed monitoring
- 👶 Real-time baby detection and state tracking
- 🔔 Intelligent alert system with severity levels
- 📊 Daily activity summaries and analytics
- ⚙️ Customizable settings and detection options
- 🌐 WebSocket-based real-time updates
- 📱 Responsive and modern UI design

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

The application will open at [http://localhost:3000](http://localhost:3000).

### Backend Setup

Make sure your backend server is running on `http://localhost:8000` with WebSocket support at `ws://localhost:8000/ws`.

## Project Structure

```
baby_frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── StatusCard.jsx
│   │   │   ├── AlertCard.jsx
│   │   │   ├── VideoFeed.jsx
│   │   │   ├── DailySummaryCard.jsx
│   │   │   └── ActivityItem.jsx
│   │   ├── layout/
│   │   │   └── NavSidebar.jsx
│   │   └── index.js
│   ├── pages/
│   │   ├── Dashboard.jsx
│   │   ├── Alerts.jsx
│   │   └── Settings.jsx
│   ├── services/
│   │   └── WebSocketService.js
│   ├── styles/
│   │   ├── index.css
│   │   └── animations.css
│   ├── App.jsx
│   └── index.js
├── package.json
├── tailwind.config.js
└── README.md
```

## Available Scripts

- `npm start` - Runs the app in development mode
- `npm build` - Builds the app for production
- `npm test` - Runs the test suite

## Configuration

The app connects to the backend WebSocket at `ws://localhost:8000/ws` by default. You can modify this in the Settings page or in `src/services/WebSocketService.js`.

## Technologies Used

- React 18
- Tailwind CSS
- WebSocket API
- Modern CSS animations

## License

MIT

