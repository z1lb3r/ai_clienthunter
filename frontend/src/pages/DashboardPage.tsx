// frontend/src/pages/DashboardPage.tsx
import React, { useState } from 'react';
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
import { ProductTemplateModal } from '../components/ProductTemplates/ProductTemplateModal';

export const DashboardPage: React.FC = () => {
  // Состояние модального окна
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ProductTemplate | undefined>();

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

  // Обработчики модального окна
  const handleCreateTemplate = () => {
    setEditingTemplate(undefined);
    setIsTemplateModalOpen(true);
  };

  const handleEditTemplate = (template: ProductTemplate) => {
    setEditingTemplate(template);
    setIsTemplateModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsTemplateModalOpen(false);
    setEditingTemplate(undefined);
  };

  // Вычисляем топ шаблоны на основе реальных данных
  const getTopTemplates = () => {
    if (!clients.length || !templates.length) return [];

    const templateStats = templates.map(template => {
      const templateClients = clients.filter(client => client.matched_template_id === template.id);

      return {
        id: template.id,
        name: template.name,
        clients: templateClients.length
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

  // Компоненты загрузки и ошибок
  const LoadingSpinner = () => (
    <div className="flex items-center justify-center py-4">
      <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
    </div>
  );

  const ErrorMessage = ({ message }: { message: string }) => (
    <div className="flex items-center justify-center py-4 text-red-400">
      <AlertCircle className="h-5 w-5 mr-2" />
      <span>{message}</span>
    </div>
  );

  return (
    <div className="p-6 bg-gray-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Заголовок и быстрые действия */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Панель управления</h1>
            <div className="flex items-center mt-2 text-sm text-gray-400">
              <div className="flex items-center space-x-2">
                <span>Статус мониторинга:</span>
                <div className={`w-2 h-2 rounded-full ${isMonitoringActive ? 
                  'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                <span className={`text-xs font-medium ${isMonitoringActive ? 'text-green-400' : 'text-red-400'}`}>
                  {isMonitoringActive ? 'Активен' : 'Остановлен'}
                </span>
              </div>
            </div>
          </div>
          <div className="flex space-x-3">
            <button 
              onClick={handleCreateTemplate}
              className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
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
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Users className="h-6 w-6 text-green-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-400">Сегодня</p>
                    <p className="text-2xl font-bold text-gray-100">{stats.clientsToday}</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <TrendingUp className="h-6 w-6 text-blue-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-400">За неделю</p>
                    <p className="text-2xl font-bold text-gray-100">{stats.clientsWeek}</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <Target className="h-6 w-6 text-purple-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-400">Всего</p>
                    <p className="text-2xl font-bold text-gray-100">{stats.totalClients}</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-yellow-100 rounded-lg">
                    <Star className="h-6 w-6 text-yellow-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-400">Конверсия</p>
                    <p className="text-2xl font-bold text-gray-100">{stats.conversionRate}%</p>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="col-span-4">
              <ErrorMessage message="Нет данных статистики" />
            </div>
          )}
        </div>

        {/* Основной контент */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Последние клиенты */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 border border-gray-700 rounded-lg">
              <div className="px-6 py-4 border-b border-gray-700">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-100">Последние клиенты</h3>
                  <div className="flex items-center space-x-2 text-sm text-gray-400">
                    <Clock className="h-4 w-4" />
                    <span>Обновлено только что</span>
                  </div>
                </div>
              </div>
              
              {clientsLoading ? (
                <LoadingSpinner />
              ) : clientsError ? (
                <ErrorMessage message="Ошибка загрузки клиентов" />
              ) : clients.length === 0 ? (
                <div className="text-center text-gray-400 py-8">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Клиенты пока не найдены</p>
                  <p className="text-sm mt-1">Настройте мониторинг и добавьте шаблоны</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-700">
                  {clients.map((client) => (
                    <div key={client.id} className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <h4 className="font-medium text-gray-100">
                              {client.first_name} {client.last_name}
                              {client.username && (
                                <span className="text-green-400 ml-2">@{client.username}</span>
                              )}
                            </h4>
                          </div>
                          
                          <p className="text-gray-300 text-sm mb-2">
                            "{client.message_text}"
                          </p>
                          
                          <div className="flex items-center space-x-4 text-xs text-gray-400">
                            <span>Шаблон: {getTemplateName(client.matched_template_id)}</span>
                            <span>•</span>
                            <span>Ключевые слова: {Array.isArray(client.matched_keywords) 
                              ? client.matched_keywords.join(', ') 
                              : client.matched_keywords || 'Нет данных'}</span>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-3 ml-4">
                          <div className="flex items-center space-x-2">
                            <select
                              value={client.client_status}
                              onChange={(e) => handleStatusChange(client.id, e.target.value as any)}
                              className="text-xs px-2 py-1 bg-gray-700 border border-gray-600 rounded text-gray-200 focus:outline-none focus:ring-2 focus:ring-green-500"
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
                        <p className="text-sm font-medium text-green-400">#{index + 1}</p>
                        <p className="text-xs text-gray-400">место</p>
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
                <button 
                  onClick={handleCreateTemplate}
                  className="w-full flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
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

      {/* Модальное окно для шаблонов */}
      <ProductTemplateModal
        isOpen={isTemplateModalOpen}
        onClose={handleCloseModal}
        template={editingTemplate}
      />
    </div>
  );
};