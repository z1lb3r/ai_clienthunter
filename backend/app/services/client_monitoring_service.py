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
        """Публичный метод для одноразового поиска и анализа"""
        await self._search_and_analyze(user_id, settings)
    
    async def _search_and_analyze(self, user_id: int, settings: Dict[str, Any]):
        """Основной метод поиска и анализа клиентов"""
        try:
            logger.info(f"Starting client search and analysis for user {user_id}")
            
            # Получаем шаблоны
            templates = await self._get_user_templates(user_id)
            if not templates:
                logger.info(f"No active templates found for user {user_id}")
                return
            
            logger.info(f"Found {len(templates)} active templates for user {user_id}")
            
            # Статистика
            total_messages_found = 0
            total_keyword_matches = 0
            total_potential_clients = 0
            
            # Обрабатываем каждый шаблон
            for template in templates:
                template_name = template.get('name', 'Unknown')
                logger.info(f"Processing template: {template_name}")
                
                # Парсим keywords
                keywords = self._parse_keywords(template.get('keywords'))
                if not keywords:
                    logger.warning(f"No valid keywords in template {template_name}")
                    continue
                
                # Получаем чаты для этого шаблона
                monitored_chats = template.get('chat_ids', [])
                if not monitored_chats:
                    logger.warning(f"No monitored chats in template {template_name}")
                    continue
                
                logger.debug(f"Template {template_name}: {len(keywords)} keywords, {len(monitored_chats)} chats")
                
                # Обрабатываем каждый чат
                template_matches = 0
                for chat_id in monitored_chats:
                    try:
                        # Получаем сообщения
                        lookback_minutes = template.get('lookback_minutes', 5)
                        messages = await self._get_recent_messages(chat_id, lookback_minutes)
                        
                        if not messages:
                            continue
                            
                        total_messages_found += len(messages)
                        logger.debug(f"Chat {chat_id}: found {len(messages)} recent messages")
                        
                        # Анализируем каждое сообщение
                        for message in messages:
                            matched_keywords = self._find_keywords_in_message(
                                message.get('message', ''), keywords
                            )
                            
                            if matched_keywords:
                                total_keyword_matches += 1
                                template_matches += 1
                                
                                if settings.ENABLE_DEBUG_LOGGING:
                                    logger.debug(f"Keywords match in chat {chat_id}: {matched_keywords}")
                                
                                # Анализ через ИИ
                                try:
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
                                    total_potential_clients += 1
                                except Exception as ai_error:
                                    logger.error(f"AI analysis failed for message: {ai_error}")
                    
                    except Exception as chat_error:
                        logger.error(f"Error processing chat {chat_id}: {chat_error}")
                        continue
                
                logger.info(f"Template {template_name} completed: {template_matches} keyword matches")
            
            # Финальная статистика
            logger.info(f"Analysis completed for user {user_id}: "
                       f"{total_messages_found} messages, "
                       f"{total_keyword_matches} keyword matches, "
                       f"{total_potential_clients} potential clients analyzed")
            
        except Exception as e:
            logger.error(f"Critical error in search and analyze: {e}")
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
                chat_id=chat_id,
                limit=100,
                offset_date=cutoff_time
            )
            
            # Фильтруем по времени
            filtered_messages = []
            for msg in messages:
                msg_date = msg.get('date')
                if msg_date and msg_date >= cutoff_time:
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
        
        found_keywords = []
        message_lower = message_text.lower()
        
        for keyword in keywords:
            if keyword.lower() in message_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    async def _analyze_message_with_ai(
        self, 
        user_id: int, 
        chat_id: str, 
        chat_name: str,
        message_data: Dict[str, Any], 
        settings: Dict[str, Any]
    ):
        """Анализ сообщения через ИИ"""
        try:
            message = message_data['message']
            template = message_data['template']
            matched_keywords = message_data['matched_keywords']
            
            # Подготавливаем данные для ИИ
            author_info = {
                'telegram_id': message.get('from_id', 'unknown'),
                'username': message.get('username', ''),
                'first_name': message.get('first_name', ''),
                'last_name': message.get('last_name', '')
            }
            
            chat_info = {
                'chat_id': chat_id,
                'chat_name': chat_name
            }
            
            message_text = message.get('message', '')
            
            # Логируем только в DEBUG режиме
            if settings.ENABLE_DEBUG_LOGGING and settings.LOG_MESSAGE_CONTENT:
                logger.debug(f"AI analysis for message: {message_text[:100]}...")
            
            # Вызываем ИИ анализ
            ai_result = await self.openai_service.analyze_potential_client(
                message_text=message_text,
                product_name=template.get('name', 'Unknown Product'),
                keywords=template.get('keywords', []),
                matched_keywords=matched_keywords,
                author_info=author_info,
                chat_info=chat_info,
                custom_prompt=template.get('ai_prompt', '')
            )
            
            confidence = ai_result.get('confidence', 0)
            min_confidence = template.get('min_ai_confidence', 7)
            
            if confidence >= min_confidence:
                # Сохраняем потенциального клиента
                await self._save_potential_client(
                    user_id, message, template, matched_keywords, ai_result, chat_id, chat_name
                )
                
                # Отправляем уведомления
                await self._send_notifications(user_id, message, template, ai_result, settings)
                
                logger.info(f"Potential client found: confidence {confidence}/10, template '{template.get('name')}'")
            else:
                logger.debug(f"Low confidence ({confidence}/10), skipping client")
                
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            raise
    
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
                'telegram_user_id': str(message.get('from_id', '')),
                'username': message.get('username', ''),
                'first_name': message.get('first_name', ''),
                'last_name': message.get('last_name', ''),
                'message_text': message.get('message', ''),
                'matched_template_id': template.get('id'),
                'matched_keywords': matched_keywords,
                'ai_confidence': ai_result.get('confidence', 0),
                'ai_reasoning': ai_result.get('reasoning', ''),
                'intent_type': ai_result.get('intent_type', ''),
                'chat_id': chat_id,
                'chat_title': chat_name,
                'message_id': message.get('id', 0),
                'client_status': 'new',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            result = supabase_client.table('potential_clients').insert(client_data).execute()
            
            if result.data:
                logger.info(f"Saved potential client: {client_data.get('username', 'unknown')}")
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
                    await self.telegram_service.send_message(account, notification_text)
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
        return f"""🎯 НОВЫЙ ПОТЕНЦИАЛЬНЫЙ КЛИЕНТ

👤 Пользователь: @{message.get('username', 'unknown')} ({message.get('first_name', '')})
📋 Шаблон: {template.get('name', 'Unknown')}
🎯 Уверенность ИИ: {ai_result.get('confidence', 0)}/10
💭 Тип намерения: {ai_result.get('intent_type', 'unknown')}

📝 Сообщение:
{message.get('message', '')[:300]}{'...' if len(message.get('message', '')) > 300 else ''}

🤖 Анализ ИИ:
{ai_result.get('reasoning', 'Нет объяснения')}

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""