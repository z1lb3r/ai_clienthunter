# backend/app/services/telegram_service.py
from telethon import TelegramClient, types
from telethon.sessions import StringSession
from telethon.tl.types import Message, User, Channel, Chat
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import asyncio
import uuid
import logging
import re
from urllib.parse import urlparse
from ..core.config import settings
from ..core.database import supabase_client

logger = logging.getLogger(__name__)


class TelegramService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.session_string = settings.TELEGRAM_SESSION_STRING
        
        # Создаем клиента сразу, но не подключаемся
        self.client = TelegramClient(
            StringSession(self.session_string),
            self.api_id,
            self.api_hash
        )
        
        # Замок для синхронизации доступа к клиенту
        self.client_lock = asyncio.Lock()
        
        # Отслеживаем состояние подключения
        self.is_connected = False
        self._initialized = True
        
        logger.info("TelegramService initialized")
    
    async def start(self):
        """Запуск клиента при старте приложения"""
        try:
            if not self.is_connected:
                logger.info("Starting Telegram client...")
                await self.client.start()
                self.is_connected = True
                logger.info("Telegram client started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram client: {e}")
            self.is_connected = False
            raise
    
    async def close(self):
        """Корректное закрытие клиента при завершении работы приложения"""
        if self.is_connected:
            logger.info("Disconnecting Telegram client...")
            try:
                # Освобождаем блокировку, если она активна
                if self.client_lock.locked():
                    self.client_lock.release()
                    
                # Отключаем клиента с таймаутом
                await asyncio.wait_for(self.client.disconnect(), timeout=3.0)
                self.is_connected = False
                logger.info("Telegram client disconnected")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
                # Принудительно освобождаем ресурсы
                self.client = None
                self.is_connected = False
    
    async def ensure_connected(self):
        """Проверка и восстановление соединения при необходимости"""
        if not self.client.is_connected():
            logger.info("Client is not connected, reconnecting...")
            try:
                await self.client.connect()
                
                # Проверяем авторизацию
                is_authorized = await self.client.is_user_authorized()
                if not is_authorized:
                    logger.warning("User is not authorized. Session might be invalid.")
                    raise ValueError("User is not authorized. Please provide a valid session string.")
                
                self.is_connected = True
                logger.info("Reconnected successfully")
            except Exception as e:
                self.is_connected = False
                logger.error(f"Failed to reconnect: {e}")
                raise


    async def ensure_connected_with_diagnostics(self):
        """Проверка подключения с расширенной диагностикой"""
        try:
            if not self.client.is_connected():
                logger.info("Client not connected, attempting to reconnect...")
                await self.connect_with_retry()
            
            # Дополнительная проверка авторизации
            if not await self.client.is_user_authorized():
                logger.error("Lost authorization, attempting to reconnect...")
                await self.disconnect()
                await self.connect_with_retry()
            
            return True
            
        except Exception as e:
            logger.error(f"Connection diagnostics failed: {str(e)}")
            self.is_connected = False
            raise

    
    async def execute_telegram_operation(self, operation):
        """
        Выполняет операцию с Telegram API с обработкой соединения и блокировкой.
        
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
        days_back: Optional[int] = None  # НОВЫЙ параметр для фильтрации по дням
    ) -> List[Dict[str, Any]]:
        """
        БЕЗОПАСНЫЙ метод получения сообщений из группы
        Основан на рабочей версии + логика days_back из daysback.docx
        """
        try:
            # Подключаемся если нужно (как в рабочей версии)
            await self.ensure_connected()
            
            # Получаем entity напрямую (БЕЗ execute_telegram_operation!)
            try:
                if str(group_id).lstrip('-').isdigit():
                    entity = await self.client.get_entity(int(group_id))
                else:
                    entity = await self.client.get_entity(group_id)
            except Exception as e:
                logger.error(f"Failed to get entity for group {group_id}: {e}")
                return []
            
            # Логика фильтрации по дням (из daysback.docx)
            cutoff_date = None
            if days_back is not None and days_back > 0:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
                logger.info(f"Getting messages newer than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} (last {days_back} days)")
            else:
                logger.info(f"Getting last {limit} messages (no date filtering)")
            
            messages = []
            users_cache = {}
            
            # Основной цикл получения сообщений (АДАПТИРОВАННЫЙ из daysback.docx для Telethon)
            async for message in self.client.iter_messages(entity, limit=limit):
                # КЛЮЧЕВАЯ ЛОГИКА: Если сообщение старше cutoff_date - останавливаемся
                if cutoff_date is not None and message.date < cutoff_date:
                    logger.info(f"Reached message from {message.date.strftime('%Y-%m-%d %H:%M:%S')} - stopping (older than {days_back} days)")
                    break
                
                # Обрабатываем сообщение (как в рабочей версии)
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
                        'user_info': None
                    }
                    
                    # Информация о медиа
                    if message.media:
                        if hasattr(message.media, 'photo'):
                            msg_data['media_type'] = 'photo'
                        elif hasattr(message.media, 'document'):
                            msg_data['media_type'] = 'document'
                        elif hasattr(message.media, 'video'):
                            msg_data['media_type'] = 'video'
                        else:
                            msg_data['media_type'] = 'other'
                    
                    # Информация о пересылке
                    if message.forward:
                        msg_data['forward_from'] = {
                            'from_id': str(message.forward.from_id) if message.forward.from_id else None,
                            'from_name': getattr(message.forward, 'from_name', None),
                            'date': message.forward.date.isoformat() if message.forward.date else None
                        }
                    
                    # Получаем информацию о пользователе (если нужно)
                    if get_users and message.sender_id:
                        if message.sender_id not in users_cache:
                            try:
                                user = await self.client.get_entity(message.sender_id)
                                if user:
                                    users_cache[message.sender_id] = {
                                        'telegram_id': str(user.id),
                                        'username': getattr(user, 'username', None),
                                        'first_name': getattr(user, 'first_name', None),
                                        'last_name': getattr(user, 'last_name', None),
                                        'is_bot': getattr(user, 'bot', False)
                                    }
                                else:
                                    users_cache[message.sender_id] = None
                            except Exception as user_error:
                                logger.warning(f"Failed to get user info for {message.sender_id}: {user_error}")
                                users_cache[message.sender_id] = None
                        
                        msg_data['user_info'] = users_cache.get(message.sender_id)
                    
                    messages.append(msg_data)
                    
                except Exception as message_error:
                    logger.warning(f"Failed to process message {message.id}: {message_error}")
                    continue
            
            # Финальная статистика
            if cutoff_date:
                logger.info(f"Retrieved {len(messages)} messages for last {days_back} days (newer than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})")
            else:
                logger.info(f"Retrieved {len(messages)} latest messages (limit={limit})")
            
            # Сохранение в БД (если нужно) - как в рабочей версии
            if save_to_db and messages:
                try:
                    for msg in messages:
                        msg_for_db = msg.copy()
                        msg_for_db['group_id'] = group_id
                        msg_for_db['created_at'] = datetime.now().isoformat()
                        
                        supabase_client.table('telegram_messages').upsert(msg_for_db).execute()
                    
                    logger.info(f"Saved {len(messages)} messages to database")
                except Exception as db_error:
                    logger.warning(f"Failed to save messages to database: {db_error}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages from group {group_id}: {e}")
            return []
    
    async def _save_message_to_db(self, group_id: str, message: Dict[str, Any]):
        """Сохранить сообщение в базу данных"""
        try:
            # Сначала получаем ID группы из базы
            db_group = supabase_client.table('telegram_groups').select('id').eq('group_id', group_id).execute()
            
            if not db_group.data:
                logger.warning(f"Group with telegram_id {group_id} not found in database")
                return
                
            db_group_id = db_group.data[0]['id']
            
            # Проверяем, есть ли уже такое сообщение в базе
            existing_msg = supabase_client.table('telegram_messages').select('id')\
                .eq('group_id', db_group_id)\
                .eq('message_id', message['message_id']).execute()
            
            if not existing_msg.data:
                # Создаем запись в базе
                msg_for_db = {
                    'group_id': db_group_id,
                    'message_id': message['message_id'],
                    'sender_id': message['sender_id'],
                    'text': message['text'],
                    'date': message['date'],
                    'is_reply': message['is_reply'],
                    'reply_to_message_id': message['reply_to_message_id']
                }
                supabase_client.table('telegram_messages').insert(msg_for_db).execute()
                logger.debug(f"Message {message['message_id']} saved to database")
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
    
    async def get_group_info(self, group_id: str) -> Dict[str, Any]:
        """Получить информацию о группе"""
        async def operation():
            entity = await self.client.get_entity(group_id)
            group_info = {}
            
            if isinstance(entity, Channel) or isinstance(entity, Chat):
                # Получаем базовую информацию о группе
                group_info = {
                    'id': str(entity.id),
                    'title': getattr(entity, 'title', 'Unknown'),
                    'username': getattr(entity, 'username', None),
                    'description': getattr(entity, 'about', None) if hasattr(entity, 'about') else None,
                    'participants_count': getattr(entity, 'participants_count', None) if hasattr(entity, 'participants_count') else None,
                    'date': getattr(entity, 'date', datetime.now()).isoformat() if hasattr(entity, 'date') else datetime.now().isoformat(),
                    'is_public': bool(getattr(entity, 'username', None))
                }
                
                # Дополнительная информация для каналов
                if isinstance(entity, Channel):
                    group_info.update({
                        'is_broadcast': getattr(entity, 'broadcast', False),
                        'is_megagroup': getattr(entity, 'megagroup', False)
                    })
                
                # Сохраняем или обновляем информацию в базе данных
                await self._save_group_to_db(group_info)
                
                logger.info(f"Retrieved info for group {group_id}")
                return group_info
            
            logger.warning(f"Entity {group_id} is not a group or channel")
            return {}
            
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Error retrieving group info for {group_id}: {e}")
            raise
    
    async def _save_group_to_db(self, group_info: Dict[str, Any]):
        """Сохранить или обновить информацию о группе в базе данных"""
        try:
            # Проверяем, есть ли группа в базе
            existing_group = supabase_client.table('telegram_groups').select('id').eq('group_id', group_info['id']).execute()
            
            # Подготовка данных для базы
            group_data = {
                'name': group_info['title'],
                'settings': {
                    'members_count': group_info.get('participants_count'),
                    'username': group_info.get('username'),
                    'description': group_info.get('description'),
                    'is_public': group_info.get('is_public', False),
                    'is_broadcast': group_info.get('is_broadcast', False),
                    'is_megagroup': group_info.get('is_megagroup', False)
                }
            }
            
            if existing_group.data:
                # Обновляем существующую группу
                supabase_client.table('telegram_groups').update(group_data).eq('group_id', group_info['id']).execute()
                logger.debug(f"Updated group {group_info['id']} in database")
            else:
                # Создаем новую группу
                group_data['group_id'] = group_info['id']
                supabase_client.table('telegram_groups').insert(group_data).execute()
                logger.debug(f"Added new group {group_info['id']} to database")
        except Exception as e:
            logger.error(f"Error saving group to database: {e}")
    
    async def get_moderators(self, group_id: str, save_to_db: bool = False) -> List[Dict[str, Any]]:
        """Получить список модераторов группы"""
        async def operation():
            entity = await self.get_entity(group_id)
            
            moderators = []
            async for user in self.client.iter_participants(
                entity, 
                filter='admin'
            ):
                if isinstance(user, User):
                    mod = {
                        'telegram_id': str(user.id),
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_bot': user.bot,
                        'is_moderator': True,
                        'photo_url': None
                    }
                    moderators.append(mod)
                    
                    # Сохраняем в базу данных если требуется
                    if save_to_db:
                        await self._save_user_to_db(mod, group_id)
            
            logger.info(f"Retrieved {len(moderators)} moderators from group {group_id}")
            return moderators
            
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Error retrieving moderators from group {group_id}: {e}")
            raise
    
    async def _save_user_to_db(self, user_data: Dict[str, Any], group_id: str = None):
        """Сохранить или обновить информацию о пользователе в базе данных"""
        try:
            # Проверяем, есть ли уже такой пользователь в базе
            existing_user = supabase_client.table('telegram_users').select('id')\
                .eq('telegram_id', user_data['telegram_id']).execute()
            
            if not existing_user.data:
                # Создаем запись в базе
                supabase_client.table('telegram_users').insert(user_data).execute()
                logger.debug(f"Added new user {user_data['telegram_id']} to database")
            else:
                # Обновляем существующую запись
                user_id = existing_user.data[0]['id']
                supabase_client.table('telegram_users').update({
                    'username': user_data['username'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_bot': user_data.get('is_bot', False),
                    'is_moderator': user_data['is_moderator'],
                    'photo_url': user_data.get('photo_url')
                }).eq('id', user_id).execute()
                logger.debug(f"Updated user {user_data['telegram_id']} in database")
            
            # Если указан group_id, добавляем связь пользователя с группой
            if group_id:
                db_group = supabase_client.table('telegram_groups').select('id').eq('group_id', group_id).execute()
                if db_group.data:
                    db_group_id = db_group.data[0]['id']
                    db_user = supabase_client.table('telegram_users').select('id').eq('telegram_id', user_data['telegram_id']).execute()
                    
                    if db_user.data:
                        db_user_id = db_user.data[0]['id']
                        
                        # Проверяем, существует ли уже связь
                        existing_relation = supabase_client.table('user_group_relations').select('id')\
                            .eq('user_id', db_user_id)\
                            .eq('group_id', db_group_id).execute()
                        
                        if not existing_relation.data:
                            # Создаем связь
                            relation_data = {
                                'user_id': db_user_id,
                                'group_id': db_group_id,
                                'role': 'moderator' if user_data['is_moderator'] else 'user'
                            }
                            supabase_client.table('user_group_relations').insert(relation_data).execute()
                            logger.debug(f"Added user-group relation for user {user_data['telegram_id']} and group {group_id}")
        except Exception as e:
            logger.error(f"Error saving user to database: {e}")
    
    async def collect_group_data(self, group_id: str, messages_limit: int = 100) -> Dict[str, Any]:
        """Собрать все данные о группе и сохранить в базу"""
        try:
            # Получаем информацию о группе
            group_info = await self.get_group_info(group_id)
            
            # Получаем модераторов
            moderators = await self.get_moderators(group_id, save_to_db=True)
            
            # Получаем сообщения
            messages = await self.get_group_messages(group_id, limit=messages_limit, save_to_db=True)
            
            logger.info(f"Collected data for group {group_id}: {len(messages)} messages, {len(moderators)} moderators")
            
            return {
                'group': group_info,
                'moderators': moderators,
                'messages': messages
            }
        except Exception as e:
            logger.error(f"Error collecting data for group {group_id}: {e}")
            raise
    
    async def get_group_members(self, group_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить участников группы"""
        async def operation():
            entity = await self.get_entity(group_id)
            
            members = []
            async for user in self.client.iter_participants(entity, limit=limit):
                if isinstance(user, User):
                    member = {
                        'telegram_id': str(user.id),
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_bot': user.bot,
                        'is_moderator': False,  # По умолчанию не модератор
                        'date_joined': None  # Telegram API не предоставляет эту информацию напрямую
                    }
                    members.append(member)
            
            logger.info(f"Retrieved {len(members)} members from group {group_id}")
            return members
            
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Error retrieving members from group {group_id}: {e}")
            raise
    
    async def get_message_reactions(self, group_id: str, message_id: int) -> List[Dict[str, Any]]:
        """Получить реакции на сообщение"""
        async def operation():
            entity = await self.get_entity(group_id)
            
            # Получаем сообщение
            message = await self.client.get_messages(entity, ids=message_id)
            
            if not message or not hasattr(message, 'reactions'):
                return []
                
            reactions = []
            if message.reactions:
                for reaction in message.reactions.results:
                    reactions.append({
                        'emoji': reaction.reaction,
                        'count': reaction.count
                    })
            
            return reactions
            
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Error retrieving reactions for message {message_id} in group {group_id}: {e}")
            return []
    
    async def get_message_thread(self, group_id: str, message_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить ветку сообщений (ответы на конкретное сообщение)"""
        async def operation():
            entity = await self.get_entity(group_id)
            
            # Получаем сообщение
            thread_messages = []
            async for message in self.client.iter_messages(
                entity, 
                reply_to=message_id,
                limit=limit
            ):
                if isinstance(message, Message):
                    msg = {
                        'message_id': str(message.id),
                        'text': message.text or "",
                        'date': message.date.isoformat(),
                        'sender_id': str(message.sender_id) if message.sender_id else None,
                        'is_reply': True,
                        'reply_to_message_id': str(message_id)
                    }
                    thread_messages.append(msg)
            
            return thread_messages
            
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Error retrieving thread for message {message_id} in group {group_id}: {e}")
            return []

    async def get_entity(self, entity_id: str):
        """Исправленное получение сущности Telegram"""
        async def operation():
            try:
                # Сначала пробуем получить как есть
                return await self.client.get_entity(entity_id)
            except Exception as e1:
                logger.warning(f"Direct entity lookup failed: {e1}")
                
                # Если не получилось, пробуем разные форматы
                try:
                    # Убираем @ если есть
                    clean_id = entity_id.lstrip('@')
                    return await self.client.get_entity(clean_id)
                except Exception as e2:
                    logger.warning(f"Clean ID lookup failed: {e2}")
                    
                    # Пробуем как число если это возможно
                    try:
                        if str(entity_id).lstrip('-').isdigit():
                            numeric_id = int(entity_id)
                            return await self.client.get_entity(numeric_id)
                    except Exception as e3:
                        logger.warning(f"Numeric ID lookup failed: {e3}")
                        
                    # Если ничего не помогло, выбрасываем исходную ошибку
                    raise e1
        
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            raise ValueError(f"Entity {entity_id} not found or not accessible. Error: {str(e)}")
            
    async def generate_session_string(self, phone: str):
        """
        Генерация строки сессии для последующего использования
        Требует интерактивного ввода кода подтверждения
        """
        client = TelegramClient(
            StringSession(), 
            self.api_id,
            self.api_hash
        )
        
        try:
            await client.connect()
            await client.send_code_request(phone)
            
            # В реальном приложении здесь должен быть механизм получения кода от пользователя
            # Например, через веб-интерфейс или API endpoint
            code = input("Enter the code you received: ")
            await client.sign_in(phone, code)
            
            session_string = client.session.save()
            logger.info("Session string generated successfully")
            
            return session_string
        except Exception as e:
            logger.error(f"Error generating session string: {e}")
            raise
        finally:
            if client.is_connected():
                await client.disconnect()

    async def get_group_info_by_link(self, link_or_username: str) -> Dict[str, Any]:
        """Получить информацию о группе по ссылке или username"""
        async def operation():
            try:
                entity = await self.client.get_entity(link_or_username)
                
                group_info = {}
                
                if isinstance(entity, Channel) or isinstance(entity, Chat):
                    # Получаем базовую информацию о группе
                    group_info = {
                        'id': str(entity.id),
                        'title': getattr(entity, 'title', 'Unknown'),
                        'username': getattr(entity, 'username', None),
                        'description': getattr(entity, 'about', None) if hasattr(entity, 'about') else None,
                        'participants_count': getattr(entity, 'participants_count', None) if hasattr(entity, 'participants_count') else None,
                        'date': getattr(entity, 'date', datetime.now()).isoformat() if hasattr(entity, 'date') else datetime.now().isoformat(),
                        'is_public': bool(getattr(entity, 'username', None))
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
        
    async def _check_if_moderator(self, entity, user_id: str) -> bool:
        """Проверить, является ли пользователь модератором группы"""
        try:
            # Преобразуем user_id из строки в int
            user_id_int = int(user_id)
            
            # Получаем информацию о правах пользователя
            participant = await self.client.get_permissions(entity, user_id_int)
            
            # Проверяем права администратора
            return participant.is_admin
        except Exception as e:
            logger.warning(f"Failed to check if user {user_id} is moderator: {e}")
            return False
        
    async def get_conversation_threads(self, group_id: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Получить цепочки диалогов между пользователями и модераторами
        
        Args:
            group_id: ID группы
            days_back: За сколько дней назад получать сообщения
            
        Returns:
            Список цепочек диалогов
        """
        try:
            # Вычисляем дату, с которой начинать получение сообщений
            offset_date = datetime.now() - timedelta(days=days_back)
            
            # Получаем сообщения
            messages = await self.get_group_messages(
                group_id, 
                limit=500,  # Увеличиваем лимит для более полного анализа
                offset_date=offset_date,
                include_replies=True,
                get_users=True
            )
            
            # Организуем сообщения по цепочкам
            threads = {}
            standalone_messages = []
            
            # Сначала группируем сообщения по reply_to_message_id
            for msg in messages:
                if msg['is_reply'] and msg['reply_to_message_id']:
                    thread_id = msg['reply_to_message_id']
                    if thread_id not in threads:
                        threads[thread_id] = {
                            'root_message_id': thread_id,
                            'messages': []
                        }
                    threads[thread_id]['messages'].append(msg)
                else:
                    standalone_messages.append(msg)
            
            # Дополняем цепочки корневыми сообщениями
            for msg in standalone_messages:
                if msg['message_id'] in threads:
                    threads[msg['message_id']]['root_message'] = msg
            
            # Преобразуем в список и сортируем по дате
            thread_list = []
            for thread_id, thread in threads.items():
                if 'root_message' in thread:
                    # Добавляем дополнительную информацию о цепочке
                    thread['start_date'] = thread['root_message']['date']
                    thread['participants'] = set()
                    thread['moderator_involved'] = False
                    
                    # Добавляем отправителя корневого сообщения
                    if 'sender' in thread['root_message']:
                        thread['participants'].add(thread['root_message']['sender']['id'])
                        if thread['root_message']['sender'].get('is_moderator', False):
                            thread['moderator_involved'] = True
                    
                    # Добавляем отправителей ответов
                    for msg in thread['messages']:
                        if 'sender' in msg:
                            thread['participants'].add(msg['sender']['id'])
                            if msg['sender'].get('is_moderator', False):
                                thread['moderator_involved'] = True
                    
                    # Конвертируем set в list для сериализации
                    thread['participants'] = list(thread['participants'])
                    
                    # Вычисляем время первого ответа модератора
                    if thread['moderator_involved']:
                        thread['first_moderator_response_time'] = self._calculate_first_response_time(
                            thread['root_message'],
                            thread['messages']
                        )
                    
                    thread_list.append(thread)
            
            # Сортируем по дате начала, самые новые первыми
            thread_list.sort(key=lambda x: x['start_date'], reverse=True)
            
            return thread_list
        except Exception as e:
            logger.error(f"Error getting conversation threads for group {group_id}: {e}")
            raise

    def _calculate_first_response_time(self, root_message: Dict[str, Any], replies: List[Dict[str, Any]]) -> Optional[float]:
        """
        Вычислить время первого ответа модератора на сообщение
        
        Args:
            root_message: Корневое сообщение
            replies: Ответы на сообщение
            
        Returns:
            Время ответа в минутах или None, если ответа не было
        """
        # Проверяем, что корневое сообщение не от модератора
        if root_message.get('sender', {}).get('is_moderator', False):
            return None
        
        # Сортируем ответы по дате
        sorted_replies = sorted(replies, key=lambda x: x['date'])
        
        # Ищем первый ответ от модератора
        for reply in sorted_replies:
            if reply.get('sender', {}).get('is_moderator', False):
                # Преобразуем строки в datetime
                root_date = datetime.fromisoformat(root_message['date'].replace('Z', '+00:00'))
                reply_date = datetime.fromisoformat(reply['date'].replace('Z', '+00:00'))
                
                # Вычисляем разницу в минутах
                time_diff = (reply_date - root_date).total_seconds() / 60
                return time_diff
        
        return None
    
    async def prepare_data_for_analysis(self, group_id: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Подготовить данные для анализа
        
        Args:
            group_id: ID группы
            days_back: За сколько дней назад получать данные
            
        Returns:
            Словарь с данными для анализа
        """
        try:
            # Получаем информацию о группе
            group_info = await self.get_group_info(group_id)
            
            # Получаем модераторов
            moderators = await self.get_moderators(group_id, save_to_db=True)
            
            # Получаем цепочки диалогов
            threads = await self.get_conversation_threads(group_id, days_back)
            
            # Вычисляем метрики
            metrics = self._calculate_metrics(threads, moderators)
            
            # Формируем данные для анализа
            analysis_data = {
                'group': group_info,
                'period': {
                    'start_date': (datetime.now() - timedelta(days=days_back)).isoformat(),
                    'end_date': datetime.now().isoformat(),
                    'days': days_back
                },
                'moderators': moderators,
                'conversation_threads': threads,
                'metrics': metrics
            }
            
            return analysis_data
        except Exception as e:
            logger.error(f"Error preparing data for analysis for group {group_id}: {e}")
            raise

    def _calculate_metrics(self, threads: List[Dict[str, Any]], moderators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Вычислить метрики на основе данных о диалогах
        
        Args:
            threads: Цепочки диалогов
            moderators: Модераторы группы
            
        Returns:
            Словарь с метриками
        """
        # Инициализируем метрики
        metrics = {
            'total_threads': len(threads),
            'moderator_involved_threads': 0,
            'response_times': [],
            'response_time_avg': None,
            'response_time_min': None,
            'response_time_max': None,
            'moderator_activity': {},
            'thread_length_avg': 0
        }
        
        # Инициализируем данные по модераторам
        for mod in moderators:
            mod_id = mod['telegram_id']
            metrics['moderator_activity'][mod_id] = {
                'threads_participated': 0,
                'messages_sent': 0,
                'avg_response_time': None,
                'response_times': []
            }
        
        # Обрабатываем каждую цепочку
        total_messages = 0
        for thread in threads:
            # Считаем общее количество сообщений
            thread_messages = len(thread.get('messages', [])) + 1  # +1 для корневого сообщения
            total_messages += thread_messages
            
            # Если в цепочке участвовал модератор
            if thread.get('moderator_involved', False):
                metrics['moderator_involved_threads'] += 1
                
                # Добавляем время ответа, если есть
                response_time = thread.get('first_moderator_response_time')
                if response_time is not None:
                    metrics['response_times'].append(response_time)
                    
                    # Обновляем статистику по каждому модератору
                    for msg in thread.get('messages', []):
                        if msg.get('sender', {}).get('is_moderator', False):
                            mod_id = msg['sender']['id']
                            if mod_id in metrics['moderator_activity']:
                                metrics['moderator_activity'][mod_id]['threads_participated'] += 1
                                metrics['moderator_activity'][mod_id]['messages_sent'] += 1
                                
                                # Вычисляем время ответа для конкретного модератора
                                if 'replied_message' in msg:
                                    root_date = datetime.fromisoformat(msg['replied_message']['date'].replace('Z', '+00:00'))
                                    msg_date = datetime.fromisoformat(msg['date'].replace('Z', '+00:00'))
                                    mod_response_time = (msg_date - root_date).total_seconds() / 60
                                    metrics['moderator_activity'][mod_id]['response_times'].append(mod_response_time)
        
        # Вычисляем среднюю длину цепочки
        if metrics['total_threads'] > 0:
            metrics['thread_length_avg'] = total_messages / metrics['total_threads']
        
        # Вычисляем статистику по времени ответа
        if metrics['response_times']:
            metrics['response_time_avg'] = sum(metrics['response_times']) / len(metrics['response_times'])
            metrics['response_time_min'] = min(metrics['response_times'])
            metrics['response_time_max'] = max(metrics['response_times'])
        
        # Вычисляем среднее время ответа для каждого модератора
        for mod_id, activity in metrics['moderator_activity'].items():
            if activity['response_times']:
                activity['avg_response_time'] = sum(activity['response_times']) / len(activity['response_times'])
        
        return metrics
    
    
    async def connect_with_retry(self, max_retries: int = 3):
        """Подключение к Telegram с повторными попытками и диагностикой"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to Telegram (attempt {attempt + 1}/{max_retries})")
                
                # Проверяем конфигурацию
                if not self.api_id or not self.api_hash:
                    raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured")
                
                if not self.session_string:
                    raise ValueError("TELEGRAM_SESSION_STRING must be configured")
                
                # Логируем конфигурацию (без раскрытия секретов)
                logger.info(f"API ID configured: {bool(self.api_id)}")
                logger.info(f"API Hash configured: {bool(self.api_hash)}")
                logger.info(f"Session string length: {len(self.session_string)}")
                
                # Подключаемся
                if not self.client.is_connected():
                    await self.client.connect()
                    logger.info("Connected to Telegram servers")
                
                # Проверяем авторизацию
                if not await self.client.is_user_authorized():
                    logger.error("User is not authorized. Session string might be invalid or expired.")
                    raise ValueError("User is not authorized. Please regenerate session string.")
                
                # Получаем информацию о текущем пользователе для проверки
                me = await self.client.get_me()
                logger.info(f"Successfully authenticated as: {me.first_name} (@{me.username})")
                
                self.is_connected = True
                return True
                
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == max_retries - 1:
                    logger.error("All connection attempts failed")
                    self.is_connected = False
                    raise
                
                # Ждем перед следующей попыткой
                await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
        
        return False
    

    async def disconnect(self):
        """Безопасное отключение"""
        try:
            if hasattr(self, 'client') and self.client and self.client.is_connected():
                await self.client.disconnect()
                logger.info("Disconnected from Telegram")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self.is_connected = False

        
    async def health_check(self):
        """Проверка здоровья Telegram соединения"""
        try:
            await self.ensure_connected_with_diagnostics()
            
            # Простая операция для проверки работоспособности
            me = await self.client.get_me()
            
            return {
                "status": "healthy",
                "connected": True,
                "user_id": str(me.id),
                "username": me.username,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
    
    async def parse_post_links(self, post_links: List[str]) -> List[Dict[str, Any]]:
        """
        Парсинг ссылок на посты и получение их ID
        
        Args:
            post_links: Список ссылок на посты (t.me/channel/123 или t.me/c/1234567890/456)
            
        Returns:
            Список словарей с информацией о постах
        """
        parsed_posts = []
        
        for link in post_links:
            try:
                post_info = self._parse_telegram_post_link(link.strip())
                if post_info:
                    parsed_posts.append(post_info)
                else:
                    logger.warning(f"Failed to parse post link: {link}")
            except Exception as e:
                logger.error(f"Error parsing post link {link}: {e}")
        
        return parsed_posts  
    

    def _parse_telegram_post_link(self, link: str) -> Optional[Dict[str, Any]]:
        """
        Парсинг одной ссылки на пост Telegram
        
        Поддерживаемые форматы:
        - https://t.me/channel_name/123
        - https://t.me/c/1234567890/456
        - t.me/channel_name/123
        """
        try:
            # Убираем лишние пробелы и приводим к нижнему регистру
            link = link.strip()
            
            # Добавляем https:// если отсутствует
            if not link.startswith(('http://', 'https://')):
                link = 'https://' + link
            
            parsed_url = urlparse(link)
            
            if parsed_url.netloc != 't.me':
                return None
            
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                return None
            
            # Формат: /c/channel_id/message_id (приватные каналы)
            if path_parts[0] == 'c' and len(path_parts) >= 3:
                channel_id = f"-100{path_parts[1]}"  # Добавляем префикс для супергрупп
                message_id = int(path_parts[2])
                
                return {
                    'channel_id': channel_id,
                    'message_id': message_id,
                    'link': link,
                    'is_private': True
                }
            
            # Формат: /channel_name/message_id (публичные каналы)
            elif len(path_parts) == 2:
                channel_username = path_parts[0]
                message_id = int(path_parts[1])
                
                return {
                    'channel_username': channel_username,
                    'message_id': message_id,
                    'link': link,
                    'is_private': False
                }
            
            return None
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing post link {link}: {e}")
            return None
    

    async def get_post_comments(self, post_info: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получить комментарии к посту
        
        Args:
            post_info: Информация о посте из parse_post_links
            limit: Максимальное количество комментариев
            
        Returns:
            Список комментариев
        """
        async def operation():
            try:
                # Получаем entity канала/группы
                if post_info['is_private']:
                    entity = await self.client.get_entity(int(post_info['channel_id']))
                else:
                    entity = await self.client.get_entity(post_info['channel_username'])
                
                # Получаем сам пост
                post_message = await self.client.get_messages(entity, ids=post_info['message_id'])
                
                if not post_message:
                    logger.warning(f"Post {post_info['message_id']} not found")
                    return []
                
                # Получаем комментарии (replies) к посту
                comments = []
                
                # Проверяем есть ли комментарии у поста
                if hasattr(post_message, 'replies') and post_message.replies:
                    
                    async for message in self.client.iter_messages(
                        entity, 
                        reply_to=post_info['message_id'],
                        limit=limit
                    ):
                        if isinstance(message, Message) and message.text:
                            # Получаем информацию об авторе комментария
                            author_info = None
                            if message.sender_id:
                                try:
                                    user = await self.client.get_entity(message.sender_id)
                                    author_info = {
                                        'id': str(user.id),
                                        'username': getattr(user, 'username', None),
                                        'first_name': getattr(user, 'first_name', None),
                                        'last_name': getattr(user, 'last_name', None)
                                    }
                                except:
                                    pass
                            
                            comment_data = {
                                'message_id': str(message.id),
                                'text': message.text,
                                'date': message.date.isoformat(),
                                'author': author_info,
                                'post_link': post_info['link'],
                                'post_message_id': str(post_info['message_id']),
                                'has_media': bool(message.media),
                                'is_reply': True,
                                'reply_to_message_id': str(post_info['message_id'])
                            }
                            
                            comments.append(comment_data)
                
                logger.info(f"Retrieved {len(comments)} comments for post {post_info['message_id']}")
                return comments
                
            except Exception as e:
                logger.error(f"Error getting comments for post {post_info}: {e}")
                return []
        
        try:
            return await self.execute_telegram_operation(operation)
        except Exception as e:
            logger.error(f"Failed to get comments for post {post_info}: {e}")
            return []
        
    async def get_multiple_posts_comments(self, post_links: List[str], limit_per_post: int = 100) -> Dict[str, Any]:
        """
        Получить комментарии к нескольким постам
        
        Args:
            post_links: Список ссылок на посты
            limit_per_post: Максимальное количество комментариев на пост
            
        Returns:
            Словарь с комментариями и метаинформацией
        """
        try:
            # Парсим ссылки на посты
            parsed_posts = await self.parse_post_links(post_links)
            
            if not parsed_posts:
                return {
                    'comments': [],
                    'posts_info': [],
                    'total_comments': 0,
                    'processed_posts': 0
                }
            
            all_comments = []
            posts_info = []
            
            for post_info in parsed_posts:
                try:
                    # Получаем комментарии к каждому посту
                    post_comments = await self.get_post_comments(post_info, limit_per_post)
                    
                    # Добавляем информацию о посте к каждому комментарию
                    for comment in post_comments:
                        comment['source_post'] = post_info
                    
                    all_comments.extend(post_comments)
                    posts_info.append({
                        'post_info': post_info,
                        'comments_count': len(post_comments)
                    })
                    
                    logger.info(f"Processed post {post_info['message_id']}: {len(post_comments)} comments")
                    
                except Exception as e:
                    logger.error(f"Error processing post {post_info}: {e}")
                    posts_info.append({
                        'post_info': post_info,
                        'comments_count': 0,
                        'error': str(e)
                    })
            
            result = {
                'comments': all_comments,
                'posts_info': posts_info,
                'total_comments': len(all_comments),
                'processed_posts': len([p for p in posts_info if 'error' not in p])
            }
            
            logger.info(f"Retrieved total {len(all_comments)} comments from {len(parsed_posts)} posts")
            return result
            
        except Exception as e:
            logger.error(f"Error getting multiple posts comments: {e}")
            return {
                'comments': [],
                'posts_info': [],
                'total_comments': 0,
                'processed_posts': 0
            }
        
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
        