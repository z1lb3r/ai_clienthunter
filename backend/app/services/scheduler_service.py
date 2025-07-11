# backend/app/services/scheduler_service.py
import asyncio
import logging
from datetime import datetime, timezone

from ..core.database import supabase_client
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
                logger.warning("⚠️ SCHEDULER: Already running")
                return
                
            print("🚀 SCHEDULER: Starting scheduler with asyncio approach...")
            logger.info("🚀 SCHEDULER: Starting scheduler with asyncio approach...")
            
            # Создаем asyncio task для мониторинга
            print("📋 SCHEDULER: Creating asyncio task...")
            self.task = asyncio.create_task(self._monitoring_loop())
            print(f"📋 SCHEDULER: Task created: {self.task}")
            
            # ← КРИТИЧЕСКИ ВАЖНО: Сохраняем strong reference
            self.background_tasks.add(self.task)
            print("📋 SCHEDULER: Task added to background_tasks set")
            
            # Удаляем task из set после завершения
            self.task.add_done_callback(self.background_tasks.discard)
            
            self.running = True
            print("✅ SCHEDULER: self.running = True")
            
            print("✅ SCHEDULER: Scheduler started successfully")
            logger.info("✅ SCHEDULER: Scheduler started successfully")
            
        except Exception as e:
            print(f"❌ SCHEDULER: Error starting scheduler: {e}")
            logger.error(f"❌ SCHEDULER: Error starting scheduler: {e}")
            import traceback
            logger.error(f"❌ SCHEDULER: Traceback: {traceback.format_exc()}")
            raise
    
    async def stop(self):
        """Остановить планировщик"""
        try:
            if not self.running:
                logger.info("ℹ️ SCHEDULER: Already stopped")
                return
                
            print("🛑 SCHEDULER: Stopping scheduler...")
            logger.info("🛑 SCHEDULER: Stopping scheduler...")
            self.running = False
            
            if self.task and not self.task.done():
                self.task.cancel()
                try:
                    # Ждем завершения task с timeout
                    await asyncio.wait_for(self.task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("⏰ SCHEDULER: Task cancellation timeout")
                except asyncio.CancelledError:
                    logger.info("✅ SCHEDULER: Task cancelled successfully")
                
            # Очищаем background tasks
            self.background_tasks.clear()
            
            print("✅ SCHEDULER: Scheduler stopped successfully")
            logger.info("✅ SCHEDULER: Scheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ SCHEDULER: Error stopping scheduler: {e}")
    
    async def _monitoring_loop(self):
        """Основной цикл мониторинга (запускается каждую минуту)"""
        print("🚀 SCHEDULER: Monitoring loop started")
        logger.info("🚀 SCHEDULER: Monitoring loop started")
        
        iteration_count = 0
        
        while self.running:
            iteration_count += 1
            print(f"🔄 SCHEDULER: Loop iteration #{iteration_count} started (running={self.running})")
            
            try:
                print("📞 SCHEDULER: Calling _monitor_all_users()...")
                # Выполняем мониторинг
                await self._monitor_all_users()
                print("✅ SCHEDULER: _monitor_all_users() completed successfully")
                
            except asyncio.CancelledError:
                print("📴 SCHEDULER: Monitoring loop cancelled")
                logger.info("📴 SCHEDULER: Monitoring loop cancelled")
                break
            except Exception as e:
                print(f"❌ SCHEDULER: Error in monitoring loop: {e}")
                logger.error(f"❌ SCHEDULER: Error in monitoring loop: {e}")
                import traceback
                logger.error(f"❌ SCHEDULER: Traceback: {traceback.format_exc()}")
                
                print("⏳ SCHEDULER: Waiting 30 seconds after error...")
                # При ошибке ждем 30 секунд и продолжаем
                await asyncio.sleep(30)
                print("⏰ SCHEDULER: 30 second wait completed")
                continue
            
            # Ждем 60 секунд до следующей проверки
            print("💤 SCHEDULER: Starting 60 second sleep...")
            await asyncio.sleep(60)
            print("⏰ SCHEDULER: 60 second sleep completed, next iteration...")
            
        print("🔚 SCHEDULER: Monitoring loop ended")
        logger.info("🔚 SCHEDULER: Monitoring loop ended")
    
    async def _monitor_all_users(self):
        """Проверить всех пользователей на необходимость мониторинга"""
        try:
            print("🔍 SCHEDULER: Running scheduled client monitoring check")
            logger.info("🔍 SCHEDULER: Running scheduled client monitoring check")
            
            # Получаем всех пользователей с активным мониторингом
            print("📊 SCHEDULER: Getting active monitoring users...")
            active_users = await self._get_active_monitoring_users()
            print(f"📊 SCHEDULER: Retrieved {len(active_users)} users from database")
            
            if not active_users:
                print("❌ SCHEDULER: No active monitoring users found")
                logger.warning("❌ SCHEDULER: No active monitoring users found")
                return
            
            logger.info(f"✅ SCHEDULER: Found {len(active_users)} active monitoring users")
            
            for user_data in active_users:
                user_id = user_data['user_id']
                settings = user_data
                
                print(f"🔍 SCHEDULER: Checking monitoring for user {user_id}")
                logger.info(f"🔍 SCHEDULER: Checking monitoring for user {user_id}")
                
                # Проверяем, пора ли запускать мониторинг для этого пользователя
                should_run = self._should_run_monitoring(settings)
                print(f"🎯 SCHEDULER: Should run monitoring for user {user_id}: {should_run}")
                logger.info(f"🎯 SCHEDULER: Should run monitoring for user {user_id}: {should_run}")
                
                if should_run:
                    print(f"🚀 SCHEDULER: Running monitoring for user {user_id}")
                    logger.info(f"🚀 SCHEDULER: Running monitoring for user {user_id}")
                    
                    # Запускаем мониторинг
                    await self._run_monitoring_for_user(user_id, settings)
                    print(f"✅ SCHEDULER: Monitoring for user {user_id} completed")
                else:
                    print(f"⏰ SCHEDULER: Skipping monitoring for user {user_id} - too early")
                    logger.info(f"⏰ SCHEDULER: Skipping monitoring for user {user_id} - too early")
                    
        except Exception as e:
            print(f"❌ SCHEDULER: Error in scheduled monitoring: {e}")
            logger.error(f"❌ SCHEDULER: Error in scheduled monitoring: {e}")
            import traceback
            logger.error(f"❌ SCHEDULER: Traceback: {traceback.format_exc()}")
    
    async def _get_active_monitoring_users(self) -> list:
        """Получить всех пользователей с активными шаблонами"""
        try:
            print("📊 SCHEDULER: Querying database for users with active templates")
            logger.info("📊 SCHEDULER: Querying database for users with active templates")
            
            # НОВАЯ ЛОГИКА: Читаем активные product_templates вместо monitoring_settings
            result = supabase_client.table('product_templates').select('user_id').eq('is_active', True).execute()
            
            if not result.data:
                print("📊 SCHEDULER: No active templates found")
                logger.info("📊 SCHEDULER: No active templates found")
                return []
                
            # Получаем уникальные user_id с активными шаблонами
            unique_user_ids = list(set([template['user_id'] for template in result.data]))
            
            print(f"📊 SCHEDULER: Found {len(unique_user_ids)} users with active templates")
            logger.info(f"📊 SCHEDULER: Found {len(unique_user_ids)} users with active templates")
            
            # Формируем список пользователей для мониторинга
            users = []
            for user_id in unique_user_ids:
                # Получаем глобальные настройки пользователя
                settings_result = supabase_client.table('monitoring_settings').select('*').eq('user_id', user_id).execute()
                
                if settings_result.data:
                    settings = settings_result.data[0]
                    # Проверяем что глобальный мониторинг включен
                    if settings.get('is_active', False):
                        users.append({
                            'user_id': user_id,
                            'notification_account': settings.get('notification_account', ''),
                            'is_active': True,
                            'last_monitoring_check': settings.get('last_monitoring_check')
                        })
                        print(f"👤 SCHEDULER: User {user_id} - global monitoring ACTIVE")
                    else:
                        print(f"👤 SCHEDULER: User {user_id} - global monitoring DISABLED")
                else:
                    print(f"👤 SCHEDULER: User {user_id} - no global settings found")
            
            print(f"📊 SCHEDULER: Database returned {len(users)} users with active monitoring")
            logger.info(f"📊 SCHEDULER: Retrieved {len(users)} users with active monitoring")
            
            return users
        
        except Exception as e:
            print(f"❌ SCHEDULER: Error getting users with active templates: {e}")
            logger.error(f"❌ SCHEDULER: Error getting users with active templates: {e}")
            return []
    
    def _should_run_monitoring(self, settings: dict) -> bool:
        """Проверить, нужно ли запускать мониторинг для пользователя"""
        try:
            last_check = settings.get('last_monitoring_check')
            interval_minutes = 5
            
            print(f"⏰ SCHEDULER: Checking interval - last_check: {last_check}, interval: {interval_minutes}min")
            logger.info(f"⏰ SCHEDULER: Checking interval - last_check: {last_check}, interval: {interval_minutes}min")
            
            if not last_check:
                print("⏰ SCHEDULER: No last check time, running monitoring")
                logger.info("⏰ SCHEDULER: No last check time, running monitoring")
                return True
            
            # Обрабатываем время с учетом timezone
            try:
                # Парсим время из БД (может быть с timezone)
                if isinstance(last_check, str):
                    # Убираем Z и заменяем на +00:00 если есть
                    time_str = last_check.replace('Z', '+00:00')
                    last_check_time = datetime.fromisoformat(time_str)
                else:
                    last_check_time = last_check
                
                # Приводим к UTC если есть timezone info
                if last_check_time.tzinfo is not None:
                    last_check_utc = last_check_time.astimezone(timezone.utc)
                else:
                    # Если timezone нет, считаем что это UTC
                    last_check_utc = last_check_time.replace(tzinfo=timezone.utc)
                
                # Текущее время в UTC
                now_utc = datetime.now(timezone.utc)
                
                # Вычисляем разницу в минутах
                time_diff_minutes = (now_utc - last_check_utc).total_seconds() / 60
                
                print(f"⏰ SCHEDULER: Time difference: {time_diff_minutes:.1f} minutes (need {interval_minutes})")
                logger.info(f"⏰ SCHEDULER: Time difference: {time_diff_minutes:.1f} minutes (need {interval_minutes})")
                
                if time_diff_minutes >= interval_minutes:
                    print("✅ SCHEDULER: Interval elapsed, running monitoring")
                    logger.info("✅ SCHEDULER: Interval elapsed, running monitoring")
                    return True
                else:
                    print(f"⏳ SCHEDULER: Too early, need to wait {interval_minutes - time_diff_minutes:.1f} more minutes")
                    logger.info(f"⏳ SCHEDULER: Too early, need to wait {interval_minutes - time_diff_minutes:.1f} more minutes")
                    return False
                    
            except Exception as time_error:
                print(f"⚠️ SCHEDULER: Error parsing time, running monitoring anyway: {time_error}")
                logger.warning(f"⚠️ SCHEDULER: Error parsing time, running monitoring anyway: {time_error}")
                return True
            
        except Exception as e:
            print(f"❌ SCHEDULER: Error checking if should run monitoring: {e}")
            logger.error(f"❌ SCHEDULER: Error checking if should run monitoring: {e}")
            # При ошибке все равно запускаем мониторинг
            return True
    
    async def _run_monitoring_for_user(self, user_id: int, settings: dict):
        """Запустить мониторинг для конкретного пользователя"""
        try:
            print(f"🚀 SCHEDULER: Starting monitoring execution for user {user_id}")
            logger.info(f"🚀 SCHEDULER: Starting monitoring execution for user {user_id}")
            
            # Обновляем время последней проверки в начале
            await self._update_last_check_time(user_id)
            
            # НОВАЯ ЛОГИКА: Получаем активные шаблоны пользователя
            templates = await self._get_user_templates(user_id)
            if not templates:
                print(f"❌ SCHEDULER: No active product templates found for user {user_id}")
                logger.warning(f"❌ SCHEDULER: No active product templates found for user {user_id}")
                return
            
            print(f"📝 SCHEDULER: Found {len(templates)} active templates for user {user_id}")
            logger.info(f"📝 SCHEDULER: Found {len(templates)} active templates for user {user_id}")
            
            # НОВАЯ ЛОГИКА: Обрабатываем каждый шаблон отдельно
            for template in templates:
                template_name = template.get('name', f'Template {template.get("id")}')
                chat_ids = template.get('chat_ids', [])
                
                if not chat_ids:
                    print(f"⚠️ SCHEDULER: Template '{template_name}' has no chat_ids - skipping")
                    continue
                    
                print(f"📝 SCHEDULER: Processing template '{template_name}' with {len(chat_ids)} chats")
                
                # Подготавливаем настройки для этого шаблона
                template_settings = {
                    'notification_account': settings.get('notification_account', ''),
                    'chat_ids': chat_ids,  # ВАЖНО: используем chat_ids
                    'check_interval_minutes': template.get('check_interval_minutes', 5),
                    'lookback_minutes': template.get('lookback_minutes', 60),
                    'min_ai_confidence': template.get('min_ai_confidence', 7),
                    'is_active': True
                }
                
                # Запускаем поиск и анализ для этого шаблона
                print(f"🔎 SCHEDULER: Calling _search_and_analyze for template '{template_name}'")
                await self.monitoring_service._search_and_analyze_template(user_id, template, template_settings)
                print(f"✅ SCHEDULER: _search_and_analyze completed for template '{template_name}'")
            
            logger.info(f"✅ SCHEDULER: Monitoring execution completed for user {user_id}")
            
        except Exception as e:
            print(f"❌ SCHEDULER: Error running monitoring for user {user_id}: {e}")
            logger.error(f"❌ SCHEDULER: Error running monitoring for user {user_id}: {e}")
            import traceback
            logger.error(f"❌ SCHEDULER: Traceback: {traceback.format_exc()}")
        
    async def _update_last_check_time(self, user_id: int):
        """Обновить время последней проверки"""
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            
            supabase_client.table('monitoring_settings').update({
                'last_monitoring_check': current_time
            }).eq('user_id', user_id).execute()
            
            print(f"🕐 SCHEDULER: Updated last check time for user {user_id} to {current_time}")
            logger.info(f"🕐 SCHEDULER: Updated last check time for user {user_id} to {current_time}")
            
        except Exception as e:
            print(f"❌ SCHEDULER: Error updating last check time for user {user_id}: {e}")
            logger.error(f"❌ SCHEDULER: Error updating last check time for user {user_id}: {e}")
    
    async def _get_user_templates(self, user_id: int) -> list:
        """Получить активные шаблоны пользователя"""
        try:
            result = supabase_client.table('product_templates').select('*').eq('user_id', user_id).eq('is_active', True).execute()
            
            templates = result.data or []
            print(f"📝 SCHEDULER: Retrieved {len(templates)} active templates for user {user_id}")
            logger.info(f"📝 SCHEDULER: Retrieved {len(templates)} active templates for user {user_id}")
            return templates
            
        except Exception as e:
            print(f"❌ SCHEDULER: Error getting user templates for user {user_id}: {e}")
            logger.error(f"❌ SCHEDULER: Error getting user templates for user {user_id}: {e}")
            return []

    @property
    def scheduler(self):
        """Совместимость с health check - эмулируем APScheduler"""
        class FakeScheduler:
            def __init__(self, running):
                self.running = running
        
        return FakeScheduler(self.running)

# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()