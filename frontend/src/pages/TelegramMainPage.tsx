// frontend/src/pages/TelegramMainPage.tsx - ОЧИЩЕННАЯ ВЕРСИЯ

import React from 'react';
import { Link } from 'react-router-dom';
import { Users, Settings, BarChart3 } from 'lucide-react';

export const TelegramMainPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Анализ Telegram
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Инструменты для анализа работы модераторов и управления Telegram группами
          </p>
        </div>

        {/* Основные функции */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          {/* Анализ модераторов */}
          <Link
            to="/telegram/analyze/moderators"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow duration-300 border border-gray-200 hover:border-indigo-300"
          >
            <div className="flex items-center justify-center w-16 h-16 bg-indigo-100 rounded-lg mb-6 mx-auto">
              <Users className="h-8 w-8 text-indigo-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 text-center mb-4">
              Анализ Модераторов
            </h3>
            <p className="text-gray-600 text-center mb-6">
              Оценка эффективности работы модераторов: время ответа, качество общения, решение проблем
            </p>
            <div className="text-center">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                Требует выбор группы
              </span>
            </div>
          </Link>

          {/* Управление группами */}
          <Link
            to="/telegram/groups"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow duration-300 border border-gray-200 hover:border-green-300"
          >
            <div className="flex items-center justify-center w-16 h-16 bg-green-100 rounded-lg mb-6 mx-auto">
              <Settings className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 text-center mb-4">
              Управление Группами
            </h3>
            <p className="text-gray-600 text-center mb-6">
              Просмотр групп, настройка параметров мониторинга и управление подключенными каналами
            </p>
            <div className="text-center">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Всегда доступно
              </span>
            </div>
          </Link>
        </div>

        {/* Информационный блок */}
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mb-4 mx-auto">
              <BarChart3 className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-3">
              Аналитика Telegram
            </h3>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Получайте детальную аналитику по работе с Telegram группами и эффективности модерации
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm text-gray-700">
            <div className="text-center">
              <div className="bg-indigo-50 rounded-lg p-4 mb-3">
                <Users className="h-8 w-8 text-indigo-600 mx-auto mb-2" />
                <div className="font-medium text-indigo-900">Модераторы</div>
              </div>
              <p>Анализ времени ответа, качества обратной связи и решения проблем пользователей</p>
            </div>
            
            <div className="text-center">
              <div className="bg-green-50 rounded-lg p-4 mb-3">
                <Settings className="h-8 w-8 text-green-600 mx-auto mb-2" />
                <div className="font-medium text-green-900">Управление</div>
              </div>
              <p>Централизованное управление группами, настройка параметров и мониторинг активности</p>
            </div>
            
            <div className="text-center">
              <div className="bg-blue-50 rounded-lg p-4 mb-3">
                <BarChart3 className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                <div className="font-medium text-blue-900">Аналитика</div>
              </div>
              <p>Детальные отчеты и метрики по работе с сообществом и эффективности коммуникации</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};