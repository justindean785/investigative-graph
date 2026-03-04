import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import '@/index.css';
import Dashboard from './pages/Dashboard';
import InvestigationWorkspace from './pages/InvestigationWorkspace';
import { Toaster } from './components/ui/sonner';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const API_KEY = 'trace-analyst-secret-2026';

// Configure axios defaults
axios.defaults.headers.common['x-api-key'] = API_KEY;

export { API, API_KEY };

function App() {
  const [apiValid, setApiValid] = useState(null);

  useEffect(() => {
    // Validate API connection on mount
    const validateAPI = async () => {
      try {
        const response = await axios.post(`${API}/auth/validate`, {}, {
          headers: { 'x-api-key': API_KEY }
        });
        if (response.data.valid) {
          setApiValid(true);
        } else {
          setApiValid(false);
          toast.error('Invalid API key');
        }
      } catch (error) {
        console.error('API validation error:', error);
        setApiValid(false);
        toast.error('Failed to connect to API');
      }
    };

    validateAPI();
  }, []);

  if (apiValid === null) {
    return (
      <div className="min-h-screen bg-[#0a1628] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-[#00d9ff] border-r-transparent"></div>
          <p className="mt-4 text-[#94a3b8]">Connecting to Trace Analyst...</p>
        </div>
      </div>
    );
  }

  if (apiValid === false) {
    return (
      <div className="min-h-screen bg-[#0a1628] flex items-center justify-center">
        <div className="glass border border-[#00d9ff]/20 rounded-lg p-8 max-w-md text-center">
          <h2 className="text-xl font-bold text-[#00d9ff] mb-4">Connection Error</h2>
          <p className="text-[#94a3b8]">Unable to connect to the Trace Analyst API. Please check your configuration.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/investigation/:id" element={<InvestigationWorkspace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster 
        position="top-right"
        toastOptions={{
          style: {
            background: '#0d1b2a',
            border: '1px solid rgba(0, 217, 255, 0.2)',
            color: '#fff',
          },
        }}
      />
    </div>
  );
}

export default App;
