import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Works API
export const worksAPI = {
  // List all works with optional search
  list: async (search = '') => {
    const response = await api.get('/api/works', {
      params: search ? { search } : {}
    });
    return response.data;
  },

  // Get detailed work information
  get: async (workNumber) => {
    const response = await api.get(`/api/works/${workNumber}`);
    return response.data;
  },
};

// Jobs API
export const jobsAPI = {
  // Create a new translation job
  create: async (workNumbers, config = {}) => {
    const response = await api.post('/api/jobs', {
      work_numbers: workNumbers,
      model: config.model || 'gpt-4.1-nano',
      temperature: config.temperature || 0.3,
      max_retries: config.max_retries || 3,
      output_dir: config.output_dir || null,
    });
    return response.data;
  },

  // List all jobs
  list: async () => {
    const response = await api.get('/api/jobs');
    return response.data;
  },

  // Get job status
  get: async (jobId) => {
    const response = await api.get(`/api/jobs/${jobId}`);
    return response.data;
  },

  // Cancel a job
  cancel: async (jobId) => {
    const response = await api.delete(`/api/jobs/${jobId}`);
    return response.data;
  },

  // Get detailed progress for a job's current work
  getDetailedProgress: async (jobId) => {
    const response = await api.get(`/api/jobs/${jobId}/progress`);
    return response.data;
  },
};

// Progress API
export const progressAPI = {
  // Get detailed progress for a work/volume
  get: async (workNumber, volume = null) => {
    const params = volume ? { volume } : {};
    const response = await api.get(`/api/progress/${workNumber}`, { params });
    return response.data;
  },
};

// WebSocket connection
export class JobWebSocket {
  constructor(onMessage) {
    this.ws = null;
    this.onMessage = onMessage;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws';
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      // Send ping every 30 seconds to keep connection alive
      this.pingInterval = setInterval(() => {
        if (this.ws.readyState === WebSocket.OPEN) {
          this.ws.send('ping');
        }
      }, 30000);
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.onMessage(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      clearInterval(this.pingInterval);

      // Attempt to reconnect
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), 3000);
      }
    };
  }

  disconnect() {
    if (this.ws) {
      clearInterval(this.pingInterval);
      this.ws.close();
      this.ws = null;
    }
  }
}

export default api;
