# backend/app/services/telegram_service.py - ОЧИЩЕННАЯ ВЕРСИЯ

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient
from telethon.types import User, Chat, Channel, Message
from telethon.sessions import StringSession

from app.core.config import settings
from app.core.database import supabase_client

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        """Инициализация Telegram сервиса"""
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.session_string = settings.TELEGRAM_SESSION_STRING
        
        # Инициализируем клиент с существующей сессией
        session = StringSession(self.session_string) if self.session_string else StringSession()
        self.client = TelegramClient(session, self.api_id, self.api_hash)
        
        # Блокировка для безопасного доступа к клиенту
        self.client_lock = asyncio.Lock()
        
        logger.info("🚀 Telegram Service initialized")
    
    async def start(self) -> bool:
        """Запуск Telegram клиента"""
        try:
            await self.client.start()
            
            # Если сессия пустая, генерируем новую строку сессии
            if not self.session_string:
                self.session_string = self.client.session.save()
                logger.info("📝 Generated new session string")
                
            me = await self.client.get_me()
            logger.info(f"✅ Telegram client started. Logged in as: {me.first_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Telegram client: {e}")
            return False
    
    async def close(self):
        """Закрытие Telegram клиента"""
        try:
            if self.client.is_connected():
                await self.client.disconnect()
                logger.info("✅ Telegram client disconnected")
        except Exception as e:
            logger.error(f"❌ Error closing Telegram client: {e}")
    
    async def is_connected(self) -> bool:
        """Проверка подключения к Telegram"""
        try:
            return self.client.is_connected()
        except Exception:
            return False
    
    async def ensure_connected(self):
        """Обеспечить подключение к Telegram"""
        try:
            if not self.client.is_connected():
                print("🔌 TELEGRAM: Connecting to Telegram...")
                await self.client.connect()
                print("✅ TELEGRAM: Connected to Telegram")
            
            # ИСПРАВЛЯЕМ: Добавляем await
            if not await self.client.is_user_authorized():
                print("❌ TELEGRAM: User not authorized! Need to login first")
                logger.error("Telegram user not authorized. Run authorization script first.")
                raise Exception("Telegram user not authorized. Please run authorization first.")
            else:
                print("✅ TELEGRAM: User is authorized")
                
        except Exception as e:
            logger.error(f"Error ensuring Telegram connection: {e}")
            print(f"❌ TELEGRAM: Connection error: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка состояния Telegram сервиса"""
        try:
            await self.ensure_connected()
            me = await self.client.get_me()
            
            return {
                "status": "healthy",
                "connected": True,
                "user_id": me.id,
                "username": me.username,
                "first_name": me.first_name
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "error": str(e)
            }
    
    async def execute_telegram_operation(self, operation):
        """
        Безопасное выполнение операций с Telegram
        
        Этот метод гарантирует, что:
        1. Клиент подключен
        2. Операция выполняется эксклюзивно (без конкурентного доступа)
        3. Операция повторяется при временных проблемах
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Используем блокировку для предотвращения конкурентного доступа
                async with self.client_lock:
                    # Проверяем и восстанавливаем соединение
                    await self.ensure_connected()
                    
                    # Выполняем операцию
                    return await operation()
                    
            except asyncio.CancelledError:
                logger.warning(f"Operation was cancelled (attempt {attempt+1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error("All retry attempts failed due to cancellation")
                    raise ValueError("Operation was repeatedly cancelled. Please try again later.")
                
                # Экспоненциальная задержка перед повторной попыткой
                await asyncio.sleep(retry_delay * (2 ** attempt))
                
            except Exception as e:
                logger.error(f"Operation failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error("All retry attempts failed")
                    raise
                
                # Экспоненциальная задержка перед повторной попыткой
                await asyncio.sleep(retry_delay * (2 ** attempt))
    
    async def get_group_messages(
        self, 
        group_id: str, 
        limit: int = 2000,
        offset_date: Optional[datetime] = None,
        include_replies: bool = True,
        get_users: bool = True,
        save_to_db: bool = False,
        days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        БЕЗОПАСНЫЙ метод получения сообщений из группы
        Основан на рабочей версии + логика offset_date
        """
        try:
            # Подключаемся если нужно
            await self.ensure_connected()
            
            # Получаем entity напрямую
            try:
                if str(group_id).lstrip('-').isdigit():
                    entity = await self.client.get_entity(int(group_id))
                else:
                    entity = await self.client.get_entity(group_id)
            except Exception as e:
                logger.error(f"Failed to get entity for group {group_id}: {e}")
                return []
            
            # Логика фильтрации по времени
            cutoff_date = None
            if offset_date is not None:
                # Приоритет у offset_date (для client_monitoring)
                cutoff_date = offset_date
                logger.info(f"Getting messages newer than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} (using offset_date)")
            elif days_back is not None and days_back > 0:
                # Fallback на days_back (для других частей системы)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
                logger.info(f"Getting messages newer than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} (last {days_back} days)")
            else:
                logger.info(f"Getting last {limit} messages (no date filtering)")
            
            messages = []
            users_cache = {}
            
            # Основной цикл получения сообщений
            async for message in self.client.iter_messages(entity, limit=limit):
                # КЛЮЧЕВАЯ ЛОГИКА: Если сообщение старше cutoff_date - останавливаемся
                if cutoff_date is not None and message.date < cutoff_date:
                    logger.info(f"Reached message from {message.date.strftime('%Y-%m-%d %H:%M:%S')} - stopping")
                    break
                
                # Обрабатываем сообщение
                try:
                    msg_data = {
                        'message_id': str(message.id),
                        'text': message.text or "",
                        'date': message.date.isoformat(),
                        'sender_id': str(message.sender_id) if message.sender_id else None,
                        'is_reply': message.is_reply,
                        'reply_to_message_id': str(message.reply_to_msg_id) if message.reply_to_msg_id else None,
                        'forward_from': None,
                        'media_type': None,
                        'edit_date': message.edit_date.isoformat() if message.edit_date else None,
                        'views': getattr(message, 'views', None),
                        'user_info': None,
                        'chat_id': str(group_id),
                        'chat_title': getattr(entity, 'title', f'Chat {group_id}') 
                    }
                    
                    # Добавляем информацию о пользователе если запрошено
                    if get_users and message.sender_id:
                        user_id_str = str(message.sender_id)
                        
                        # Проверяем кэш пользователей
                        if user_id_str not in users_cache:
                            try:
                                user = await self.client.get_entity(message.sender_id)
                                users_cache[user_id_str] = {
                                    'telegram_id': str(user.id),
                                    'username': user.username,
                                    'first_name': user.first_name,
                                    'last_name': user.last_name,
                                    'is_bot': getattr(user, 'bot', False)
                                }
                            except:
                                users_cache[user_id_str] = {
                                    'telegram_id': user_id_str,
                                    'username': None,
                                    'first_name': None,
                                    'last_name': None,
                                    'is_bot': False
                                }
                        
                        msg_data['user_info'] = users_cache[user_id_str]
                    
                    # Определяем тип медиа
                    if message.media:
                        if hasattr(message.media, 'photo'):
                            msg_data['media_type'] = 'photo'
                        elif hasattr(message.media, 'video'):
                            msg_data['media_type'] = 'video'
                        elif hasattr(message.media, 'document'):
                            msg_data['media_type'] = 'document'
                        else:
                            msg_data['media_type'] = 'other'
                    
                    messages.append(msg_data)
                    
                except Exception as message_error:
                    logger.warning(f"Failed to process message {message.id}: {message_error}")
                    continue
            
            # Финальная статистика
            if cutoff_date:
                logger.info(f"Retrieved {len(messages)} messages newer than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                logger.info(f"Retrieved {len(messages)} latest messages (limit={limit})")
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages from group {group_id}: {e}")
            return []
    
    async def get_entity(self, identifier):
        """Получить entity по идентификатору"""
        await self.ensure_connected()
        return await self.client.get_entity(identifier)
    
    async def get_group_info(self, link_or_username: str) -> Dict[str, Any]:
        """Получить информацию о группе/канале"""
        async def operation():
            try:
                entity = await self.client.get_entity(link_or_username)
                
                if isinstance(entity, (Chat, Channel)):
                    group_info = {
                        'id': str(entity.id),
                        'title': entity.title,
                        'username': getattr(entity, 'username', None),
                        'participants_count': getattr(entity, 'participants_count', None),
                        'description': getattr(entity, 'about', None)
                    }
                    
                    # Дополнительная информация для каналов
                    if isinstance(entity, Channel):
                        group_info.update({
                            'is_broadcast': getattr(entity, 'broadcast', False),
                            'is_megagroup': getattr(entity, 'megagroup', False)
                        })
                    
                    logger.info(f"Retrieved info for group {link_or_username}")
                    return group_info
                
                logger.warning(f"Entity {link_or_username} is not a group or channel")
                return {}
            except Exception as e:
                logger.error(f"Error getting entity {link_or_username}: {e}")
                return {}
                
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Error retrieving group info for {link_or_username}: {e}")
            return {}
    
    async def get_moderators(self, group_id: str, save_to_db: bool = False) -> List[Dict[str, Any]]:
        """Получить модераторов группы"""
        async def operation():
            try:
                entity = await self.client.get_entity(group_id)
                moderators = []
                
                async for participant in self.client.iter_participants(entity, filter=None):
                    if hasattr(participant.participant, 'admin_rights') and participant.participant.admin_rights:
                        moderator = {
                            'telegram_id': str(participant.id),
                            'username': participant.username,
                            'first_name': participant.first_name,
                            'last_name': participant.last_name,
                            'is_creator': hasattr(participant.participant, 'creator') and participant.participant.creator,
                            'admin_rights': str(participant.participant.admin_rights)
                        }
                        moderators.append(moderator)
                
                logger.info(f"Found {len(moderators)} moderators in group {group_id}")
                return moderators
                
            except Exception as e:
                logger.error(f"Error getting moderators for group {group_id}: {e}")
                return []
        
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Error retrieving moderators for group {group_id}: {e}")
            return []
    
    async def send_private_message(self, username: str, message: str) -> bool:
        """Отправить личное сообщение пользователю"""
        try:
            await self.ensure_connected()
            
            # Убираем @ если есть
            clean_username = username.lstrip('@')
            
            # Отправляем сообщение
            await self.client.send_message(clean_username, message)
            logger.info(f"✅ Sent notification to {username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send message to {username}: {e}")
            return False
        
    async def resolve_chat_link(self, chat_link: str) -> Optional[str]:
        """
        Конвертировать ссылку t.me в chat_id
        
        Args:
            chat_link: Ссылка вида https://t.me/username или @username
            
        Returns:
            chat_id как строка или None если не удалось найти
        """
        try:
            await self.ensure_connected()
            
            # Очищаем ссылку до username
            username = self._extract_username_from_link(chat_link)
            if not username:
                logger.error(f"Cannot extract username from link: {chat_link}")
                return None
                
            logger.info(f"Resolving username: {username}")
            
            # Получаем entity через Telethon
            entity = await self.client.get_entity(username)
            
            # Получаем chat_id
            if isinstance(entity, Channel):
            # Для каналов и супергрупп нужен отрицательный ID с префиксом -100
                chat_id = f"-100{entity.id}"
            elif isinstance(entity, Chat):
                # Для обычных групп просто отрицательный ID
                chat_id = f"-{entity.id}"
            else:
                # Для пользователей оставляем как есть
                chat_id = str(entity.id)

            # Обработка миграции
            if hasattr(entity, 'migrated_to') and entity.migrated_to:
                # Если канал мигрировал в супергруппу
                chat_id = f"-100{entity.migrated_to.channel_id}"

            print(f"🔗 RESOLVE: Entity type: {type(entity).__name__}, Raw ID: {entity.id}, Chat ID: {chat_id}")


                
            logger.info(f"✅ Resolved {username} -> {chat_id}")
            return chat_id
            
        except Exception as e:
            logger.error(f"❌ Failed to resolve chat link {chat_link}: {e}")
            return None

    def _extract_username_from_link(self, chat_link: str) -> Optional[str]:
        """Извлечь username из различных форматов ссылок"""
        try:
            # Убираем пробелы
            link = chat_link.strip()
            
            # Если уже username без ссылки
            if link.startswith('@'):
                return link[1:]  # убираем @
                
            # Если полная ссылка https://t.me/username
            if 't.me/' in link:
                parts = link.split('t.me/')
                if len(parts) > 1:
                    username = parts[1].strip('/')
                    # Убираем дополнительные параметры после ?
                    if '?' in username:
                        username = username.split('?')[0]
                    return username
                    
            # Если просто username без @
            if link and not link.startswith('http'):
                return link
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting username from {chat_link}: {e}")
            return None

    async def resolve_multiple_chat_links(self, chat_links: List[str]) -> Dict[str, Optional[str]]:
        """
        Конвертировать несколько ссылок одновременно
        
        Returns:
            Словарь {ссылка: chat_id или None}
        """
        results = {}
        
        print(f"🔗 RESOLVING {len(chat_links)} chat links:")
        for i, link in enumerate(chat_links):
            print(f"  {i+1}. '{link}'")
        
        for link in chat_links:
            chat_id = await self.resolve_chat_link(link)
            results[link] = chat_id
            print(f"🔗 RESULT: '{link}' -> {chat_id}")
            
            # Небольшая пауза между запросами чтобы не нарваться на лимиты
            await asyncio.sleep(0.5)
        
        return results
        
    def generate_session_string(self) -> str:
        """Получить строку сессии"""
        return self.client.session.save()
    

# Глобальный экземпляр сервиса
telegram_service = TelegramService()


    