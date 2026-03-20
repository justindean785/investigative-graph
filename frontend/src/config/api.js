import axios from 'axios';

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
export const API_KEY = process.env.REACT_APP_API_KEY || 'trace-analyst-secret-2026';

// Configure axios defaults
axios.defaults.headers.common['x-api-key'] = API_KEY;

export default axios;
