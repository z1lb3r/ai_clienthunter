// frontend/src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Новые страницы для ClientHunter
import { DashboardPage } from './pages/DashboardPage';
import { TemplatesPage } from './pages/TemplatesPage';
import { MonitoringPage } from './pages/MonitoringPage';
import { ClientsHistoryPage } from './pages/ClientsHistoryPage';
import { SettingsPage } from './pages/SettingsPage';

// Обновленные компоненты
import { Sidebar } from './components/Common/Sidebar';
import { Header } from './components/Common/Header';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="flex h-screen bg-dark-900">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <Header />
            <main className="flex-1 overflow-x-hidden overflow-y-auto bg-dark-900">
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/templates" element={<TemplatesPage />} />
                <Route path="/monitoring" element={<MonitoringPage />} />
                <Route path="/clients" element={<ClientsHistoryPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </main>
          </div>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App; 