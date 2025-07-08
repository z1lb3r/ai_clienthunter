// frontend/src/components/Common/Sidebar.tsx
import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FileTemplate, 
  Search, 
  Users, 
  Settings,
  Target,
  Activity
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const menuItems = [
    {
      path: '/',
      icon: LayoutDashboard,
      label: 'Дашборд',
      description: 'Найденные клиенты'
    },
    {
      path: '/templates',
      icon: FileTemplate,
      label: 'Шаблоны',
      description: 'Продукты и ключевые слова'
    },
    {
      path: '/monitoring',
      icon: Search,
      label: 'Мониторинг',
      description: 'Настройка поиска'
    },
    {
      path: '/clients',
      icon: Users,
      label: 'История',
      description: 'Архив клиентов'
    },
    {
      path: '/settings',
      icon: Settings,
      label: 'Настройки',
      description: 'Конфигурация'
    }
  ];

  return (
    <div className="w-64 bg-dark-800 shadow-lg border-r border-dark-600">
      {/* Логотип */}
      <div className="flex items-center justify-center h-16 px-4 border-b border-dark-600">
        <div className="flex items-center space-x-2">
          <Target className="h-8 w-8 text-hunter-600" />
          <div>
            <h1 className="text-lg font-bold text-primary">ClientHunter</h1>
            <p className="text-xs text-muted">AI Lead Generation</p>
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
                className={({ isActive }) =>
                  `group flex items-center px-3 py-3 text-sm font-medium rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-hunter-900 text-hunter-400 border border-hunter-700'
                      : 'text-secondary hover:text-primary hover:bg-dark-700 border border-transparent'
                  }`
                }
              >
                <Icon className="mr-3 h-5 w-5 flex-shrink-0" />
                <div className="flex-1">
                  <div className="font-medium">{item.label}</div>
                  <div className="text-xs text-muted group-hover:text-secondary">
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
        <div className="bg-dark-700 rounded-lg p-3 border border-dark-600">
          <div className="flex items-center space-x-2">
            <Activity className="h-4 w-4 text-hunter-600" />
            <div className="flex-1">
              <div className="text-xs font-medium text-primary">Мониторинг</div>
              <div className="text-xs text-hunter-400">Активен</div>
            </div>
            <div className="w-2 h-2 bg-hunter-600 rounded-full animate-pulse"></div>
          </div>
        </div>
      </div>
    </div>
  );
};