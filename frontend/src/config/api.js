import axios from 'axios';

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_KEY = process.env.REACT_APP_API_KEY;

if (!BACKEND_URL) {
  const msg =
    '[Trace Analyst] REACT_APP_BACKEND_URL is not set. ' +
    'Set this variable in frontend/.env (dev) or in your deploy environment (prod).';
  // In production builds, fail fast so we don't silently call "undefined/api".
  if (process.env.NODE_ENV === 'production') {
    throw new Error(msg);
  } else {
    console.error(msg);
  }
}

export const API = `${BACKEND_URL}/api`;

if (!API_KEY) {
  console.error(
    '[Trace Analyst] REACT_APP_API_KEY is not set. ' +
    'API calls will fail with 401. Set this variable in frontend/.env.'
  );
}

// Configure axios defaults
axios.defaults.headers.common['x-api-key'] = API_KEY;

export default axios;
