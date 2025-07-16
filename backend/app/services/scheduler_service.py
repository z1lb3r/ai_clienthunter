# backend/app/services/scheduler_service.py
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any 

from ..core.database import supabase_client
from ..core.config import settings
from .client_monitoring_service import ClientMonitoringService

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.monitoring_service = ClientMonitoringService()
        self.task = None
        self.running = False
        self.background_tasks = set()  # Сохраняем strong references
        
    async def start(self):
        """Запустить планировщик"""
        try:
            if self.running:
                logger.warning("Scheduler already running")
                return
                
            logger.info("Starting scheduler service")
            
            # Создаем asyncio task для мониторинга
            self.task = asyncio.create_task(self._monitoring_loop())
            
            # Сохраняем strong reference
            self.background_tasks.add(self.task)
            self.task.add_done_callback(self.background_tasks.discard)
            
            self.running = True
            logger.info("Scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise
    
    async def stop(self):
        """Остановить планировщик"""
        try:
            if not self.running:
                logger.info("Scheduler already stopped")
                return
                
            logger.info("Stopping scheduler")
            self.running = False
            
            if self.task and not self.task.done():
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Scheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            raise
    
    async def _monitoring_loop(self):
        """Основной цикл планировщика"""
        logger.info("Scheduler monitoring loop started")
        
        iteration_count = 0
        
        try:
            while self.running:
                iteration_count += 1
                
                if settings.ENABLE_DEBUG_LOGGING:
                    logger.debug(f"Scheduler iteration #{iteration_count}")
                
                # Проверяем всех пользователей
                await self._monitor_all_users()
                
                # Ждем 60 секунд до следующей проверки
                if self.running:  # Проверяем перед сном
                    await asyncio.sleep(60)
                    
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
        finally:
            logger.info("Scheduler monitoring loop ended")
    
    async def _monitor_all_users(self):
        """Проверить всех пользователей на необходимость мониторинга"""
        try:
            logger.info("🔍 Начинаем проверку пользователей")
            
            # Получаем всех пользователей с активным мониторингом
            active_users = await self._get_active_monitoring_users()
            
            if not active_users:
                logger.info("❌ Нет активных пользователей для мониторинга")
                return
            
            logger.info(f"👥 Найдено {len(active_users)} активных пользователей")
    
            for user_data in active_users:
                try:
                    logger.info(f"📋 ОБРАБАТЫВАЕМ пользователя: {user_data}")
                    
                    user_id = user_data['user_id']
                    user_settings_data = user_data
                    
                    logger.info(f"👤 Проверяем пользователя {user_id}")
                    
                    # Проверяем, пора ли запускать мониторинг для этого пользователя
                    should_run = self._should_run_monitoring(user_settings_data)
                    logger.info(f"⏰ Результат проверки времени для пользователя {user_id}: {should_run}")
                    
                    if should_run:
                        logger.info(f"🚀 ЗАПУСКАЕМ мониторинг для пользователя {user_id}")
                        
                        # Запускаем мониторинг
                        await self._run_monitoring_for_user(user_id, user_settings_data)
                        
                        # Обновляем время последней проверки
                        await self._update_last_monitoring_check(user_id)
                        
                        logger.info(f"✅ Мониторинг для пользователя {user_id} завершен")
                    else:
                        logger.info(f"⏸️ НЕ ЗАПУСКАЕМ мониторинг для пользователя {user_id} - время еще не пришло")
                        
                except Exception as user_error:
                    logger.error(f"💥 Ошибка обработки пользователя {user_data.get('user_id', 'unknown')}: {user_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"💥 КРИТИЧЕСКАЯ ошибка в monitor_all_users: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    
    async def _get_active_monitoring_users(self) -> List[Dict[str, Any]]:
        """Получить пользователей с активным мониторингом"""
        try:
            result = supabase_client.table('monitoring_settings').select('*').eq('is_active', True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting active monitoring users: {e}")
            return []
    
    def _should_run_monitoring(self, user_settings: Dict[str, Any]) -> bool:  # ← ПЕРЕИМЕНОВАНО ПАРАМЕТР
        """Определить, нужно ли запускать мониторинг для пользователя"""
        try:
            last_check = user_settings.get('last_monitoring_check')  # ← ИСПРАВЛЕНО
            if not last_check:
                return True  # Первый запуск
            
            # Парсим время последней проверки
            last_check_time = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            
            # Проверяем, прошло ли достаточно времени
            time_diff = current_time - last_check_time
            check_interval = 5 * 60  # 5 минут по умолчанию
            
            should_run = time_diff.total_seconds() >= check_interval
            
            if settings.ENABLE_DEBUG_LOGGING:  # ← ТЕПЕРЬ РАБОТАЕТ ПРАВИЛЬНО
                logger.debug(f"Time since last check: {time_diff.total_seconds()}s, should run: {should_run}")
            
            return should_run
            
        except Exception as e:
            logger.error(f"Error determining if should run monitoring: {e}")
            return False
    
    async def _run_monitoring_for_user(self, user_id: int, user_settings: Dict[str, Any]):  # ← ПЕРЕИМЕНОВАНО ПАРАМЕТР
        """Запустить мониторинг для конкретного пользователя"""
        try:
            await self.monitoring_service.search_and_analyze(user_id, user_settings)  # ← ИСПРАВЛЕНО
        except Exception as e:
            logger.error(f"Error running monitoring for user {user_id}: {e}")
    
    async def _update_last_monitoring_check(self, user_id: int):
        """Обновить время последней проверки мониторинга"""
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            
            supabase_client.table('monitoring_settings').update({
                'last_monitoring_check': current_time,
                'updated_at': current_time
            }).eq('user_id', user_id).execute()
            
            if settings.ENABLE_DEBUG_LOGGING:  # ← ТЕПЕРЬ РАБОТАЕТ ПРАВИЛЬНО
                logger.debug(f"Updated last monitoring check for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error updating last monitoring check for user {user_id}: {e}")

# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()