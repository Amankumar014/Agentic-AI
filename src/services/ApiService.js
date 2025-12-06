/**
 * API Service for Backend Integration
 * Handles all HTTP requests to the FastAPI backend
 */

// Base URL - can be configured via environment variable
const BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi(endpoint, options = {}) {
  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      // Handle HTTP errors
      throw {
        status: response.status,
        message: data.detail || `HTTP ${response.status} error`,
        data,
      };
    }

    return data;
  } catch (error) {
    // Network errors or JSON parse errors
    if (error.status) {
      throw error; // Re-throw HTTP errors
    }
    throw {
      status: 0,
      message: 'Network error or server unreachable',
      error,
    };
  }
}

/**
 * Fetch wrapper for multipart/form-data
 */
async function fetchMultipart(endpoint, formData) {
  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary
    });

    const data = await response.json();

    if (!response.ok) {
      throw {
        status: response.status,
        message: data.detail || `HTTP ${response.status} error`,
        data,
      };
    }

    return data;
  } catch (error) {
    if (error.status) {
      throw error;
    }
    throw {
      status: 0,
      message: 'Network error or server unreachable',
      error,
    };
  }
}

/**
 * ============================================
 * 1. HEALTH AND SYSTEM STATUS
 * ============================================
 */

/**
 * Check API health status
 * GET /api/v1/health/
 */
export async function checkHealth() {
  return fetchApi('/api/v1/health/');
}

/**
 * Get system statistics
 * GET /api/v1/stats/
 */
export async function getStats() {
  return fetchApi('/api/v1/stats/');
}

/**
 * ============================================
 * 2. FRAME AND AUDIO ANALYSIS
 * ============================================
 */

/**
 * Upload frame for analysis
 * POST /api/v1/frames/
 * @param {File} imageFile - Image file (JPEG/PNG, max 10MB)
 */
export async function uploadFrame(imageFile) {
  if (!imageFile) {
    throw { status: 400, message: 'Image file is required' };
  }

  if (imageFile.size > 10 * 1024 * 1024) {
    throw { status: 400, message: 'Image file must be less than 10 MB' };
  }

  const formData = new FormData();
  formData.append('file', imageFile);

  return fetchMultipart('/api/v1/frames/', formData);
}

/**
 * Upload frame with audio for analysis
 * POST /api/v1/frames/with-audio/
 * @param {File} imageFile - Image file (JPEG/PNG, max 10MB)
 * @param {File} audioFile - Audio file (max 10MB)
 */
export async function uploadFrameWithAudio(imageFile, audioFile) {
  if (!imageFile || !audioFile) {
    throw { status: 400, message: 'Both image and audio files are required' };
  }

  if (imageFile.size > 10 * 1024 * 1024) {
    throw { status: 400, message: 'Image file must be less than 10 MB' };
  }

  if (audioFile.size > 10 * 1024 * 1024) {
    throw { status: 400, message: 'Audio file must be less than 10 MB' };
  }

  const formData = new FormData();
  formData.append('file', imageFile);
  formData.append('audio', audioFile);

  return fetchMultipart('/api/v1/frames/with-audio/', formData);
}

/**
 * ============================================
 * 3. ALERTS AND LOGS
 * ============================================
 */

/**
 * Get recent alerts
 * GET /api/v1/alerts/
 * @param {number} limit - Number of alerts to retrieve (1-500, default 50)
 */
export async function getAlerts(limit = 50) {
  if (limit < 1 || limit > 500) {
    throw { status: 400, message: 'Limit must be between 1 and 500' };
  }
  return fetchApi(`/api/v1/alerts/?limit=${limit}`);
}

/**
 * Get recent frame analysis logs
 * GET /api/v1/logs/
 * @param {number} limit - Number of logs to retrieve (1-500, default 50)
 */
export async function getLogs(limit = 50) {
  if (limit < 1 || limit > 500) {
    throw { status: 400, message: 'Limit must be between 1 and 500' };
  }
  return fetchApi(`/api/v1/logs/?limit=${limit}`);
}

/**
 * ============================================
 * 4. CHATBOT (RAG-based assistant)
 * ============================================
 */

/**
 * Ask the chatbot a question
 * POST /api/v1/chatbot/ask
 * @param {string} question - Question to ask (non-empty, max 500 chars)
 */
export async function askChatbot(question) {
  if (!question || question.trim().length === 0) {
    throw { status: 400, message: 'Question cannot be empty' };
  }

  if (question.length > 500) {
    throw { status: 400, message: 'Question must be 500 characters or less' };
  }

  return fetchApi('/api/v1/chatbot/ask', {
    method: 'POST',
    body: JSON.stringify({ question: question.trim() }),
  });
}

/**
 * Check chatbot index status
 * GET /api/v1/chatbot/status
 */
export async function getChatbotStatus() {
  return fetchApi('/api/v1/chatbot/status');
}

/**
 * Rebuild chatbot index (admin only)
 * POST /api/v1/chatbot/rebuild_index
 */
export async function rebuildChatbotIndex() {
  return fetchApi('/api/v1/chatbot/rebuild_index', {
    method: 'POST',
  });
}

/**
 * ============================================
 * UTILITY FUNCTIONS
 * ============================================
 */

/**
 * Format error message for display
 * @param {Object} error - Error object from API calls
 * @returns {string} - User-friendly error message
 */
export function formatErrorMessage(error) {
  if (!error) return 'An unknown error occurred';

  // Network errors
  if (error.status === 0) {
    return 'Unable to connect to server. Please check your connection and try again.';
  }

  // Client errors (4xx)
  if (error.status >= 400 && error.status < 500) {
    return error.message || 'Invalid request. Please check your input.';
  }

  // Server errors (5xx)
  if (error.status >= 500) {
    return 'Server error. Please try again later.';
  }

  return error.message || 'An error occurred';
}

/**
 * Check if error is a file size error
 * @param {Object} error - Error object
 * @returns {boolean}
 */
export function isFileSizeError(error) {
  return error.message && error.message.toLowerCase().includes('10 mb');
}

/**
 * Get base URL (useful for debugging)
 */
export function getBaseUrl() {
  return BASE_URL;
}

/**
 * ============================================
 * 5. VIDEO STREAMING
 * ============================================
 */

/**
 * Get MJPEG stream URL (raw video feed)
 * The stream endpoint provides Motion JPEG video that can be displayed in an <img> tag
 * @returns {string} - Full URL to the raw MJPEG stream endpoint
 */
export function getStreamUrl() {
  return `${BASE_URL}/api/v1/stream/`;
}

/**
 * Get annotated MJPEG stream URL (with detection overlays)
 * The annotated stream includes real-time detection visualizations:
 * - Green pose skeleton lines (33 keypoints)
 * - Magenta face mesh lines (468 points)
 * - Cyan iris tracking markers
 * - Yellow bounding boxes (babies)
 * - Orange bounding boxes (adults)
 * - Status overlay bar with alerts and state
 * @returns {string} - Full URL to the annotated MJPEG stream endpoint
 */
export function getAnnotatedStreamUrl() {
  return `${BASE_URL}/api/v1/stream/annotated/`;
}

/**
 * Get audio stream URL (live audio from baby monitor)
 * Continuous WAV audio stream from the baby monitor microphone
 * Can be played using HTML5 <audio> element
 * @returns {string} - Full URL to the audio stream endpoint
 */
export function getAudioStreamUrl() {
  return `${BASE_URL}/api/v1/stream/audio/`;
}

/**
 * ============================================
 * 6. REAL-TIME DETECTIONS
 * ============================================
 */

/**
 * Get latest detection data (REST fallback for WebSocket)
 * GET /api/v1/detections/latest
 * @returns {Promise<Object>} - Latest detection data with yolo, pose, movement, emotion, etc.
 */
export async function getLatestDetection() {
  return fetchApi('/api/v1/detections/latest');
}

/**
 * Get WebSocket URL for live detections
 * @returns {string} - WebSocket URL for live detection stream
 */
export function getDetectionWebSocketUrl() {
  const wsProtocol = BASE_URL.startsWith('https') ? 'wss' : 'ws';
  const baseWithoutProtocol = BASE_URL.replace('http://', '').replace('https://', '');
  return `${wsProtocol}://${baseWithoutProtocol}/api/v1/detections/live`;
}

// Export all functions as default object as well
const ApiService = {
  checkHealth,
  getStats,
  uploadFrame,
  uploadFrameWithAudio,
  getAlerts,
  getLogs,
  askChatbot,
  getChatbotStatus,
  rebuildChatbotIndex,
  formatErrorMessage,
  isFileSizeError,
  getBaseUrl,
  getStreamUrl,
  getAnnotatedStreamUrl,
  getAudioStreamUrl,
  getLatestDetection,
  getDetectionWebSocketUrl,
};

export default ApiService;

