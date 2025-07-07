# backend/app/services/client_monitoring_service.py
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import re

from ..core.database import supabase_client
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
            
            # Запускаем фоновую задачу мониторинга
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
                # Получаем настройки пользователя
                settings = await self._get_user_settings(user_id)
                
                if not settings or not settings.get('is_active', False):
                    await asyncio.sleep(60)  # Ждем минуту если мониторинг выключен
                    continue
                
                # Выполняем поиск и анализ
                await self._search_and_analyze(user_id, settings)
                
                # Ждем следующий цикл
                interval = settings.get('check_interval_minutes', 5) * 60
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop for user {user_id}: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    async def _get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить настройки мониторинга пользователя"""
        try:
            result = supabase_client.table('monitoring_settings').select('*').eq('user_id', user_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting user settings for {user_id}: {e}")
            return None

    
    async def _search_and_analyze(self, user_id: int, settings: Dict[str, Any]):
        """Поиск ключевых слов и анализ найденных сообщений - С ДЕТАЛЬНОЙ ДИАГНОСТИКОЙ"""
        try:
            print(f"🔎 CLIENT_MONITOR: Starting search and analyze for user {user_id}")
            print(f"🔎 CLIENT_MONITOR: Settings received: {settings}")
            logger.info(f"🔎 CLIENT_MONITOR: Starting search and analyze for user {user_id}")
            
            # === ЭТАП 1: Получение шаблонов ===
            print("📝 CLIENT_MONITOR: Step 1 - Getting user templates...")
            templates = await self._get_user_templates(user_id)
            print(f"📝 CLIENT_MONITOR: Retrieved {len(templates)} templates from database")
            
            if not templates:
                print("❌ CLIENT_MONITOR: No templates found - stopping analysis")
                logger.info(f"No templates for user {user_id}")
                return
            
            # Детальная информация о каждом шаблоне
            for i, template in enumerate(templates):
                print(f"📝 CLIENT_MONITOR: Template {i+1}: '{template.get('name', 'UNNAMED')}'")
                print(f"📝 CLIENT_MONITOR: Template {i+1} ID: {template.get('id')}")
                
                # ПРОБЛЕМА keywords могут быть строкой вместо массива - ИСПРАВЛЯЕМ
                keywords_raw = template.get('keywords', [])
                print(f"📝 CLIENT_MONITOR: Template {i+1} keywords (RAW): {keywords_raw}")
                print(f"📝 CLIENT_MONITOR: Template {i+1} keywords TYPE: {type(keywords_raw)}")
                
                # Проверяем и парсим keywords
                if isinstance(keywords_raw, str):
                    print(f"⚠️ CLIENT_MONITOR: Keywords is STRING, need to parse JSON: {keywords_raw}")
                    try:
                        import json
                        keywords_parsed = json.loads(keywords_raw)
                        print(f"✅ CLIENT_MONITOR: Successfully parsed keywords: {keywords_parsed}")
                        template['keywords'] = keywords_parsed  # Обновляем в template
                    except Exception as parse_error:
                        print(f"❌ CLIENT_MONITOR: Failed to parse keywords JSON: {parse_error}")
                        print(f"❌ CLIENT_MONITOR: Skipping template {i+1} due to keywords error")
                        continue
                elif isinstance(keywords_raw, list):
                    print(f"✅ CLIENT_MONITOR: Keywords is already LIST: {keywords_raw}")
                else:
                    print(f"❌ CLIENT_MONITOR: Keywords has unexpected type: {type(keywords_raw)}")
                    continue
                
                final_keywords = template.get('keywords', [])
                print(f"📝 CLIENT_MONITOR: Template {i+1} FINAL keywords: {final_keywords}")
            
            # === ЭТАП 2: Получение чатов ===
            print("💬 CLIENT_MONITOR: Step 2 - Getting monitored chats...")
            monitored_chats = settings.get('monitored_chats', [])
            print(f"💬 CLIENT_MONITOR: Found {len(monitored_chats)} monitored chats: {monitored_chats}")
            
            if not monitored_chats:
                print("❌ CLIENT_MONITOR: No monitored chats - stopping analysis")
                logger.info(f"No monitored chats for user {user_id}")
                return
            
            # === ЭТАП 3: Получение настроек ===
            print("⚙️ CLIENT_MONITOR: Step 3 - Processing settings...")
            lookback_minutes = settings.get('lookback_minutes', 5)
            min_ai_confidence = settings.get('min_ai_confidence', 7)
            print(f"⚙️ CLIENT_MONITOR: Lookback minutes: {lookback_minutes}")
            print(f"⚙️ CLIENT_MONITOR: Min AI confidence: {min_ai_confidence}")
            
            # === ЭТАП 4: Обработка каждого чата ===
            print(f"🔄 CLIENT_MONITOR: Step 4 - Processing {len(monitored_chats)} chats...")
            
            total_messages_found = 0
            total_keyword_matches = 0
            
            for chat_index, chat_id in enumerate(monitored_chats):
                try:
                    print(f"💬 CLIENT_MONITOR: === Processing chat {chat_index+1}/{len(monitored_chats)}: {chat_id} ===")
                    
                    # Получаем название чата
                    try:
                        chat_info = await self.telegram_service.get_group_info(chat_id)
                        chat_name = chat_info.get('title', f'Chat {chat_id}') if chat_info else f'Chat {chat_id}'
                        print(f"📋 CLIENT_MONITOR: Chat name: '{chat_name}'")
                    except Exception as chat_info_error:
                        print(f"⚠️ CLIENT_MONITOR: Could not get chat info: {chat_info_error}")
                        chat_name = f'Chat {chat_id}'  # Fallback название
                        print(f"📋 CLIENT_MONITOR: Using fallback chat name: '{chat_name}'")
                    
                    # === ЭТАП 4.1: Получение сообщений ===
                    print(f"📥 CLIENT_MONITOR: Getting recent messages from chat {chat_id}...")
                    print(f"📥 CLIENT_MONITOR: Calling _get_recent_messages({chat_id}, {lookback_minutes})")
                    
                    recent_messages = await self._get_recent_messages(chat_id, lookback_minutes)
                    print(f"📥 CLIENT_MONITOR: Retrieved {len(recent_messages)} recent messages from chat {chat_id}")
                    total_messages_found += len(recent_messages)
                    
                    if not recent_messages:
                        print(f"⚠️ CLIENT_MONITOR: No recent messages in chat {chat_id} - skipping")
                        continue
                    
                    # Показываем примеры сообщений
                    for msg_i, msg in enumerate(recent_messages[:3]):  # Показываем первые 3
                        msg_text = msg.get('text', '')[:100]  # Первые 100 символов
                        print(f"📄 CLIENT_MONITOR: Message {msg_i+1}: '{msg_text}...'")
                    
                    # === ЭТАП 4.2: Поиск по шаблонам ===
                    print(f"🔍 CLIENT_MONITOR: Searching through {len(templates)} templates...")
                    
                    for template_index, template in enumerate(templates):
                        template_name = template.get('name', f'Template_{template_index}')
                        keywords = template.get('keywords', [])
                        
                        print(f"🔍 CLIENT_MONITOR: === Template {template_index+1}: '{template_name}' ===")
                        print(f"🔍 CLIENT_MONITOR: Searching for keywords: {keywords}")
                        
                        if not keywords:
                            print(f"⚠️ CLIENT_MONITOR: No keywords in template '{template_name}' - skipping")
                            continue
                        
                        # === ЭТАП 4.3: Поиск ключевых слов в сообщениях ===
                        template_matches = 0
                        for message_index, message in enumerate(recent_messages):
                            message_text = message.get('text', '')
                            
                            if not message_text:
                                continue
                            
                            print(f"🔎 CLIENT_MONITOR: Checking message {message_index+1} with template '{template_name}'")
                            print(f"🔎 CLIENT_MONITOR: Message text: '{message_text[:150]}...'")
                            
                            matched_keywords = self._find_keywords_in_text(message_text, keywords)
                            
                            if matched_keywords:
                                template_matches += 1
                                total_keyword_matches += 1
                                
                                print(f"🎯 CLIENT_MONITOR: MATCH FOUND! Keywords: {matched_keywords}")
                                print(f"🎯 CLIENT_MONITOR: Message: '{message_text}'")
                                
                                # === ЭТАП 4.4: Подготовка данных для ИИ ===
                                print(f"🤖 CLIENT_MONITOR: Preparing data for AI analysis...")
                                message_data = {
                                    'message': message,
                                    'template': template,
                                    'matched_keywords': matched_keywords
                                }
                                
                                print(f"🤖 CLIENT_MONITOR: Message data prepared: {list(message_data.keys())}")
                                
                                # === ЭТАП 4.5: Анализ через ИИ ===
                                print(f"🤖 CLIENT_MONITOR: Calling AI analysis...")
                                try:
                                    await self._analyze_message_with_ai(user_id, chat_id, chat_name, message_data, settings)
                                    print(f"✅ CLIENT_MONITOR: AI analysis completed successfully")
                                except Exception as ai_error:
                                    print(f"❌ CLIENT_MONITOR: AI analysis failed: {ai_error}")
                                    logger.error(f"AI analysis error: {ai_error}")
                                    # ПРОДОЛЖАЕМ обработку следующих сообщений
                                    continue  # ← ВАЖНО: НЕ ПРЕРЫВАЕМ ВЕСЬ ПРОЦЕСС
                            else:
                                print(f"❌ CLIENT_MONITOR: No keywords found in message {message_index+1}")
                        
                        print(f"📊 CLIENT_MONITOR: Template '{template_name}' matches: {template_matches}")
                    
                    print(f"✅ CLIENT_MONITOR: Completed processing chat {chat_id}")
                    
                except Exception as chat_error:
                    print(f"❌ CLIENT_MONITOR: Error processing chat {chat_id}: {chat_error}")
                    logger.error(f"Error processing chat {chat_id}: {chat_error}")
                    import traceback
                    print(f"❌ CLIENT_MONITOR: Chat error traceback: {traceback.format_exc()}")
                    # ПРОДОЛЖАЕМ обработку следующих чатов
                    continue  # ← ВАЖНО: НЕ ПРЕРЫВАЕМ ВЕСЬ ПРОЦЕСС
            
            # === ФИНАЛЬНАЯ СТАТИСТИКА ===
            print(f"📊 CLIENT_MONITOR: === FINAL STATISTICS ===")
            print(f"📊 CLIENT_MONITOR: Total chats processed: {len(monitored_chats)}")
            print(f"📊 CLIENT_MONITOR: Total messages found: {total_messages_found}")
            print(f"📊 CLIENT_MONITOR: Total keyword matches: {total_keyword_matches}")
            print(f"✅ CLIENT_MONITOR: Search and analyze completed successfully")
            
        except Exception as e:
            print(f"❌ CLIENT_MONITOR: CRITICAL ERROR in search and analyze: {e}")
            logger.error(f"Error in search and analyze: {e}")
            import traceback
            print(f"❌ CLIENT_MONITOR: Critical error traceback: {traceback.format_exc()}")
            raise
    
    async def _get_user_templates(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить активные шаблоны пользователя"""
        try:
            result = supabase_client.table('product_templates').select('*').eq('user_id', user_id).eq('is_active', True).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting user templates: {e}")
            return []
    
    async def _get_recent_messages(self, chat_id: str, lookback_minutes: int) -> List[Dict[str, Any]]:
        """Получить сообщения за последние N минут - ПРАВИЛЬНАЯ ВЕРСИЯ"""
        try:
            print(f"📥 CLIENT_MONITOR: Getting messages from last {lookback_minutes} minutes from chat {chat_id}")
            
            # Вычисляем точное время cutoff
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
            print(f"📥 CLIENT_MONITOR: Cutoff time (UTC): {cutoff_time}")
            
            # Проверяем доступные методы TelegramService
            print(f"📥 CLIENT_MONITOR: TelegramService methods: {[method for method in dir(self.telegram_service) if not method.startswith('_')]}")
            
            # Получаем сообщения с фильтрацией по времени через Telegram API
            print(f"📥 CLIENT_MONITOR: Calling telegram_service.get_group_messages with offset_date...")
            
            try:
                # Первый способ: используем offset_date для точной фильтрации по времени
                messages = await self.telegram_service.get_group_messages(
                    group_id=chat_id,
                    offset_date=cutoff_time,
                    get_users=True 
                )
                print(f"✅ CLIENT_MONITOR: Got {len(messages)} messages using offset_date filter")
                
            except Exception as api_error:
                print(f"⚠️ CLIENT_MONITOR: offset_date failed: {api_error}")
                print(f"🔄 CLIENT_MONITOR: Trying fallback method...")
                
                # Fallback: получаем разумное количество сообщений и фильтруем сами
                # В очень активном чате может быть до 100 сообщений в минуту
                estimated_limit = max(500, lookback_minutes * 100)
                print(f"📥 CLIENT_MONITOR: Using fallback with limit={estimated_limit}")
                
                all_messages = await self.telegram_service.get_group_messages(
                    group_id=chat_id,
                    limit=estimated_limit,
                    get_users=True 
                )
                
                # Фильтруем по времени
                print(f"📥 CLIENT_MONITOR: Filtering {len(all_messages)} messages by time...")
                messages = []
                
                for msg in all_messages:
                    try:
                        msg_date = msg.get('date', '')
                        if not msg_date:
                            continue
                        
                        # Парсим дату
                        if msg_date.endswith('Z'):
                            msg_time = datetime.fromisoformat(msg_date.replace('Z', '+00:00'))
                        elif '+' in msg_date or msg_date.endswith('+00:00'):
                            msg_time = datetime.fromisoformat(msg_date)
                        else:
                            msg_time = datetime.fromisoformat(msg_date).replace(tzinfo=timezone.utc)
                        
                        # Проверяем время
                        if msg_time >= cutoff_time:
                            messages.append(msg)
                        else:
                            # Сообщения отсортированы по убыванию времени - можно остановиться
                            print(f"📥 CLIENT_MONITOR: Reached old message from {msg_time}, stopping")
                            break
                            
                    except Exception as parse_error:
                        print(f"⚠️ CLIENT_MONITOR: Error parsing message date: {parse_error}")
                        continue
                
                print(f"✅ CLIENT_MONITOR: Filtered to {len(messages)} recent messages")
            
            # Показываем примеры найденных сообщений
            if messages:
                print(f"📊 CLIENT_MONITOR: Sample messages:")
                for i, msg in enumerate(messages[:3]):
                    msg_text = msg.get('text', '')[:50]
                    msg_date = msg.get('date', 'No date')
                    print(f"📄 CLIENT_MONITOR: Message {i+1}: '{msg_text}...' at {msg_date}")
            else:
                print(f"⚠️ CLIENT_MONITOR: No messages found in last {lookback_minutes} minutes")
            
            return messages
            
        except Exception as e:
            print(f"❌ CLIENT_MONITOR: Error getting recent messages from {chat_id}: {e}")
            logger.error(f"Error getting recent messages from {chat_id}: {e}")
            import traceback
            print(f"❌ CLIENT_MONITOR: Traceback: {traceback.format_exc()}")
        return []
    
    def _find_keywords_in_text(self, text: str, keywords: List[str]) -> List[str]:
        """Найти ключевые слова в тексте"""
        if not text:
            return []
        
        text_lower = text.lower()
        matched_keywords = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            
            # Простой поиск подстроки
            if keyword_lower in text_lower:
                matched_keywords.append(keyword)
        
        return matched_keywords
    
    async def _analyze_message_with_ai(
        self, 
        user_id: int, 
        chat_id: str,
        chat_name: str,
        message_data: Dict[str, Any], 
        settings: Dict[str, Any]
    ):
        """Анализ сообщения через ИИ и сохранение результата"""
        try:
            message = message_data['message']
            template = message_data['template']
            matched_keywords = message_data['matched_keywords']
            
            # Проверяем, не анализировали ли мы уже это сообщение
            if await self._is_message_already_processed(message.get('message_id'), user_id):
                print(f"🔄 CLIENT_MONITOR: Message {message.get('message_id')} already processed - skipping")
                return
            
            # Подготавливаем данные автора
            author_info = message.get('user_info', {}) or {}

            # Подготавливаем данные чата
            chat_info = {
                'chat_id': chat_id,
                'chat_name': chat_name
            }

            # Вызываем реальный ИИ анализ с полными данными
            ai_result = await self._call_ai_analysis(
                message_text=message.get('text', ''),
                product_name=template['name'],
                keywords=template['keywords'],
                matched_keywords=matched_keywords,
                author_info=author_info,
                chat_info=chat_info
            )
            
            print(f"🤖 CLIENT_MONITOR: AI analysis result - confidence: {ai_result.get('confidence', 0)}/10")
            
            # Проверяем минимальную уверенность
            min_confidence = settings.get('min_ai_confidence', 7)
            if ai_result.get('confidence', 0) >= min_confidence:
                print(f"✅ CLIENT_MONITOR: Confidence {ai_result.get('confidence')} >= {min_confidence} - saving client")
                
                # Сохраняем потенциального клиента
                await self._save_potential_client(user_id, chat_id, chat_name, message_data, ai_result)
                
                # Отправляем уведомление
                notification_account = settings.get('notification_account')
                await self._send_notification(notification_account, message_data, ai_result)
            else:
                print(f"❌ CLIENT_MONITOR: Confidence {ai_result.get('confidence')} < {min_confidence} - not saving")
            
        except Exception as e:
            print(f"❌ CLIENT_MONITOR: AI analysis failed for message {message.get('message_id')}: {e}")
            logger.error(f"AI analysis failed for message {message.get('message_id')}: {e}")
            # НЕ ПРЕРЫВАЕМ ОБРАБОТКУ - продолжаем с другими сообщениями

    
    async def _is_message_already_processed(self, message_id: str, user_id: int) -> bool:
        """Проверить, обрабатывалось ли уже это сообщение"""
        try:
            if not message_id:
                return False
            
            result = supabase_client.table('potential_clients').select('id').eq('message_id', message_id).eq('user_id', user_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error checking if message processed: {e}")
            return False
    
    async def _call_ai_analysis(self, 
                            message_text: str,
                            product_name: str, 
                            keywords: List[str],
                            matched_keywords: List[str],
                            author_info: Dict[str, Any],
                            chat_info: Dict[str, Any]) -> Dict[str, Any]:
        """Вызов ИИ для анализа с полными данными"""
        try:
            # Вызываем реальный OpenAI анализ
            result = await self.openai_service.analyze_potential_client(
                message_text=message_text,
                product_name=product_name,
                keywords=keywords,
                matched_keywords=matched_keywords,
                author_info=author_info,
                chat_info=chat_info
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling AI analysis: {e}")
            return {
                "confidence": 0,
                "intent_type": "unknown", 
                "reasoning": "Ошибка анализа ИИ",
                "message_data": {
                    "text": message_text,
                    "author": author_info,
                    "chat": chat_info
                }
            }
    
    async def _save_potential_client(
        self, 
        user_id: int, 
        chat_id: str,   
        chat_name: str,
        message_data: Dict[str, Any], 
        ai_result: Dict[str, Any]
    ):
        """Сохранить потенциального клиента в базу данных"""
        try:
            message = message_data['message']
            template = message_data['template']
            author = message.get('user_info', {}) or {}
            
            # Подготавливаем данные для сохранения
            client_data = {
                'user_id': user_id,
                'product_template_id': template.get('id'),
                'template_name': template.get('name'),             
                'message_id': message.get('message_id'),
                'chat_id': chat_id,
                'chat_name': chat_name,   
                'author_username': author.get('username'),
                'author_id': author.get('telegram_id'),                 
                'message_text': message.get('text', '')[:1000],
                'matched_keywords': message_data['matched_keywords'],
                'ai_confidence': ai_result.get('confidence', 0),
                'ai_intent_type': ai_result.get('intent_type', 'unknown'),
                'ai_explanation_text': ai_result.get('reasoning', ''), 
                'client_status': 'new',
                'notification_sent': False,
                'created_at': datetime.now().isoformat()
            }
                        
            result = supabase_client.table('potential_clients').insert(client_data).execute()
            
            if result.data:
                logger.info(f"Saved potential client: {author.get('username', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error saving potential client: {e}")
    
    async def _send_notification(
        self, 
        notification_account: Optional[str], 
        message_data: Dict[str, Any], 
        ai_result: Dict[str, Any]
    ):
        """Отправить уведомление о найденном клиенте"""
        try:
            if not notification_account:
                logger.info("No notification account configured")
                return
            
            message = message_data['message']
            template = message_data['template']
            author = message.get('user_info', {}) or {}

            # Формируем информацию об авторе
            username = author.get('username')
            first_name = author.get('first_name', 'Имя не указано')
            author_id = author.get('telegram_id', message.get('sender_id', 'ID неизвестен'))

            if username:
                author_info = f"@{username} ({first_name})"
            else:
                author_info = f"{first_name} (ID: {author_id})"

            # Формируем ссылку на сообщение - ИСПРАВЛЕНО!
            chat_id = message.get('chat_id', 'unknown')
            message_id = message.get('message_id', 'unknown')
            chat_name = message.get('chat_title', 'Неизвестный чат')
            
            # Убираем -100 из chat_id для ссылки
            if str(chat_id).startswith('-100'):
                clean_chat_id = str(chat_id)[4:]
            else:
                clean_chat_id = str(chat_id)
                
            message_link = f"https://t.me/c/{clean_chat_id}/{message_id}"
            
            # Формируем текст уведомления
            notification_text = f"""🔥 НАЙДЕН ПОТЕНЦИАЛЬНЫЙ КЛИЕНТ!

    💡 Продукт: {template['name']}
    📱 Сообщение: "{message.get('text', '')[:200]}..."
    👤 Автор: {author_info}
    💬 Чат: {chat_name}
    🎯 Ключевые слова: {', '.join(message_data['matched_keywords'])}
    🤖 Уверенность ИИ: {ai_result.get('confidence', 0)}/10
    📊 Тип намерения: {ai_result.get('intent_type', 'unknown')}
    📅 Время: {datetime.now().strftime('%H:%M, %d.%m.%Y')}

    🔗 [Перейти к сообщению]({message_link})

    👆 Переходи в чат и предлагай свой товар!"""

            # Отправляем через Telegram API
            try:
                success = await self.telegram_service.send_private_message(notification_account, notification_text)
                if success:
                    logger.info(f"✅ Notification sent to {notification_account}")
                else:
                    logger.error(f"❌ Failed to send notification to {notification_account}")
            except Exception as e:
                logger.error(f"❌ Error sending Telegram notification: {e}")
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")