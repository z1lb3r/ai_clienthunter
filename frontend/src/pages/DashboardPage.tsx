// frontend/src/pages/DashboardPage.tsx - ЗАМЕНИ ПОЛНОСТЬЮ
import React from 'react';
import { 
  Target, 
  Plus, 
  Settings, 
  Users, 
  TrendingUp, 
  Clock,
  MessageSquare,
  ExternalLink,
  Star
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  // Заглушечные данные
  const stats = {
    clientsToday: 12,
    clientsWeek: 47,
    totalClients: 234,
    conversionRate: 23.5
  };

  const topTemplates = [
    { name: 'iPhone ремонт', clients: 15, confidence: 8.7 },
    { name: 'Доставка еды', clients: 12, confidence: 7.9 },
    { name: 'Репетиторы', clients: 8, confidence: 8.1 }
  ];

  const recentClients = [
    {
      id: 1,
      username: '@ivan_petrov',
      name: 'Иван Петров',
      message: 'Нужен мастер по ремонту iPhone 13, экран разбился...',
      template: 'iPhone ремонт',
      confidence: 9.2,
      time: '15:30',
      status: 'new'
    },
    {
      id: 2,
      username: '@maria_k',
      name: 'Мария',
      message: 'Ищу хорошую доставку суши в районе Арбата',
      template: 'Доставка еды',
      confidence: 8.5,
      time: '14:45',
      status: 'contacted'
    },
    {
      id: 3,
      username: null,
      name: 'Анна Смирнова',
      message: 'Нужен репетитор по математике для 9 класса...',
      template: 'Репетиторы',
      confidence: 7.8,
      time: '13:20',
      status: 'new'
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new': return 'bg-green-500';
      case 'contacted': return 'bg-blue-500';
      case 'ignored': return 'bg-gray-500';
      case 'converted': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'new': return 'Новый';
      case 'contacted': return 'Связались';
      case 'ignored': return 'Игнор';
      case 'converted': return 'Конверсия';
      default: return 'Неизвестно';
    }
  };

  return (
    <div className="h-full bg-gray-900 p-6 overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        
        {/* Заголовок */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-100">Dashboard</h1>
            <p className="text-gray-400 mt-1">Мониторинг потенциальных клиентов</p>
          </div>
          <div className="flex space-x-3">
            <button className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
              <Plus className="h-4 w-4 mr-2" />
              Добавить шаблон
            </button>
            <button className="flex items-center px-4 py-2 bg-gray-700 text-gray-200 rounded-lg hover:bg-gray-600 transition-colors">
              <Settings className="h-4 w-4 mr-2" />
              Настроить мониторинг
            </button>
          </div>
        </div>

        {/* Статистические карточки */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-green-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">Сегодня</p>
                <p className="text-2xl font-bold text-gray-100">{stats.clientsToday}</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center">
              <TrendingUp className="h-8 w-8 text-blue-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">За неделю</p>
                <p className="text-2xl font-bold text-gray-100">{stats.clientsWeek}</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center">
              <Target className="h-8 w-8 text-purple-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">Всего</p>
                <p className="text-2xl font-bold text-gray-100">{stats.totalClients}</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center">
              <Star className="h-8 w-8 text-yellow-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">Конверсия</p>
                <p className="text-2xl font-bold text-gray-100">{stats.conversionRate}%</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Основная таблица клиентов */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 border border-gray-700 rounded-lg">
              <div className="px-6 py-4 border-b border-gray-700">
                <h2 className="text-xl font-semibold text-gray-100">Последние клиенты</h2>
              </div>
              
              <div className="divide-y divide-gray-700">
                {recentClients.map((client) => (
                  <div key={client.id} className="p-6 hover:bg-gray-750 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <div className="flex items-center space-x-2">
                            <div className={`w-2 h-2 rounded-full ${getStatusColor(client.status)}`}></div>
                            <span className="font-medium text-gray-100">
                              {client.username || client.name}
                            </span>
                          </div>
                          <span className="text-xs px-2 py-1 bg-green-900 text-green-300 rounded">
                            {client.template}
                          </span>
                          <span className="text-xs text-gray-400">{client.time}</span>
                        </div>
                        
                        <p className="text-gray-300 text-sm mb-3 line-clamp-2">
                          {client.message}
                        </p>
                        
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <span className="text-xs text-gray-400">
                              Уверенность: <span className="text-green-400 font-medium">{client.confidence}/10</span>
                            </span>
                            <span className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded">
                              {getStatusText(client.status)}
                            </span>
                          </div>
                          <button className="text-gray-400 hover:text-gray-200 transition-colors">
                            <ExternalLink className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="px-6 py-4 border-t border-gray-700">
                <button className="w-full text-center text-green-400 hover:text-green-300 text-sm">
                  Показать всех клиентов →
                </button>
              </div>
            </div>
          </div>

          {/* Боковая панель */}
          <div className="space-y-6">
            
            {/* Топ шаблоны */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Топ шаблоны</h3>
              <div className="space-y-4">
                {topTemplates.map((template, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-200">{template.name}</p>
                      <p className="text-xs text-gray-400">{template.clients} клиентов</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-green-400">{template.confidence}</p>
                      <p className="text-xs text-gray-400">ср. уверенность</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Быстрые действия */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Быстрые действия</h3>
              <div className="space-y-3">
                <button className="w-full flex items-center px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-left">
                  <MessageSquare className="h-5 w-5 text-gray-400 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-200">Управление шаблонами</p>
                    <p className="text-xs text-gray-400">Создать или изменить</p>
                  </div>
                </button>
                
                <button className="w-full flex items-center px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-left">
                  <Clock className="h-5 w-5 text-gray-400 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-200">Настройки мониторинга</p>
                    <p className="text-xs text-gray-400">Чаты и интервалы</p>
                  </div>
                </button>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};