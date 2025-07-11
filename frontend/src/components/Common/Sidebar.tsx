// frontend/src/components/Common/Sidebar.tsx
import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FileText, 
  Settings,
  Target,
  Activity,
  Loader2,
  Monitor
} from 'lucide-react';
import { useMonitoringSettings } from '../../hooks/useClientHunterApi';

export const Sidebar: React.FC = () => {
  const { data: monitoringResponse, isLoading } = useMonitoringSettings();
  const monitoringSettings = monitoringResponse?.data;
  const isMonitoringActive = monitoringSettings?.is_active || false;

  const menuItems = [
    {
      path: '/',
      icon: LayoutDashboard,
      label: 'Дашборд',
      description: 'Найденные клиенты'
    },
    {
      path: '/templates',
      icon:  FileText,
      label: 'Шаблоны',
      description: 'Управление продуктами'
    },
    {
      path: '/monitoring',
      icon: Monitor,
      label: 'Мониторинг',
      description: 'Настройки поиска'
    }
  ];

  return (
    <div className="w-64 bg-gray-800 shadow-lg border-r border-gray-600">
      {/* Логотип */}
      <div className="flex items-center justify-center h-16 px-4 border-b border-gray-600">
        <div className="flex items-center space-x-2">
          <Target className="h-8 w-8 text-green-500" />
          <div>
            <h1 className="text-lg font-bold text-gray-100">ClientHunter</h1>
            <p className="text-xs text-gray-400">AI Lead Generation</p>
          </div>
        </div>
      </div>

      {/* Навигация */}
      <nav className="mt-8 px-4">
        <div className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  group flex items-center px-3 py-3 text-sm font-medium rounded-lg transition-all duration-200
                  ${isActive 
                    ? 'bg-green-600 text-white border border-green-500 shadow-lg' 
                    : 'bg-gray-700 text-gray-100 border border-gray-600 hover:bg-gray-600 hover:border-gray-500'
                  }
                `}
              >
                <Icon className="mr-3 h-5 w-5 flex-shrink-0" />
                <div className="flex-1">
                  <div className="font-medium">{item.label}</div>
                  <div className="text-xs text-gray-400">
                    {item.description}
                  </div>
                </div>
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Статус мониторинга */}
      <div className="absolute bottom-4 left-4 right-4">
        <div className="bg-gray-700 rounded-lg p-3 border border-gray-600">
          <div className="flex items-center space-x-2">
            {isLoading ? (
              <Loader2 className="h-4 w-4 text-gray-400 animate-spin" />
            ) : (
              <Activity className={`h-4 w-4 ${isMonitoringActive ? 'text-green-500' : 'text-red-500'}`} />
            )}
            <div className="flex-1">
              <div className="text-xs font-medium text-gray-100">Мониторинг</div>
              <div className={`text-xs ${isMonitoringActive ? 'text-green-400' : 'text-red-400'}`}>
                {isLoading ? 'Загрузка...' : (isMonitoringActive ? 'Активен' : 'Остановлен')}
              </div>
            </div>
            {!isLoading && (
              <div className={`w-2 h-2 rounded-full ${isMonitoringActive ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};