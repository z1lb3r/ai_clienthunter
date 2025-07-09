// frontend/src/pages/DashboardPage.tsx
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
  Star,
  Loader2,
  AlertCircle
} from 'lucide-react';

import { 
  useDashboardStats, 
  usePotentialClients, 
  useProductTemplates,
  useUpdateClientStatus,
  useMonitoringSettings
} from '../hooks/useClientHunterApi';
import { PotentialClient, ProductTemplate } from '../types/api';

export const DashboardPage: React.FC = () => {
  // API хуки
  const { data: stats, isLoading: statsLoading, error: statsError } = useDashboardStats();
  const { data: clientsResponse, isLoading: clientsLoading, error: clientsError } = usePotentialClients({ limit: 10 });
  const { data: templatesResponse, isLoading: templatesLoading } = useProductTemplates();
  const { data: monitoringResponse } = useMonitoringSettings();
  
  const updateClientStatusMutation = useUpdateClientStatus();

  // Обработка данных
  const clients = clientsResponse?.data || [];
  const templates = templatesResponse?.data || [];
  const monitoringSettings = monitoringResponse?.data;
  const isMonitoringActive = monitoringSettings?.is_active || false;

  // Вычисляем топ шаблоны на основе реальных данных
  const getTopTemplates = () => {
    if (!clients.length || !templates.length) return [];

    const templateStats = templates.map(template => {
      const templateClients = clients.filter(client => client.matched_template_id === template.id);
      const avgConfidence = templateClients.length > 0 
        ? templateClients.reduce((sum, client) => sum + client.ai_confidence, 0) / templateClients.length
        : 0;

      return {
        id: template.id,
        name: template.name,
        clients: templateClients.length,
        confidence: Math.round(avgConfidence * 10) / 10
      };
    });

    return templateStats
      .filter(stat => stat.clients > 0)
      .sort((a, b) => b.clients - a.clients)
      .slice(0, 3);
  };

  const topTemplates = getTopTemplates();

  // Функция для изменения статуса клиента
  const handleStatusChange = async (clientId: number, newStatus: 'new' | 'contacted' | 'ignored' | 'converted') => {
    try {
      await updateClientStatusMutation.mutateAsync({
        clientId,
        statusUpdate: { status: newStatus }
      });
    } catch (error) {
      console.error('Failed to update client status:', error);
    }
  };

  // Функция для получения информации о шаблоне
  const getTemplateName = (templateId: number) => {
    const template = templates.find(t => t.id === templateId);
    return template?.name || 'Неизвестный шаблон';
  };

  // Функция для форматирования имени клиента
  const getClientDisplayName = (client: PotentialClient) => {
    if (client.username) return `@${client.username}`;
    if (client.first_name || client.last_name) {
      return `${client.first_name || ''} ${client.last_name || ''}`.trim();
    }
    return `User ${client.telegram_user_id}`;
  };

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

  // Форматирование времени
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('ru-RU', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // Компонент ошибки
  const ErrorMessage = ({ message }: { message: string }) => (
    <div className="flex items-center justify-center p-8 text-red-400">
      <AlertCircle className="h-5 w-5 mr-2" />
      <span>{message}</span>
    </div>
  );

  // Компонент загрузки
  const LoadingSpinner = () => (
    <div className="flex items-center justify-center p-8">
      <Loader2 className="h-6 w-6 animate-spin text-green-500" />
    </div>
  );

  return (
    <div className="h-full bg-gray-900 p-6 overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        
        {/* Заголовок */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-100">Dashboard</h1>
            <div className="flex items-center mt-1 space-x-2">
              <p className="text-gray-400">Мониторинг потенциальных клиентов</p>
              <div className="flex items-center space-x-1">
                <div className={`w-2 h-2 rounded-full ${isMonitoringActive ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                <span className={`text-xs font-medium ${isMonitoringActive ? 'text-green-400' : 'text-red-400'}`}>
                  {isMonitoringActive ? 'Активен' : 'Остановлен'}
                </span>
              </div>
            </div>
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
          {statsLoading ? (
            <>
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                  <LoadingSpinner />
                </div>
              ))}
            </>
          ) : statsError ? (
            <div className="col-span-4">
              <ErrorMessage message="Ошибка загрузки статистики" />
            </div>
          ) : stats ? (
            <>
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
            </>
          ) : null}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Основная таблица клиентов */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 border border-gray-700 rounded-lg">
              <div className="px-6 py-4 border-b border-gray-700">
                <h2 className="text-xl font-semibold text-gray-100">Последние клиенты</h2>
              </div>
              
              {clientsLoading ? (
                <LoadingSpinner />
              ) : clientsError ? (
                <ErrorMessage message="Ошибка загрузки клиентов" />
              ) : clients.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Клиенты не найдены</p>
                  <p className="text-sm mt-1">Запустите мониторинг для поиска клиентов</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-700">
                  {clients.map((client) => (
                    <div key={client.id} className="p-6 hover:bg-gray-750 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <div className="flex items-center space-x-2">
                              <div className={`w-2 h-2 rounded-full ${getStatusColor(client.client_status)}`}></div>
                              <span className="font-medium text-gray-100">
                                {getClientDisplayName(client)}
                              </span>
                            </div>
                            <span className="text-xs px-2 py-1 bg-green-900 text-green-300 rounded">
                              {getTemplateName(client.matched_template_id)}
                            </span>
                            <span className="text-xs text-gray-400">
                              {formatTime(client.created_at)}
                            </span>
                          </div>
                          
                          <p className="text-gray-300 text-sm mb-3 line-clamp-2">
                            {client.message_text}
                          </p>
                          
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-4">
                              <span className="text-xs text-gray-400">
                                Уверенность: <span className="text-green-400 font-medium">{client.ai_confidence}/10</span>
                              </span>
                              
                              {/* Интерактивное изменение статуса */}
                              <select 
                                value={client.client_status}
                                onChange={(e) => handleStatusChange(client.id, e.target.value as any)}
                                disabled={updateClientStatusMutation.isPending}
                                className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded border border-gray-600 focus:border-green-500 focus:outline-none"
                              >
                                <option value="new">Новый</option>
                                <option value="contacted">Связались</option>
                                <option value="ignored">Игнор</option>
                                <option value="converted">Конверсия</option>
                              </select>
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
              )}
              
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
              
              {templatesLoading ? (
                <LoadingSpinner />
              ) : topTemplates.length === 0 ? (
                <div className="text-center text-gray-400 py-4">
                  <Target className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Нет данных по шаблонам</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {topTemplates.map((template, index) => (
                    <div key={template.id} className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-200">{template.name}</p>
                        <p className="text-xs text-gray-400">{template.clients} клиентов</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-green-400">{template.confidence}</p>
                        <p className="text-xs text-gray-400">ср. увер.</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Быстрые действия */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Быстрые действия</h3>
              <div className="space-y-3">
                <button className="w-full flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                  <Plus className="h-4 w-4 mr-2" />
                  Новый шаблон
                </button>
                <button className="w-full flex items-center justify-center px-4 py-2 bg-gray-700 text-gray-200 rounded-lg hover:bg-gray-600 transition-colors">
                  <Settings className="h-4 w-4 mr-2" />
                  Настройки
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};