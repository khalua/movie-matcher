import axios from 'axios';

// Determine API URL based on environment
// In production (same-origin), use relative URLs
// In development, use separate backend port
const getApiUrl = () => {
  // If explicitly set, use that
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

  // In production, frontend is served by Flask, so use same origin (empty string for relative URLs)
  if (process.env.NODE_ENV === 'production') {
    return '';
  }

  // In development, use separate backend port
  const API_PORT = process.env.REACT_APP_API_PORT || '5001';
  return `http://${window.location.hostname}:${API_PORT}`;
};

const API_URL = getApiUrl();

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
