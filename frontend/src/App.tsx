// frontend/src/App.tsx - ЗАМЕНИ ПОЛНОСТЬЮ
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardPage } from './pages/DashboardPage';
import { Sidebar } from './components/Common/Sidebar';
import { TemplatesPage } from './pages/TemplatesPage';
import { MonitoringPage } from './pages/MonitoringPage';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="flex h-screen bg-gray-900">
          <Sidebar />
          <div className="flex-1 overflow-hidden">
            <main className="h-full overflow-y-auto">
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/templates" element={<TemplatesPage />} />
                <Route path="/monitoring" element={<MonitoringPage />} />
              </Routes>
            </main>
          </div>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;