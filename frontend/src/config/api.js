import axios from 'axios';

function normalizeBackendUrl() {
  const raw = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
  return raw.trim().replace(/\/+$/, '');
}

export const API_KEY = process.env.REACT_APP_API_KEY;
export const BACKEND_URL = normalizeBackendUrl();
export const API = `${BACKEND_URL}/api`;

if (process.env.NODE_ENV === 'production' && !API_KEY) {
  // eslint-disable-next-line no-console
  console.error('REACT_APP_API_KEY is missing in production build');
}

// Configure axios defaults
axios.defaults.headers.common['x-api-key'] = API_KEY;
axios.defaults.timeout = 8000; // 8s - avoid infinite hang when backend/MongoDB unavailable

export default axios;
