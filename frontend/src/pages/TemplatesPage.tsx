// frontend/src/pages/TemplatesPage.tsx
import React, { useState } from 'react';
import { 
  Target, 
  Plus, 
  Edit2, 
  Trash2, 
  Users, 
  TrendingUp,
  ToggleLeft,
  ToggleRight,
  Loader2,
  AlertCircle
} from 'lucide-react';

import { 
  useProductTemplates,
  useUpdateProductTemplate,
  useDeleteProductTemplate,
  usePotentialClients
} from '../hooks/useClientHunterApi';
import { ProductTemplate } from '../types/api';
import { ProductTemplateModal } from '../components/ProductTemplates/ProductTemplateModal';

export const TemplatesPage: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ProductTemplate | undefined>();

  // API хуки
  const { data: templatesResponse, isLoading: templatesLoading } = useProductTemplates();
  const { data: clientsResponse } = usePotentialClients({});
  const updateTemplateMutation = useUpdateProductTemplate();
  const deleteTemplateMutation = useDeleteProductTemplate();

  const templates = templatesResponse?.data || [];
  const clients = clientsResponse?.data || [];

  // Статистика по шаблонам
  const getTemplateStats = (templateId: number) => {
    const templateClients = clients.filter(client => client.matched_template_id === templateId);
    const conversions = templateClients.filter(client => client.client_status === 'converted').length;
    const avgConfidence = templateClients.length > 0 
      ? templateClients.reduce((sum, client) => sum + client.ai_confidence, 0) / templateClients.length
      : 0;

    return {
      totalClients: templateClients.length,
      conversions,
      conversionRate: templateClients.length > 0 ? Math.round((conversions / templateClients.length) * 100) : 0,
      avgConfidence: Math.round(avgConfidence * 100)
    };
  };

  // Обработчики
  const handleCreateTemplate = () => {
    setEditingTemplate(undefined);
    setIsModalOpen(true);
  };

  const handleEditTemplate = (template: ProductTemplate) => {
    setEditingTemplate(template);
    setIsModalOpen(true);
  };

  const handleToggleActive = async (template: ProductTemplate) => {
    try {
      await updateTemplateMutation.mutateAsync({
        id: template.id,
        template: { is_active: !template.is_active }
      });
    } catch (error) {
      console.error('Failed to toggle template:', error);
    }
  };

  const handleDeleteTemplate = async (templateId: number) => {
    if (window.confirm('Вы уверены, что хотите удалить этот шаблон?')) {
      try {
        await deleteTemplateMutation.mutateAsync(templateId);
      } catch (error) {
        console.error('Failed to delete template:', error);
      }
    }
  };

  if (templatesLoading) {
    return (
      <div className="p-6 bg-gray-900 min-h-screen">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Заголовок */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Шаблоны продуктов</h1>
            <p className="text-gray-400 mt-1">Управление ключевыми словами для поиска клиентов</p>
          </div>
          <button 
            onClick={handleCreateTemplate}
            className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Plus className="h-4 w-4 mr-2" />
            Создать шаблон
          </button>
        </div>

        {/* Статистика */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center">
              <Target className="h-8 w-8 text-green-500 mr-3" />
              <div>
                <p className="text-sm text-gray-400">Всего шаблонов</p>
                <p className="text-2xl font-bold text-gray-100">{templates.length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center">
              <ToggleRight className="h-8 w-8 text-blue-500 mr-3" />
              <div>
                <p className="text-sm text-gray-400">Активных</p>
                <p className="text-2xl font-bold text-gray-100">
                  {templates.filter(t => t.is_active).length}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-purple-500 mr-3" />
              <div>
                <p className="text-sm text-gray-400">Найдено клиентов</p>
                <p className="text-2xl font-bold text-gray-100">{clients.length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Список шаблонов */}
        {templates.length === 0 ? (
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
            <Target className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-100 mb-2">Нет шаблонов</h3>
            <p className="text-gray-400 mb-6">Создайте первый шаблон для поиска клиентов</p>
            <button 
              onClick={handleCreateTemplate}
              className="flex items-center mx-auto px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Plus className="h-4 w-4 mr-2" />
              Создать первый шаблон
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {templates.map((template) => {
              const stats = getTemplateStats(template.id);
              
              return (
                <div key={template.id} className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                  <div className="flex items-start justify-between">
                    {/* Основная информация */}
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-3">
                        <h3 className="text-lg font-semibold text-gray-100">{template.name}</h3>
                        
                        {/* Статус активности */}
                        <button
                          onClick={() => handleToggleActive(template)}
                          className={`flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            template.is_active 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {template.is_active ? (
                            <>
                              <ToggleRight className="h-3 w-3 mr-1" />
                              Активен
                            </>
                          ) : (
                            <>
                              <ToggleLeft className="h-3 w-3 mr-1" />
                              Неактивен
                            </>
                          )}
                        </button>
                      </div>

                      {/* Ключевые слова */}
                      <div className="mb-4">
                        <p className="text-sm text-gray-400 mb-2">Ключевые слова:</p>
                        <div className="flex flex-wrap gap-2">
                          {template.keywords.map((keyword, index) => (
                            <span
                              key={index}
                              className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                            >
                              {keyword}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Статистика */}
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-400">Клиентов</p>
                          <p className="font-semibold text-gray-100">{stats.totalClients}</p>
                        </div>
                        <div>
                          <p className="text-gray-400">Конверсий</p>
                          <p className="font-semibold text-gray-100">{stats.conversions}</p>
                        </div>
                        <div>
                          <p className="text-gray-400">Конверсия %</p>
                          <p className="font-semibold text-gray-100">{stats.conversionRate}%</p>
                        </div>
                        <div>
                          <p className="text-gray-400">Ср. уверенность</p>
                          <p className="font-semibold text-gray-100">{stats.avgConfidence}%</p>
                        </div>
                      </div>
                    </div>

                    {/* Действия */}
                    <div className="flex items-center space-x-2 ml-4">
                      <button
                        onClick={() => handleEditTemplate(template)}
                        className="p-2 text-gray-400 hover:text-blue-400 hover:bg-gray-700 rounded-lg transition-colors"
                        title="Редактировать"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteTemplate(template.id)}
                        className="p-2 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded-lg transition-colors"
                        title="Удалить"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Модальное окно */}
      <ProductTemplateModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        template={editingTemplate}
      />
    </div>
  );
};