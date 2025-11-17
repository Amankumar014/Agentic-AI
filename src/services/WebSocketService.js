/**
 * WebSocket Service for real-time communication with the backend
 */
class WebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectTimeout = null;
  }

  /**
   * Connect to WebSocket server
   * @param {string} url - WebSocket server URL
   */
  connect(url = 'ws://localhost:8000/ws') {
    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.notifyListeners('connection', { status: 'connected' });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners(data.type, data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.notifyListeners('connection', { status: 'disconnected' });
        this.attemptReconnect(url);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.notifyListeners('error', { error });
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }

  /**
   * Attempt to reconnect to WebSocket server
   * @param {string} url - WebSocket server URL
   */
  attemptReconnect(url) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = 3000 * this.reconnectAttempts;

      this.reconnectTimeout = setTimeout(() => {
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
        this.connect(url);
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
      this.notifyListeners('connection', { 
        status: 'failed',
        message: 'Failed to reconnect after maximum attempts' 
      });
    }
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
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.listeners.clear();
    this.reconnectAttempts = 0;
  }

  /**
   * Get current connection status
   * @returns {boolean} - Connection status
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// Create and export singleton instance
const wsService = new WebSocketService();
export default wsService;

