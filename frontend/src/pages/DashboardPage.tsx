// frontend/src/pages/DashboardPage.tsx
import React from 'react';
import { Target } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <Target className="h-16 w-16 text-green-500 mx-auto mb-4" />
        <h1 className="text-4xl font-bold text-gray-100 mb-2">ClientHunter</h1>
        <p className="text-xl text-gray-400 mb-8">AI Lead Generation Dashboard</p>
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 max-w-md mx-auto">
          <p className="text-gray-200">🚀 Темная тема работает!</p>
          <p className="text-gray-400 text-sm mt-2">Готов к созданию компонентов...</p>
        </div>
      </div>
    </div>
  );
};