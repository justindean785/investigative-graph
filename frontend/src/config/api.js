import axios from 'axios';

function normalizeBackendUrl() {
  const raw = process.env.REACT_APP_BACKEND_URL;
  const trimmed = typeof raw === 'string' ? raw.trim() : '';
  if (!trimmed) {
    if (process.env.NODE_ENV === 'production') {
      throw new Error(
        'REACT_APP_BACKEND_URL is required for production builds. Set it in the environment (see frontend/.env.example).'
      );
    }
    // eslint-disable-next-line no-console
    console.warn(
      '[api] REACT_APP_BACKEND_URL is unset; using http://localhost:8001 for development.'
    );
    return 'http://localhost:8001';
  }
  return trimmed.replace(/\/+$/, '');
}

export const BACKEND_URL = normalizeBackendUrl();
export const API = `${BACKEND_URL}/api`;
export const API_KEY = process.env.REACT_APP_API_KEY || 'trace-analyst-secret-2026';

// Configure axios defaults
axios.defaults.headers.common['x-api-key'] = API_KEY;
axios.defaults.timeout = 8000; // 8s - avoid infinite hang when backend/MongoDB unavailable

export default axios;
