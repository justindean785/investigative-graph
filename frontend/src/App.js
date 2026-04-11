import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import '@/index.css';
import Dashboard from './pages/Dashboard';
import UnifiedInvestigation from './components/investigation/UnifiedInvestigation';
import { Toaster } from './components/ui/sonner';

function App() {
  return (
    <div className="App">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:bg-primary focus:text-white focus:px-4 focus:py-2 focus:rounded-sm focus:text-sm">
        Skip to main content
      </a>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/investigation/:id" element={<UnifiedInvestigation />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster 
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgba(0, 0, 0, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: '#fff',
            backdropFilter: 'blur(20px)',
          },
        }}
      />
    </div>
  );
}

export default App;
