// frontend/src/components/ProductTemplates/ProductTemplateModal.tsx
import React, { useState, useEffect } from 'react';
import { Plus, X, Tag, Loader2, MessageSquare, Clock, Target, Brain } from 'lucide-react';
import { Modal } from '../Common/Modal';
import { 
  useCreateProductTemplate, 
  useUpdateProductTemplate 
} from '../../hooks/useClientHunterApi';
import { ProductTemplate } from '../../types/api';

interface ProductTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  template?: ProductTemplate;
}

export const ProductTemplateModal: React.FC<ProductTemplateModalProps> = ({
  isOpen,
  onClose,
  template
}) => {
  const [formData, setFormData] = useState({
    name: '',
    keywords: [] as string[],
    monitored_chats: [] as string[],
    check_interval_minutes: 5,
    lookback_minutes: 60,
    min_ai_confidence: 7,
    ai_prompt: ''
  });
  const [currentKeyword, setCurrentKeyword] = useState('');
  const [currentChat, setCurrentChat] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const createMutation = useCreateProductTemplate();
  const updateMutation = useUpdateProductTemplate();

  const isEditing = !!template;
  const isLoading = createMutation.isPending || updateMutation.isPending;

  // Дефолтный промпт для новых шаблонов
  const defaultPrompt = `Ты - эксперт по анализу сообщений о валютном обмене.
Твоя задача - найти КЛИЕНТОВ, которые хотят ОБМЕНЯТЬ валюту, а НЕ поставщиков услуг.

ВАЖНО: Мы ищем людей, которые ХОТЯТ обменять свои деньги, а не тех, кто ПРЕДЛАГАЕТ услуги обмена.

КРИТЕРИИ ОЦЕНКИ УВЕРЕННОСТИ (1-10):
- 9-10: Срочная потребность в обмене ("Срочно нужно обменять 1000$ на баты", "Завтра лечу, где поменять?")
- 7-8: Активный поиск обмена ("Хочу поменять USDT на баты", "Нужно обменять доллары")  
- 5-6: Интерес к обмену ("Думаю обменять тезер", "Где лучше менять валюту?")
- 3-4: Информационный интерес ("Какой курс бата?", "Сколько стоит обмен?")
- 1-2: Поставщик услуг ("Меняю доллары на баты", "Обмен валют, выгодные курсы", "Предлагаю обмен")

ТИПЫ НАМЕРЕНИЙ:
- "обмен_клиент" - хочет обменять свою валюту
- "обмен_поставщик" - предлагает услуги обмена (НЕ НАША ЦЕЛЕВАЯ АУДИТОРИЯ)
- "информация" - интересуется курсами, условиями
- "другое" - не связано с обменом валют

Приоритет отдавай ключевым словам из шаблона - они указывают на то, что именно клиент хочет обменять.`;

  // Заполнение формы при редактировании
  useEffect(() => {
    if (isOpen) {
      if (template) {
        setFormData({
          name: template.name,
          keywords: [...template.keywords],
          monitored_chats: [...(template.monitored_chats || [])],
          check_interval_minutes: template.check_interval_minutes || 5,
          lookback_minutes: template.lookback_minutes || 60,
          min_ai_confidence: template.min_ai_confidence || 7,
          ai_prompt: template.ai_prompt || defaultPrompt
        });
      } else {
        setFormData({
          name: '',
          keywords: [],
          monitored_chats: [],
          check_interval_minutes: 5,
          lookback_minutes: 60,
          min_ai_confidence: 7,
          ai_prompt: defaultPrompt
        });
      }
      setCurrentKeyword('');
      setCurrentChat('');
      setErrors({});
    }
  }, [isOpen, template]);

  // Валидация
  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Название обязательно';
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Название должно содержать минимум 2 символа';
    }

    if (formData.keywords.length === 0) {
      newErrors.keywords = 'Добавьте хотя бы одно ключевое слово';
    }

    if (!formData.ai_prompt.trim()) {
      newErrors.ai_prompt = 'AI промпт обязателен';
    } else if (formData.ai_prompt.trim().length < 50) {
      newErrors.ai_prompt = 'AI промпт должен содержать минимум 50 символов';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Добавление ключевого слова
  const addKeyword = () => {
    if (currentKeyword.trim() && !formData.keywords.includes(currentKeyword.trim())) {
      setFormData(prev => ({
        ...prev,
        keywords: [...prev.keywords, currentKeyword.trim()]
      }));
      setCurrentKeyword('');
      if (errors.keywords) {
        setErrors(prev => ({ ...prev, keywords: '' }));
      }
    }
  };

  const removeKeyword = (index: number) => {
    setFormData(prev => ({
      ...prev,
      keywords: prev.keywords.filter((_, i) => i !== index)
    }));
  };

  const handleKeywordKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addKeyword();
    }
  };

  // Добавление чата
  const addChat = () => {
    if (currentChat.trim() && !formData.monitored_chats.includes(currentChat.trim())) {
      setFormData(prev => ({
        ...prev,
        monitored_chats: [...prev.monitored_chats, currentChat.trim()]
      }));
      setCurrentChat('');
    }
  };

  const removeChat = (index: number) => {
    setFormData(prev => ({
      ...prev,
      monitored_chats: prev.monitored_chats.filter((_, i) => i !== index)
    }));
  };

  const handleChatKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addChat();
    }
  };

  // Отправка формы
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      if (isEditing && template) {
        await updateMutation.mutateAsync({
          id: template.id,
          template: formData
        });
      } else {
        await createMutation.mutateAsync(formData);
      }
      onClose();
    } catch (error) {
      console.error('Failed to save template:', error);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Редактировать шаблон' : 'Создать новый шаблон'}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="p-6">
        {/* Название шаблона */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Название шаблона
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => {
              setFormData(prev => ({ ...prev, name: e.target.value }));
              if (errors.name) {
                setErrors(prev => ({ ...prev, name: '' }));
              }
            }}
            className={`w-full px-3 py-2 bg-gray-700 border rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent ${
              errors.name ? 'border-red-500' : 'border-gray-600'
            }`}
            placeholder="Например: Обмен валют"
            disabled={isLoading}
          />
          {errors.name && (
            <p className="mt-1 text-sm text-red-400">{errors.name}</p>
          )}
        </div>

        {/* Ключевые слова */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Ключевые слова
          </label>
          
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={currentKeyword}
              onChange={(e) => setCurrentKeyword(e.target.value)}
              onKeyPress={handleKeywordKeyPress}
              className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              placeholder="Введите ключевое слово"
              disabled={isLoading}
            />
            <button
              type="button"
              onClick={addKeyword}
              disabled={!currentKeyword.trim() || isLoading}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors flex items-center"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>

          {formData.keywords.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {formData.keywords.map((keyword, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full"
                >
                  <Tag className="h-3 w-3 mr-1" />
                  {keyword}
                  <button
                    type="button"
                    onClick={() => removeKeyword(index)}
                    disabled={isLoading}
                    className="ml-2 text-green-600 hover:text-green-800 disabled:text-gray-400"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {errors.keywords && (
            <p className="mt-1 text-sm text-red-400">{errors.keywords}</p>
          )}
        </div>

        {/* AI Промпт */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <Brain className="h-4 w-4 inline mr-1" />
            AI Промпт для анализа
          </label>
          <textarea
            value={formData.ai_prompt}
            onChange={(e) => {
              setFormData(prev => ({ ...prev, ai_prompt: e.target.value }));
              if (errors.ai_prompt) {
                setErrors(prev => ({ ...prev, ai_prompt: '' }));
              }
            }}
            rows={8}
            className={`w-full px-3 py-2 bg-gray-700 border rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-vertical ${
              errors.ai_prompt ? 'border-red-500' : 'border-gray-600'
            }`}
            placeholder="Введите инструкции для ИИ анализа..."
            disabled={isLoading}
          />
          {errors.ai_prompt && (
            <p className="mt-1 text-sm text-red-400">{errors.ai_prompt}</p>
          )}
          <p className="mt-1 text-xs text-gray-400">
            Этот промпт будет использоваться ИИ для анализа сообщений и определения потенциальных клиентов
          </p>
        </div>

        {/* Telegram чаты */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Telegram чаты для мониторинга
          </label>
          
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={currentChat}
              onChange={(e) => setCurrentChat(e.target.value)}
              onKeyPress={handleChatKeyPress}
              className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              placeholder="@канал или ссылка на чат"
              disabled={isLoading}
            />
            <button
              type="button"
              onClick={addChat}
              disabled={!currentChat.trim() || isLoading}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors flex items-center"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>

          {formData.monitored_chats.length > 0 && (
            <div className="space-y-2 mb-3">
              {formData.monitored_chats.map((chat, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between px-3 py-2 bg-gray-600 rounded-lg"
                >
                  <span className="text-sm text-gray-200">{chat}</span>
                  <button
                    type="button"
                    onClick={() => removeChat(index)}
                    disabled={isLoading}
                    className="text-gray-400 hover:text-red-400 disabled:text-gray-500"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Параметры поиска */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-3">
            Параметры поиска
          </label>
          
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Интервал проверки (мин)
              </label>
              <input
                type="number"
                min="1"
                max="1440"
                value={formData.check_interval_minutes}
                onChange={(e) => setFormData(prev => ({ ...prev, check_interval_minutes: parseInt(e.target.value) || 5 }))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Глубина поиска (мин)
              </label>
              <input
                type="number"
                min="1"
                max="10080"
                value={formData.lookback_minutes}
                onChange={(e) => setFormData(prev => ({ ...prev, lookback_minutes: parseInt(e.target.value) || 60 }))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Порог ИИ (1-10)
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={formData.min_ai_confidence}
                onChange={(e) => setFormData(prev => ({ ...prev, min_ai_confidence: parseInt(e.target.value) || 7 }))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>
          </div>
        </div>

        {/* Кнопки */}
        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="px-6 py-2 text-gray-300 bg-gray-600 rounded-lg hover:bg-gray-500 disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors flex items-center"
          >
            {isLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {isEditing ? 'Обновить' : 'Создать'}
          </button>
        </div>
      </form>
    </Modal>
  );
};