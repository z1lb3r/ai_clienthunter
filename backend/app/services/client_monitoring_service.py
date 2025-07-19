# backend/app/services/client_monitoring_service.py
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import re
import json

from ..core.database import supabase_client
from ..core.config import settings
from .telegram_service import TelegramService
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)

class ClientMonitoringService:
    def __init__(self):
        self.telegram_service = TelegramService()
        self.openai_service = OpenAIService()
        self.active_monitoring = {}  # Словарь активных мониторингов по user_id
        
    async def start_monitoring(self, user_id: int):
        """Запустить мониторинг для пользователя"""
        try:
            logger.info(f"Starting monitoring for user {user_id}")
            self.active_monitoring[user_id] = True
            asyncio.create_task(self._monitoring_loop(user_id))
        except Exception as e:
            logger.error(f"Error starting monitoring for user {user_id}: {e}")
            raise
    
    async def stop_monitoring(self, user_id: int):
        """Остановить мониторинг для пользователя"""
        try:
            logger.info(f"Stopping monitoring for user {user_id}")
            self.active_monitoring[user_id] = False
        except Exception as e:
            logger.error(f"Error stopping monitoring for user {user_id}: {e}")
            raise
    
    async def _monitoring_loop(self, user_id: int):
        """Основной цикл мониторинга для пользователя"""
        while self.active_monitoring.get(user_id, False):
            try:
                settings_data = await self._get_user_settings(user_id)
                
                if not settings_data or not settings_data.get('is_active', False):
                    await asyncio.sleep(60)
                    continue
                
                await self._search_and_analyze(user_id, settings_data)
                
                interval = settings_data.get('check_interval_minutes', 5) * 60
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop for user {user_id}: {e}")
                await asyncio.sleep(60)
    
    async def _get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить настройки пользователя"""
        try:
            result = supabase_client.table('monitoring_settings').select('*').eq('user_id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return None
    
    async def search_and_analyze(self, user_id: int, settings: Dict[str, Any]):
        """Основной метод поиска и анализа клиентов с подробным логированием"""
        logger.info(f"🔥 ВХОД В search_and_analyze для пользователя {user_id}")
        try:
            logger.info(f"🚀 ЗАПУСК МОНИТОРИНГА для пользователя {user_id}")
            
            # Получаем шаблоны
            templates = await self._get_user_templates(user_id)
            if not templates:
                logger.info(f"❌ Нет активных шаблонов для пользователя {user_id}")
                return
            
            logger.info(f"📋 Найдено {len(templates)} активных шаблонов")
            
            # Статистика по всему циклу
            total_messages_found = 0
            total_keyword_matches = 0
            total_ai_analyzed = 0
            total_clients_found = 0
            
            # Обрабатываем каждый шаблон
            for template_idx, template in enumerate(templates, 1):
                template_name = template.get('name', 'Unknown')
                template_id = template.get('id', 'Unknown')
                
                logger.info(f"📊 ШАБЛОН {template_idx}/{len(templates)}: '{template_name}' (ID: {template_id})")
                
                # Парсим keywords
                keywords = self._parse_keywords(template.get('keywords'))
                if not keywords:
                    logger.warning(f"⚠️ Нет ключевых слов в шаблоне '{template_name}' - пропускаем")
                    continue
                    
                logger.info(f"🔑 Ключевые слова: {keywords}")
                
                # Получаем чаты для этого шаблона
                monitored_chats = template.get('chat_ids', [])
                if not monitored_chats:
                    logger.warning(f"⚠️ Нет чатов для мониторинга в шаблоне '{template_name}' - пропускаем")
                    continue
                    
                logger.info(f"💬 Мониторим {len(monitored_chats)} чатов: {monitored_chats}")
                
                # Статистика по шаблону
                template_messages = 0
                template_keyword_matches = 0
                template_ai_analyzed = 0
                template_clients_found = 0
                
                # Обрабатываем каждый чат
                for chat_idx, chat_id in enumerate(monitored_chats, 1):
                    try:
                        logger.info(f"  📱 ЧАТ {chat_idx}/{len(monitored_chats)}: {chat_id}")
                        
                        # Получаем сообщения
                        lookback_minutes = template.get('lookback_minutes', 5)
                        messages = await self._get_recent_messages(chat_id, lookback_minutes)
                        
                        if not messages:
                            logger.info(f"    📭 Нет новых сообщений за последние {lookback_minutes} минут")
                            continue
                            
                        template_messages += len(messages)
                        logger.info(f"    📨 Найдено {len(messages)} сообщений за последние {lookback_minutes} минут")
                        
                        # Анализируем каждое сообщение
                        chat_keyword_matches = 0
                        logger.info(f"    🔄 НАЧИНАЕМ обработку {len(messages)} сообщений")
                        logger.info(f"    🔑 Ключевые слова для поиска: {keywords} (количество: {len(keywords)})")

                        for msg_idx, message in enumerate(messages, 1):
                            try:
                                message_text = message.get('text', '')
                                
                                logger.info(f"    📨 СООБЩЕНИЕ {msg_idx}/{len(messages)}:")
                                logger.info(f"        📝 Текст: '{message_text}'")
                                logger.info(f"        📏 Длина: {len(message_text)} символов")
                                
                                # Проверяем условия перед вызовом функции поиска
                                if not message_text:
                                    logger.info(f"        ⚠️ Пустое сообщение - пропускаем")
                                    continue
                                    
                                if not keywords:
                                    logger.info(f"        ⚠️ Нет ключевых слов - пропускаем")
                                    continue
                                    
                                logger.info(f"        🚀 ВЫЗЫВАЕМ _find_keywords_in_message")
                                
                                matched_keywords = self._find_keywords_in_message(message_text, keywords)
                                
                                logger.info(f"        ✅ РЕЗУЛЬТАТ поиска: {matched_keywords}")
                                
                                if matched_keywords:
                                    chat_keyword_matches += 1
                                    template_keyword_matches += 1
                                    
                                    logger.info(f"    🎯 СОВПАДЕНИЕ ключевых слов: {matched_keywords}")
                                    logger.info(f"    💬 Сообщение: '{message_text[:100]}...'")
                                    
                                    # Анализ через ИИ
                                    try:
                                        template_ai_analyzed += 1
                                        await self._analyze_message_with_ai(
                                            user_id, chat_id, 
                                            message.get('chat_title', f'Chat {chat_id}'),
                                            {
                                                'message': message,
                                                'template': template,
                                                'matched_keywords': matched_keywords
                                            },
                                            settings
                                        )
                                        template_clients_found += 1
                                        
                                    except Exception as ai_error:
                                        logger.error(f"    ❌ Ошибка AI анализа: {ai_error}")
                                        
                            except Exception as msg_error:
                                logger.error(f"    ❌ Ошибка обработки сообщения {msg_idx}: {msg_error}")
                                continue
                        
                        if chat_keyword_matches > 0:
                            logger.info(f"    ✅ Чат обработан: {chat_keyword_matches} совпадений ключевых слов")
                        else:
                            logger.info(f"    ⚪ Чат обработан: совпадений не найдено")
                    
                    except Exception as chat_error:
                        logger.error(f"    ❌ Ошибка обработки чата {chat_id}: {chat_error}")
                        continue
                
                # Статистика по шаблону
                logger.info(f"📈 ИТОГ ШАБЛОНА '{template_name}':")
                logger.info(f"   📨 Сообщений проанализировано: {template_messages}")
                logger.info(f"   🎯 Совпадений ключевых слов: {template_keyword_matches}")
                logger.info(f"   🤖 Отправлено в AI: {template_ai_analyzed}")
                logger.info(f"   ✅ Потенциальных клиентов: {template_clients_found}")
                
                # Добавляем к общей статистике
                total_messages_found += template_messages
                total_keyword_matches += template_keyword_matches
                total_ai_analyzed += template_ai_analyzed
                total_clients_found += template_clients_found
            
            # Финальная статистика по всему циклу
            logger.info(f"🏁 ИТОГ МОНИТОРИНГА для пользователя {user_id}:")
            logger.info(f"   📋 Шаблонов обработано: {len(templates)}")
            logger.info(f"   📨 Всего сообщений: {total_messages_found}")
            logger.info(f"   🎯 Совпадений ключевых слов: {total_keyword_matches}")
            logger.info(f"   🤖 Отправлено в AI: {total_ai_analyzed}")
            logger.info(f"   ✅ Найдено клиентов: {total_clients_found}")
            
        except Exception as e:
            logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА в мониторинге пользователя {user_id}: {e}")
            raise
            
    def _parse_keywords(self, keywords_raw) -> List[str]:
        """Парсинг ключевых слов из БД"""
        if isinstance(keywords_raw, list):
            return keywords_raw
        elif isinstance(keywords_raw, str):
            try:
                return json.loads(keywords_raw)
            except Exception:
                logger.warning(f"Failed to parse keywords JSON: {keywords_raw}")
                return []
        else:
            logger.warning(f"Unexpected keywords type: {type(keywords_raw)}")
            return []
    
    async def _get_user_templates(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить активные шаблоны пользователя"""
        try:
            result = supabase_client.table('product_templates').select('*').eq('user_id', user_id).eq('is_active', True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting user templates: {e}")
            return []
    
    async def _get_recent_messages(self, chat_id: str, lookback_minutes: int) -> List[Dict[str, Any]]:
        """Получить сообщения за последние N минут"""
        try:
            logger.debug(f"Getting messages from last {lookback_minutes} minutes from chat {chat_id}")
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
            
            messages = await self.telegram_service.get_group_messages(
                group_id=chat_id,
                limit=100,
                offset_date=cutoff_time
            )
            
            # Фильтруем по времени
            filtered_messages = []
            for msg in messages:
                msg_date = msg.get('date')
                if msg_date and datetime.fromisoformat(msg_date.replace('Z', '+00:00')) >= cutoff_time:
                    filtered_messages.append(msg)
            
            logger.debug(f"Found {len(filtered_messages)} messages after time filtering")
            return filtered_messages
            
        except Exception as e:
            logger.error(f"Error getting messages from chat {chat_id}: {e}")
            return []
    
    def _find_keywords_in_message(self, message_text: str, keywords: List[str]) -> List[str]:
        """Поиск ключевых слов в сообщении"""
        if not message_text or not keywords:
            return []
        
        logger.info(f"🔍 ПОИСК: '{message_text}'")
        logger.info(f"🔑 Ключевые слова: {keywords}")
        
        found_keywords = []
        message_lower = message_text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in message_lower:
                found_keywords.append(keyword)
                logger.info(f"   ✅ '{keyword}' → НАЙДЕНО")
            else:
                logger.info(f"   ❌ '{keyword}' → НЕ НАЙДЕНО")
        
        logger.info(f"🎯 Итого найдено: {found_keywords}")
        return found_keywords
    
    async def _analyze_message_with_ai(
        self, 
        user_id: int, 
        chat_id: str, 
        chat_name: str,
        message_data: Dict[str, Any], 
        settings: Dict[str, Any]
    ):
        """Анализ сообщения через ИИ - упрощенная логика"""
        try:
            message = message_data['message']
            template = message_data['template']
            matched_keywords = message_data['matched_keywords']
            
            # Подготавливаем данные для ИИ
            author_info = {
               'telegram_id': message.get('from_id', 'unknown'),
               'username': message.get('user_info', {}).get('username', ''),       # ✅ ПРАВИЛЬНО
               'first_name': message.get('user_info', {}).get('first_name', ''),   # ✅ ПРАВИЛЬНО
               'last_name': message.get('user_info', {}).get('last_name', '')      # ✅ ПРАВИЛЬНО
            }
            
            chat_info = {
                'chat_id': chat_id,
                'chat_name': chat_name
            }
            
            message_text = message.get('text', '')  # ← ИЗМЕНЕНО: было 'message'
            
            logger.info(f"🤖 AI анализ сообщения от @{author_info.get('username', 'unknown')} в чате {chat_name}")
            
            # Вызываем ИИ анализ (убрали custom_prompt и confidence)
            ai_result = await self.openai_service.analyze_potential_client(
                message_text=message_text,
                product_name=template.get('name', 'Unknown Product'),
                keywords=template.get('keywords', []),
                matched_keywords=matched_keywords,
                author_info=author_info,
                chat_info=chat_info
            )
            
            # Простая проверка: клиент или нет
            if ai_result.get('is_client', False):
                logger.info(f"✅ AI определил как КЛИЕНТА: {ai_result.get('reasoning', '')[:100]}...")
                
                # Сохраняем потенциального клиента
                await self._save_potential_client(
                    user_id=user_id,
                    message=message,
                    template=template,
                    matched_keywords=matched_keywords,
                    ai_result=ai_result,
                    chat_id=chat_id,
                    chat_name=chat_name
                )
                
                # ДОБАВЛЕНО: Отправляем уведомления
                await self._send_notifications(
                    user_id=user_id,
                    message=message,
                    template=template, 
                    ai_result=ai_result,
                    settings=settings
                )
            else:
                logger.info(f"❌ AI определил как НЕ КЛИЕНТА: {ai_result.get('reasoning', '')[:100]}...")
                
        except Exception as e:
            logger.error(f"Ошибка AI анализа: {e}")
            
            # ✅ ИСПРАВЛЕНО: При ошибке сохраняем для ручной проверки
            await self._save_potential_client(
                user_id=user_id,
                message=message_data['message'],
                template=message_data['template'],
                matched_keywords=message_data['matched_keywords'],
                ai_result={'is_client': True, 'reasoning': f'Ошибка AI: {str(e)}'},
                chat_id=chat_id,
                chat_name=chat_name
            )
            
    async def _save_potential_client(
        self, 
        user_id: int, 
        message: Dict[str, Any], 
        template: Dict[str, Any],
        matched_keywords: List[str], 
        ai_result: Dict[str, Any],
        chat_id: str,
        chat_name: str
    ):
        """Сохранение потенциального клиента в БД"""
        try:
            client_data = {
                'user_id': user_id,
                'author_id': str(message.get('from_id', '')),
                'author_username': message.get('user_info', {}).get('username', ''),  
                'message_text': message.get('text', ''),
                'message_id': message.get('id', 0),
                'chat_id': chat_id,
                'chat_name': chat_name,
                'product_template_id': template.get('id'),
                'template_name': template.get('name', ''),
                'matched_keywords': matched_keywords,
                'ai_explanation_text': ai_result.get('reasoning', ''),
                'client_status': 'new',
                'notification_send': False,
                'created_at': datetime.now().isoformat()
            }
            # ✅ Убраны поля: ai_confidence, ai_intent_type, updated_at, first_name, last_name
            
            result = supabase_client.table('potential_clients').insert(client_data).execute()
            
            if result.data:
                logger.info(f"Saved potential client: {client_data.get('author_username', 'unknown')}")  
            else:
                logger.error("Failed to save potential client")
                
        except Exception as e:
            logger.error(f"Error saving potential client: {e}")
    
    async def _send_notifications(
        self, 
        user_id: int, 
        message: Dict[str, Any], 
        template: Dict[str, Any],
        ai_result: Dict[str, Any], 
        settings: Dict[str, Any]
    ):
        """Отправка уведомлений о найденном клиенте"""
        try:
            notification_accounts = settings.get('notification_account', [])
            if not notification_accounts:
                logger.debug("No notification accounts configured")
                return
            
            # Формируем текст уведомления
            notification_text = self._format_notification(message, template, ai_result)
            
            # Отправляем уведомления
            for account in notification_accounts:
                try:
                    await self.telegram_service.send_private_message(account, notification_text)  # ← ИСПРАВЛЕНО: было send_message
                    logger.info(f"Notification sent to {account}")
                except Exception as send_error:
                    logger.error(f"Failed to send notification to {account}: {send_error}")
                    
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
    
    def _format_notification(
        self, 
        message: Dict[str, Any], 
        template: Dict[str, Any],
        ai_result: Dict[str, Any]
    ) -> str:
        """Форматирование текста уведомления"""
        
        # ✅ Правильно извлекаем данные пользователя из структуры Telegram API
        username = message.get('user_info', {}).get('username', 'unknown')
        first_name = message.get('user_info', {}).get('first_name', '')
        
        # ✅ Данные чата берем из ai_result (там они есть)
        chat_name = ai_result.get('chat_info', {}).get('chat_name', 'Unknown Chat')
        chat_id = ai_result.get('chat_info', {}).get('chat_id', 'unknown')
        
        # ✅ Ключевые слова из ai_result
        matched_keywords = ai_result.get('matched_keywords', [])
        
        # ✅ ID сообщения из message
        message_id = message.get('message_id', message.get('id', 0))
        
        # ✅ Формируем правильную ссылку (убираем 'c/' для публичных чатов если нужно)
        if chat_id != 'unknown' and message_id:
            # Для приватных групп/каналов нужен формат /c/
            if str(chat_id).startswith('-100'):
                clean_chat_id = str(chat_id)[4:]  # убираем -100
                message_link = f"https://t.me/c/{clean_chat_id}/{message_id}"
            else:
                message_link = f"https://t.me/{chat_id}/{message_id}"
        else:
            message_link = "Ссылка недоступна"
        
        return f"""🎯 НОВЫЙ ПОТЕНЦИАЛЬНЫЙ КЛИЕНТ

    👤 Пользователь: @{username} ({first_name})
    💬 Чат: {chat_name}
    📋 Шаблон: {template.get('name', 'Unknown')}
    🔑 Ключевые слова: {', '.join(matched_keywords)}

    📝 Сообщение:
    {message.get('text', '')[:300]}{'...' if len(message.get('text', '')) > 300 else ''}

    🤖 Анализ ИИ:
    {ai_result.get('reasoning', 'Нет объяснения')}

    🔗 Ссылка: {message_link}
    ⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """