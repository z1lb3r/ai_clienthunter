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
  AlertCircle,
  User,
  Users
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
    notification_account: [] as string[],
    check_interval_minutes: 5,
    lookback_minutes: 60,
    min_ai_confidence: 7
  });
  
  const [newChatUrl, setNewChatUrl] = useState('');
  const [newNotificationUser, setNewNotificationUser] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  const currentSettings = settingsResponse?.data;
  const isMonitoringActive = currentSettings?.is_active || false;

  // Инициализация формы
  useEffect(() => {
    if (currentSettings) {
      setFormData({
        monitored_chats: currentSettings.monitored_chats || [],
        notification_account: currentSettings.notification_account || [],
        check_interval_minutes: currentSettings.check_interval_minutes || 5,
        lookback_minutes: currentSettings.lookback_minutes || 60,
        min_ai_confidence: currentSettings.min_ai_confidence || 7
      });
    }
  }, [currentSettings]);

  // Функции для управления чатами
  const validateChatUrl = (url: string): boolean => {
    const telegramUrlPattern = /^(https?:\/\/)?(t\.me\/|telegram\.me\/)([a-zA-Z0-9_]+)\/?$/;
    const usernamePattern = /^@?[a-zA-Z0-9_]+$/;
    return telegramUrlPattern.test(url) || usernamePattern.test(url);
  };

  const addChat = () => {
    const trimmedUrl = newChatUrl.trim();
    if (!trimmedUrl) return;
    
    if (!validateChatUrl(trimmedUrl)) {
      setErrors(prev => ({ 
        ...prev, 
        chat_url: 'Неверный формат ссылки. Используйте https://t.me/username или @username' 
      }));
      return;
    }
    
    if (formData.monitored_chats.includes(trimmedUrl)) {
      setErrors(prev => ({ 
        ...prev, 
        chat_url: 'Этот чат уже добавлен' 
      }));
      return;
    }
    
    setFormData(prev => ({
      ...prev,
      monitored_chats: [...prev.monitored_chats, trimmedUrl]
    }));
    setNewChatUrl('');
    setHasChanges(true);
    
    // Убираем ошибку
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors.chat_url;
      return newErrors;
    });
  };

  const removeChat = (chatUrl: string) => {
    setFormData(prev => ({
      ...prev,
      monitored_chats: prev.monitored_chats.filter(chat => chat !== chatUrl)
    }));
    setHasChanges(true);
  };

  // Функции для управления пользователями уведомлений
  const addNotificationUser = () => {
    const trimmedUser = newNotificationUser.trim();
    if (!trimmedUser) return;
    
    // Проверяем формат username
    let cleanUsername = trimmedUser;
    if (!cleanUsername.startsWith('@')) {
      cleanUsername = '@' + cleanUsername;
    }
    
    // Валидация
    const usernamePattern = /^@[a-zA-Z0-9_]+$/;
    if (!usernamePattern.test(cleanUsername)) {
      setErrors(prev => ({
        ...prev,
        notification_user: 'Неверный формат username. Используйте только буквы, цифры и _'
      }));
      return;
    }
    
    // Проверяем дубликаты
    if (formData.notification_account.includes(cleanUsername)) {
      setErrors(prev => ({
        ...prev,
        notification_user: 'Этот пользователь уже добавлен'
      }));
      return;
    }
    
    setFormData(prev => ({
      ...prev,
      notification_account: [...prev.notification_account, cleanUsername]
    }));
    setNewNotificationUser('');
    setHasChanges(true);
    
    // Убираем ошибку
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors.notification_user;
      return newErrors;
    });
  };

  const removeNotificationUser = (username: string) => {
    setFormData(prev => ({
      ...prev,
      notification_account: prev.notification_account.filter(user => user !== username)
    }));
    setHasChanges(true);
  };

  // Обработчики изменения полей
  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
  };

  // Обработчики для кнопок мониторинга
  const handleStartMonitoring = async () => {
    try {
      await startMonitoringMutation.mutateAsync();
    } catch (error) {
      console.error('Error starting monitoring:', error);
    }
  };

  const handleStopMonitoring = async () => {
    try {
      await stopMonitoringMutation.mutateAsync();
    } catch (error) {
      console.error('Error stopping monitoring:', error);
    }
  };

  // Сохранение настроек
  const handleSaveSettings = async () => {
    try {
      const updateData: MonitoringSettingsUpdate = {};
      
      // Только измененные поля
      if (currentSettings?.notification_account !== formData.notification_account) {
        updateData.notification_account = formData.notification_account;
      }
      
      await updateSettingsMutation.mutateAsync(updateData);
      setHasChanges(false);
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };

  if (settingsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-green-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Заголовок страницы */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Monitor className="w-8 h-8 text-green-500" />
          <div>
            <h1 className="text-2xl font-bold text-white">Мониторинг клиентов</h1>
            <p className="text-gray-400">Управление настройками поиска потенциальных клиентов</p>
          </div>
        </div>
        
        {/* Кнопка включения/выключения мониторинга */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">Мониторинг</span>
            <div className={`w-3 h-3 rounded-full ${isMonitoringActive ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className={`text-sm font-medium ${isMonitoringActive ? 'text-green-400' : 'text-red-400'}`}>
              {isMonitoringActive ? 'Активен' : 'Остановлен'}
            </span>
          </div>
          
          {isMonitoringActive ? (
            <button
              onClick={handleStopMonitoring}
              disabled={stopMonitoringMutation.isPending}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              <Pause className="w-4 h-4" />
              <span>Остановить</span>
            </button>
          ) : (
            <button
              onClick={handleStartMonitoring}
              disabled={startMonitoringMutation.isPending}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              <span>Запустить</span>
            </button>
          )}
        </div>
      </div>

      {/* Основные настройки */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center space-x-3 mb-6">
          <Settings className="w-6 h-6 text-green-500" />
          <h2 className="text-xl font-semibold text-white">Настройки уведомлений</h2>
        </div>

        <div className="space-y-6">
          {/* Пользователи для уведомлений */}
          <div>
            <label className="flex items-center space-x-2 text-sm font-medium text-gray-300 mb-3">
              <Users className="w-4 h-4" />
              <span>Пользователи для уведомлений</span>
            </label>
            
            {/* Список текущих пользователей */}
            {formData.notification_account.length > 0 && (
              <div className="mb-4 space-y-2">
                {formData.notification_account.map((username, index) => (
                  <div key={index} className="flex items-center justify-between bg-gray-700 rounded-lg p-3">
                    <div className="flex items-center space-x-2">
                      <User className="w-4 h-4 text-green-500" />
                      <span className="text-white font-mono">{username}</span>
                    </div>
                    <button
                      onClick={() => removeNotificationUser(username)}
                      className="text-red-400 hover:text-red-300 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            {/* Добавление нового пользователя */}
            <div className="flex space-x-2">
              <div className="flex-1">
                <input
                  type="text"
                  value={newNotificationUser}
                  onChange={(e) => setNewNotificationUser(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addNotificationUser()}
                  placeholder="@username или username"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                />
                {errors.notification_user && (
                  <p className="mt-1 text-sm text-red-400 flex items-center space-x-1">
                    <AlertCircle className="w-4 h-4" />
                    <span>{errors.notification_user}</span>
                  </p>
                )}
              </div>
              <button
                onClick={addNotificationUser}
                disabled={!newNotificationUser.trim()}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Добавить</span>
              </button>
            </div>
            
            {formData.notification_account.length === 0 && (
              <p className="text-gray-500 text-sm mt-2">
                Добавьте пользователей для получения уведомлений о найденных клиентах
              </p>
            )}
          </div>
        </div>

        {/* Кнопка сохранения */}
        {hasChanges && (
          <div className="mt-6 pt-4 border-t border-gray-700">
            <button
              onClick={handleSaveSettings}
              disabled={updateSettingsMutation.isPending}
              className="flex items-center space-x-2 px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
            >
              {updateSettingsMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              <span>Сохранить изменения</span>
            </button>
          </div>
        )}
      </div>

      {/* Статистика мониторинга */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <Clock className="w-6 h-6 text-blue-500" />
            <div>
              <h3 className="text-lg font-semibold text-white">Последняя проверка</h3>
              <p className="text-gray-400">
                {currentSettings?.last_monitoring_check 
                  ? new Date(currentSettings.last_monitoring_check).toLocaleString('ru-RU')
                  : 'Не выполнялась'
                }
              </p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <MessageSquare className="w-6 h-6 text-purple-500" />
            <div>
              <h3 className="text-lg font-semibold text-white">Отслеживаемые чаты</h3>
              <p className="text-gray-400">{formData.monitored_chats.length} чатов</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <Target className="w-6 h-6 text-green-500" />
            <div>
              <h3 className="text-lg font-semibold text-white">Получатели уведомлений</h3>
              <p className="text-gray-400">{formData.notification_account.length} пользователей</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};