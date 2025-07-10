// frontend/src/pages/MonitoringPage.tsx
import React, { useState, useEffect } from 'react';
import { 
  Monitor, 
  Play, 
  Pause, 
  Settings, 
  Clock, 
  MessageSquare, 
  Target,
  Plus,
  X,
  Save,
  Loader2,
  AlertCircle
} from 'lucide-react';

import { 
  useMonitoringSettings,
  useUpdateMonitoringSettings,
  useStartMonitoring,
  useStopMonitoring
} from '../hooks/useClientHunterApi';
import { MonitoringSettingsUpdate } from '../types/api';

export const MonitoringPage: React.FC = () => {
  // API хуки
  const { data: settingsResponse, isLoading: settingsLoading } = useMonitoringSettings();
  const updateSettingsMutation = useUpdateMonitoringSettings();
  const startMonitoringMutation = useStartMonitoring();
  const stopMonitoringMutation = useStopMonitoring();

  // Состояние формы
  const [formData, setFormData] = useState({
    monitored_chats: [] as string[],
    notification_account: '',
    check_interval_minutes: 5,
    lookback_minutes: 60,
    min_ai_confidence: 7
  });
  
  const [newChatUrl, setNewChatUrl] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  const currentSettings = settingsResponse?.data;
  const isMonitoringActive = currentSettings?.is_active || false;

  // Инициализация формы
  useEffect(() => {
    if (currentSettings) {
      setFormData({
        monitored_chats: currentSettings.monitored_chats || [],
        notification_account: currentSettings.notification_account || '',
        check_interval_minutes: currentSettings.check_interval_minutes || 5,
        lookback_minutes: currentSettings.lookback_minutes || 60,
        min_ai_confidence: currentSettings.min_ai_confidence || 7
      });
    }
  }, [currentSettings]);

  // Обработчики
  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
    setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const handleAddChat = () => {
    if (!newChatUrl.trim()) {
      setErrors(prev => ({ ...prev, newChat: 'Введите URL чата' }));
      return;
    }

    if (formData.monitored_chats.includes(newChatUrl.trim())) {
      setErrors(prev => ({ ...prev, newChat: 'Этот чат уже добавлен' }));
      return;
    }

    handleInputChange('monitored_chats', [...formData.monitored_chats, newChatUrl.trim()]);
    setNewChatUrl('');
    setErrors(prev => ({ ...prev, newChat: '' }));
  };

  const handleRemoveChat = (index: number) => {
    const newChats = formData.monitored_chats.filter((_, i) => i !== index);
    handleInputChange('monitored_chats', newChats);
  };

  const handleSaveSettings = async () => {
    try {
      const updateData: MonitoringSettingsUpdate = {
        monitored_chats: formData.monitored_chats,
        notification_account: formData.notification_account,
        check_interval_minutes: formData.check_interval_minutes,
        lookback_minutes: formData.lookback_minutes,
        min_ai_confidence: formData.min_ai_confidence
      };

      await updateSettingsMutation.mutateAsync(updateData);
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  };

  const handleToggleMonitoring = async () => {
    try {
      if (isMonitoringActive) {
        await stopMonitoringMutation.mutateAsync();
      } else {
        await startMonitoringMutation.mutateAsync();
      }
    } catch (error) {
      console.error('Failed to toggle monitoring:', error);
    }
  };

  if (settingsLoading) {
    return (
      <div className="p-6 bg-gray-900 min-h-screen">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900 min-h-screen">
      <div className="max-w-4xl mx-auto">
        {/* Заголовок */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Настройки мониторинга</h1>
            <p className="text-gray-400 mt-1">
              Настройте параметры автоматического поиска клиентов в Telegram
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Статус мониторинга */}
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${isMonitoringActive ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              <span className={`text-sm font-medium ${isMonitoringActive ? 'text-green-400' : 'text-red-400'}`}>
                {isMonitoringActive ? 'Активен' : 'Остановлен'}
              </span>
            </div>

            {/* Кнопка запуска/остановки */}
            <button
              onClick={handleToggleMonitoring}
              disabled={startMonitoringMutation.isPending || stopMonitoringMutation.isPending}
              className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${
                isMonitoringActive
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              {startMonitoringMutation.isPending || stopMonitoringMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : isMonitoringActive ? (
                <Pause className="h-4 w-4 mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {isMonitoringActive ? 'Остановить' : 'Запустить'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Основные настройки */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Мониторинг чатов */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                <MessageSquare className="h-5 w-5 mr-2 text-green-500" />
                Telegram чаты для мониторинга
              </h3>

              {/* Добавление нового чата */}
              <div className="mb-4">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={newChatUrl}
                    onChange={(e) => setNewChatUrl(e.target.value)}
                    placeholder="@канал или ссылка на чат"
                    className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    onKeyPress={(e) => e.key === 'Enter' && handleAddChat()}
                  />
                  <button
                    onClick={handleAddChat}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
                {errors.newChat && (
                  <p className="text-red-400 text-sm mt-1">{errors.newChat}</p>
                )}
              </div>

              {/* Список чатов */}
              <div className="space-y-2">
                {formData.monitored_chats.length === 0 ? (
                  <div className="text-center py-4 text-gray-400">
                    <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>Нет добавленных чатов</p>
                    <p className="text-sm">Добавьте Telegram каналы или группы для мониторинга</p>
                  </div>
                ) : (
                  formData.monitored_chats.map((chat, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-700 p-3 rounded-md">
                      <span className="text-gray-200">{chat}</span>
                      <button
                        onClick={() => handleRemoveChat(index)}
                        className="text-red-400 hover:text-red-300 transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Параметры мониторинга */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                <Settings className="h-5 w-5 mr-2 text-green-500" />
                Параметры поиска
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Интервал проверки */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Интервал проверки (минуты)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={formData.check_interval_minutes}
                    onChange={(e) => handleInputChange('check_interval_minutes', parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-400 mt-1">Как часто проверять новые сообщения</p>
                </div>

                {/* Глубина поиска */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Глубина поиска (минуты)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="1440"
                    value={formData.lookback_minutes}
                    onChange={(e) => handleInputChange('lookback_minutes', parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-400 mt-1">На сколько назад искать сообщения</p>
                </div>

                {/* Порог ИИ */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Минимальная уверенность ИИ
                  </label>
                  <div className="relative">
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={formData.min_ai_confidence}
                      onChange={(e) => handleInputChange('min_ai_confidence', parseInt(e.target.value))}
                      className="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-gray-400 mt-1">
                      <span>1</span>
                      <span className="font-medium text-green-400">{formData.min_ai_confidence}</span>
                      <span>10</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">Минимальная оценка потенциального клиента</p>
                </div>

                {/* Аккаунт для уведомлений */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Telegram для уведомлений
                  </label>
                  <input
                    type="text"
                    value={formData.notification_account}
                    onChange={(e) => handleInputChange('notification_account', e.target.value)}
                    placeholder="@username"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-400 mt-1">Куда отправлять уведомления о новых клиентах</p>
                </div>
              </div>
            </div>

            {/* Кнопка сохранения */}
            {hasChanges && (
              <div className="flex justify-end">
                <button
                  onClick={handleSaveSettings}
                  disabled={updateSettingsMutation.isPending}
                  className="flex items-center px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  {updateSettingsMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4 mr-2" />
                  )}
                  Сохранить изменения
                </button>
              </div>
            )}
          </div>

          {/* Боковая панель с информацией */}
          <div className="space-y-6">
            
            {/* Статистика */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                <Target className="h-5 w-5 mr-2 text-green-500" />
                Статистика
              </h3>
              
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Чатов в мониторинге:</span>
                  <span className="text-gray-100 font-medium">{formData.monitored_chats.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Интервал проверки:</span>
                  <span className="text-gray-100 font-medium">{formData.check_interval_minutes} мин</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Порог ИИ:</span>
                  <span className="text-gray-100 font-medium">{formData.min_ai_confidence}/10</span>
                </div>
              </div>
            </div>

            {/* Справка */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                <AlertCircle className="h-5 w-5 mr-2 text-blue-500" />
                Как это работает
              </h3>
              
              <div className="space-y-3 text-sm text-gray-400">
                <div className="flex items-start space-x-2">
                  <div className="w-6 h-6 bg-green-600 rounded-full flex items-center justify-center text-white text-xs font-bold mt-0.5">1</div>
                  <p>Система каждые {formData.check_interval_minutes} минут сканирует указанные чаты</p>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-6 h-6 bg-green-600 rounded-full flex items-center justify-center text-white text-xs font-bold mt-0.5">2</div>
                  <p>При нахождении ключевых слов ИИ анализирует намерения пользователя</p>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-6 h-6 bg-green-600 rounded-full flex items-center justify-center text-white text-xs font-bold mt-0.5">3</div>
                  <p>Если уверенность ≥ {formData.min_ai_confidence}, клиент добавляется в базу</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};