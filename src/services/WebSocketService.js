/**
 * WebSocket Service for real-time communication with the backend
 * Handles connection to detection WebSocket endpoint and fallback polling
 */
class WebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectTimeout = null;
    this.connectionUrl = null;
    this.isIntentionalClose = false;
    this.pollingInterval = null;
    this.pollingFallbackEnabled = false;
  }

  /**
   * Connect to WebSocket server
   * @param {string} url - WebSocket server URL
   */
  connect(url = 'ws://localhost:8000/api/v1/detections/live') {
    try {
      this.connectionUrl = url;
      this.isIntentionalClose = false;
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('WebSocket connected to detection endpoint');
        this.reconnectAttempts = 0;
        this.stopPolling(); // Stop polling if it was active
        this.notifyListeners('connection', { status: 'connected' });
      };

      this.ws.onmessage = (event) => {
        try {
          // Backend sends JSON strings directly
          const data = JSON.parse(event.data);
          
          // Notify detection listeners with the full detection data
          this.notifyListeners('detection', data);
          
          // Also support legacy event types if data.type is present
          if (data.type) {
            this.notifyListeners(data.type, data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          this.notifyListeners('parse_error', { error: error.message });
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.notifyListeners('connection', { status: 'disconnected' });
        
        // Only attempt reconnect if not intentional close
        if (!this.isIntentionalClose) {
          this.attemptReconnect(url);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.notifyListeners('connection', { status: 'error', error });
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.notifyListeners('connection', { status: 'error', error: error.message });
      
      // Start polling as fallback
      if (this.pollingFallbackEnabled) {
        this.startPolling();
      }
    }
  }

  /**
   * Attempt to reconnect to WebSocket server with exponential backoff
   * @param {string} url - WebSocket server URL
   */
  attemptReconnect(url) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      // Exponential backoff: 1s, 2s, 4s, 8s, 16s
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 16000);

      this.notifyListeners('connection', { 
        status: 'reconnecting',
        attempt: this.reconnectAttempts,
        maxAttempts: this.maxReconnectAttempts
      });

      this.reconnectTimeout = setTimeout(() => {
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        this.connect(url);
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
      this.notifyListeners('connection', { 
        status: 'failed',
        message: 'Failed to reconnect after maximum attempts' 
      });
      
      // Start polling as fallback if enabled
      if (this.pollingFallbackEnabled) {
        this.startPolling();
      }
    }
  }

  /**
   * Start REST polling as fallback when WebSocket fails
   * Polls GET /api/v1/detections/latest every 1 second
   */
  startPolling() {
    if (this.pollingInterval) return; // Already polling
    
    console.log('Starting REST polling fallback');
    this.notifyListeners('connection', { status: 'polling' });
    
    const pollEndpoint = async () => {
      try {
        const baseUrl = this.connectionUrl?.replace('ws://', 'http://').replace('wss://', 'https://').replace('/live', '/latest');
        const response = await fetch(baseUrl || 'http://localhost:8000/api/v1/detections/latest');
        
        if (response.ok) {
          const data = await response.json();
          this.notifyListeners('detection', data);
        } else {
          console.warn('Polling failed:', response.status);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    };
    
    // Poll immediately, then every second
    pollEndpoint();
    this.pollingInterval = setInterval(pollEndpoint, 1000);
  }

  /**
   * Stop REST polling
   */
  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
      console.log('Stopped REST polling');
    }
  }

  /**
   * Enable or disable REST polling fallback
   * @param {boolean} enabled - Whether to enable polling fallback
   */
  setPollingFallback(enabled) {
    this.pollingFallbackEnabled = enabled;
  }

  /**
   * Subscribe to WebSocket events
   * @param {string} eventType - Event type to listen for
   * @param {Function} callback - Callback function
   */
  subscribe(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
  }

  /**
   * Unsubscribe from WebSocket events
   * @param {string} eventType - Event type
   * @param {Function} callback - Callback function to remove
   */
  unsubscribe(eventType, callback) {
    if (this.listeners.has(eventType)) {
      const callbacks = this.listeners.get(eventType);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * Notify all listeners of an event
   * @param {string} eventType - Event type
   * @param {*} data - Event data
   */
  notifyListeners(eventType, data) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType).forEach(callback => callback(data));
    }
  }

  /**
   * Send data through WebSocket
   * @param {*} data - Data to send
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
      return true;
    } else {
      console.warn('WebSocket is not connected');
      return false;
    }
  }

  /**
   * Disconnect WebSocket and clean up
   */
  disconnect() {
    this.isIntentionalClose = true;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    this.stopPolling();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.listeners.clear();
    this.reconnectAttempts = 0;
    this.connectionUrl = null;
    
    this.notifyListeners('connection', { status: 'disconnected' });
  }

  /**
   * Get current connection status
   * @returns {string} - Connection status: 'connected', 'disconnected', 'reconnecting', 'polling', 'failed'
   */
  getConnectionStatus() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return 'connected';
    }
    if (this.pollingInterval) {
      return 'polling';
    }
    if (this.reconnectTimeout) {
      return 'reconnecting';
    }
    return 'disconnected';
  }

  /**
   * Check if connected (legacy method)
   * @returns {boolean} - Connection status
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// Create and export singleton instance
const wsService = new WebSocketService();
export default wsService;

