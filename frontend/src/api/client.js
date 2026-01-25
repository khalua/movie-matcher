import axios from 'axios';

// Use the same hostname as the frontend, but on the backend port
const API_PORT = process.env.REACT_APP_API_PORT || '5001';
const API_URL = process.env.REACT_APP_API_URL || `http://${window.location.hostname}:${API_PORT}`;

// Create axios instance
const client = axios.create({
  baseURL: API_URL
});

// Request interceptor to add auth token and circle context
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Add circle context from localStorage
    const circleId = localStorage.getItem('currentCircleId');
    if (circleId) {
      config.headers['X-Circle-Id'] = circleId;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired, redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('currentCircleId');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

export default client;
