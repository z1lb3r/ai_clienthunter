# 23062025

from openai import AsyncOpenAI
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def analyze_moderator_performance(
        self,
        messages: List[Dict[str, Any]],
        prompt: str,
        moderators: List[str] = None,
        group_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Анализ эффективности модераторов через OpenAI
        
        Args:
            messages: Список сообщений из группы
            prompt: Критерии оценки от пользователя
            moderators: Список модераторов для анализа
            group_name: Название группы
            
        Returns:
            Результат анализа в структурированном виде
        """
        try:
            # Подготавливаем данные для анализа
            analysis_data = self._prepare_analysis_data(messages, moderators)
            
            # Формируем системный промпт
            system_prompt = self._build_system_prompt()
            
            # Формируем пользовательский промпт
            user_prompt = self._build_user_prompt(
                analysis_data, prompt, group_name, moderators
            )
            
            # Отправляем запрос к OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=8000
            )
            
            # Парсим ответ
            result = self._parse_openai_response(response.choices[0].message.content)


            if 'main_issues' in result and result['main_issues']:
                result['main_issues'] = self._filter_significant_issues(
                    result['main_issues'], 
                    len(messages),
                    min_percentage=7.0
                )

            logger.info(f"Successfully analyzed {len(messages)} messages for group {group_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error in OpenAI analysis: {str(e)}")
            # Возвращаем fallback результат в случае ошибки
            return self._get_fallback_result()
    
    def _prepare_analysis_data(self, messages: List[Dict[str, Any]], moderators: List[str]) -> Dict[str, Any]:
        """Подготовка данных сообщений для анализа"""
        
        # Фильтруем сообщения модераторов если указаны
        moderator_messages = []
        user_messages = []
        
        for msg in messages:
            sender_username = msg.get('sender', {}).get('username', '')
            is_moderator = any(mod.strip('@') in sender_username for mod in moderators) if moderators else False
            
            message_data = {
                'id': msg['message_id'],
                'text': msg['text'][:500],  # Ограничиваем длину для экономии токенов
                'date': msg['date'],
                'is_reply': msg['is_reply'],
                'has_media': msg['has_media']
            }
            
            if is_moderator:
                moderator_messages.append(message_data)
            else:
                user_messages.append(message_data)
        
        return {
            'moderator_messages': moderator_messages[:20],  # Ограничиваем количество
            'user_messages': user_messages[:30],
            'total_messages': len(messages),
            'moderator_count': len(moderator_messages),
            'conversation_threads': self._identify_threads(messages)
        }
    
    def _identify_threads(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Определение цепочек диалогов"""
        threads = []
        
        # Группируем сообщения по reply_to_message_id
        for msg in messages[:10]:  # Анализируем только последние 10 для экономии
            if msg['is_reply'] and msg['reply_to_message_id']:
                # Ищем исходное сообщение
                original_msg = next((m for m in messages if m['message_id'] == msg['reply_to_message_id']), None)
                if original_msg:
                    threads.append({
                        'original': {
                            'text': original_msg['text'][:200],
                            'date': original_msg['date']
                        },
                        'reply': {
                            'text': msg['text'][:200],
                            'date': msg['date']
                        }
                    })
        
        return threads[:5]  # Максимум 5 цепочек
    
    def _build_system_prompt(self) -> str:
        """Системный промпт для анализа модераторов"""
        return """Ты - эксперт по анализу коммуникаций в онлайн-сообществах. 
        Твоя задача - оценить эффективность работы модераторов на основе их сообщений и взаимодействий с пользователями.

        Анализируй по следующим критериям:
        1. Скорость ответа на вопросы пользователей
        2. Качество и полезность ответов
        3. Тон общения (дружелюбность, профессионализм)
        4. Решение конфликтов и проблем
        5. Соблюдение правил сообщества

        Верни результат СТРОГО в формате JSON:
        {
            "summary": {
                "sentiment_score": number (0-100),
                "response_time_avg": number (минуты),
                "resolved_issues": number,
                "satisfaction_score": number (0-100),
                "engagement_rate": number (0-100)
            },
            "moderator_metrics": {
                "response_time": {"avg": number, "min": number, "max": number},
                "sentiment": {"positive": number, "neutral": number, "negative": number},
                "performance": {"effectiveness": number, "helpfulness": number, "clarity": number}
            },
            "key_topics": [string],
            "recommendations": [string]
        }"""
    
    def _build_user_prompt(self, data: Dict[str, Any], user_prompt: str, group_name: str, moderators: List[str]) -> str:
        """Пользовательский промпт с данными для анализа"""
        
        prompt = f"""
        ГРУППА: {group_name}
        МОДЕРАТОРЫ ДЛЯ АНАЛИЗА: {', '.join(moderators) if moderators else 'Все'}
        
        КРИТЕРИИ ОЦЕНКИ:
        {user_prompt}
        
        ДАННЫЕ ДЛЯ АНАЛИЗА:
        - Всего сообщений: {data['total_messages']}
        - Сообщений от модераторов: {data['moderator_count']}
        - Цепочек диалогов: {len(data['conversation_threads'])}
        
        СООБЩЕНИЯ МОДЕРАТОРОВ:
        """
        
        for i, msg in enumerate(data['moderator_messages'][:10]):
            prompt += f"\n{i+1}. [{msg['date']}] {msg['text']}"
        
        if data['conversation_threads']:
            prompt += "\n\nПРИМЕРЫ ДИАЛОГОВ:"
            for i, thread in enumerate(data['conversation_threads']):
                prompt += f"\n\nДиалог {i+1}:"
                prompt += f"\nВопрос: {thread['original']['text']}"
                prompt += f"\nОтвет: {thread['reply']['text']}"
        
        prompt += f"\n\nПроанализируй эффективность модераторов согласно указанным критериям и верни результат в JSON формате."
        
        return prompt
    
    def _parse_openai_response(self, response_text: str) -> Dict[str, Any]:
        """Парсинг ответа от OpenAI"""
        try:
            # Ищем JSON в ответе
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Валидируем структуру
                if self._validate_result_structure(result):
                    return result
            
            # Если парсинг не удался, возвращаем fallback
            logger.warning("Failed to parse OpenAI response, using fallback")
            return self._get_fallback_result()
            
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            return self._get_fallback_result()
    
    def _validate_result_structure(self, result: Dict[str, Any]) -> bool:
        """Валидация структуры результата"""
        required_keys = ['summary', 'moderator_metrics', 'key_topics', 'recommendations']
        return all(key in result for key in required_keys)
    
    def _get_fallback_result(self) -> Dict[str, Any]:
        """Fallback результат в случае ошибки"""
        return {
            "summary": {
                "sentiment_score": 75,
                "response_time_avg": 5.0,
                "resolved_issues": 10,
                "satisfaction_score": 80,
                "engagement_rate": 70
            },
            "moderator_metrics": {
                "response_time": {"avg": 5.0, "min": 1.0, "max": 15.0},
                "sentiment": {"positive": 60, "neutral": 30, "negative": 10},
                "performance": {"effectiveness": 75, "helpfulness": 80, "clarity": 70}
            },
            "key_topics": ["support", "general discussion", "questions"],
            "recommendations": [
                "Анализ временно недоступен - используются базовые метрики",
                "Попробуйте запустить анализ позже"
            ]
        }
    
    async def analyze_community_sentiment(
        self,
        messages: List[Dict[str, Any]],
        prompt: str = None,
        group_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Анализ настроений жителей и проблем ЖКХ с добавлением связанных сообщений
        
        Args:
            messages: Список сообщений из группы
            prompt: Критерии анализа от пользователя
            group_name: Название группы
            
        Returns:
            Результат анализа настроений сообщества с related_messages
        """
        try:
            logger.info(f"🏠 Starting community sentiment analysis for group: {group_name}")
            
            # Проверяем входные данные
            if not messages:
                logger.warning("❌ No messages provided for community analysis")
                return self._get_community_fallback_result()
            
            # ОБНОВЛЕННЫЙ системный промпт для анализа жителей ЖКХ
            system_prompt = """Ты - эксперт по анализу общественных настроений в жилых комплексах и районах.

        Анализируй сообщения жителей для выявления:
                
        1. Основные проблемы и жалобы
        2. Качество работы управляющих компаний и коммунальных служб  
        3. Общие настроения жителей
        4. Предложения по улучшениям
        5. Проблемные зоны (подъезды, дворы, инфраструктура)

        ВАЖНО: Для каждой найденной проблемы укажи конкретные сообщения, которые привели к этому выводу.

        Верни результат СТРОГО в JSON формате:
        {
            "sentiment_summary": {
                "overall_mood": "недовольны|нейтрально|довольны",
                "satisfaction_score": number (0-100),
                "complaint_level": "низкий|средний|высокий"
            },
            "main_issues": [
                {
                    "category": "ЖКХ|Двор|Подъезд|Парковка|Шум|Безопасность", 
                    "issue": "описание проблемы", 
                    "frequency": number,
                    "related_messages": [
                        {
                            "text": "полный текст сообщения",
                            "date": "2025-06-20T14:30:00",
                            "author": "имя автора или null"
                        }
                    ]
                }
            ],
            "service_quality": {
                "управляющая_компания": number (0-100),
                "коммунальные_службы": number (0-100), 
                "уборка": number (0-100),
                "безопасность": number (0-100)
            },
            "improvement_suggestions": [string],
            "key_topics": [string],
            "urgent_issues": [
                {
                    "issue": "описание срочной проблемы",
                    "related_messages": [
                        {
                            "text": "текст сообщения",
                            "date": "2025-06-20T14:30:00", 
                            "author": "имя автора или null"
                        }
                    ]
                }
            ]
        }"""
            
            # Подготавливаем данные сообщений (ограничиваем для экономии токенов)
            message_texts = []
            for msg in messages:  # Максимум 100 сообщений
                if msg.get('text') and len(msg['text'].strip()) > 5:
                    # Извлекаем автора если есть
                    author = None
                    if msg.get('user_info') and msg['user_info']:
                        first_name = msg['user_info'].get('first_name', '')
                        last_name = msg['user_info'].get('last_name', '')
                        if first_name:
                            author = f"{first_name} {last_name[0] if last_name else ''}."
                    
                    message_texts.append({
                        'text': msg['text'][:500],  # Ограничиваем длину сообщения
                        'date': msg.get('date', ''),
                        'author': author
                    })
            
            # Пользовательский промпт
            if not prompt or not prompt.strip():
                prompt = "Проанализируй настроения жителей и выяви основные проблемы в жилом комплексе"
                
            user_prompt = f"""
    ГРУППА: {group_name}
    ЗАДАЧА: {prompt}

    СООБЩЕНИЯ ЖИТЕЛЕЙ ({len(message_texts)} шт.):
    """
            
            # Добавляем сообщения (максимум 30 для экономии токенов)
            for i, msg in enumerate(message_texts[:30]):
                author_info = f" от {msg['author']}" if msg['author'] else ""
                user_prompt += f"\n{i+1}. [{msg['date']}]{author_info}: {msg['text']}"
            
            if len(message_texts) > 30:
                user_prompt += f"\n... и еще {len(message_texts) - 30} сообщений"
            
            user_prompt += """

    ВАЖНЫЕ ИНСТРУКЦИИ:
    1. Для каждой проблемы в main_issues укажи ВСЕ сообщения, которые привели к этому выводу
    2. Для каждой срочной проблемы в urgent_issues также укажи related_messages  
    3. Включай полный текст сообщения, точную дату и автора (если известен)
    4. Если один автор упоминал проблему несколько раз - включай все его сообщения
    5. Анализируй настроения и проблемы жителей согласно указанным критериям"""
            
            logger.info("📤 Sending community analysis request to OpenAI...")
            
            # Запрос к OpenAI с таймаутом
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-4.1-2025-04-14",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=8000 # Увеличиваем лимит токенов для related_messages
                ),
                timeout=240.0
            )
            
            logger.info("✅ Received community analysis response from OpenAI")
            
            # Парсим ответ
            result = self._parse_community_response(response.choices[0].message.content)
            
            # Применяем фильтрацию 7% к main_issues
            if 'main_issues' in result and result['main_issues']:
                result['main_issues'] = self._filter_significant_issues(
                    result['main_issues'], 
                    len(messages),
                    min_percentage=7.0
                )
            
            logger.info("✅ Community sentiment analysis completed successfully")
            return result
            
        except asyncio.TimeoutError:
            logger.error("⏰ OpenAI request timed out for community analysis")
            return self._get_community_fallback_result()
        except Exception as e:
            logger.error(f"💥 Error in community sentiment analysis: {str(e)}")
            return self._get_community_fallback_result()
        

    def _get_community_fallback_result(self) -> Dict[str, Any]:
        """Fallback результат для анализа сообщества с related_messages"""
        return {
            "sentiment_summary": {
                "overall_mood": "анализ недоступен",
                "satisfaction_score": 0,
                "complaint_level": "неопределен"
            },
            "main_issues": [
                {
                    "category": "Техническая", 
                    "issue": "Анализ временно недоступен", 
                    "frequency": 1,
                    "related_messages": [
                        {
                            "text": "Анализ не может быть выполнен в данный момент",
                            "date": datetime.now().isoformat(),
                            "author": "Система"
                        }
                    ]
                }
            ],
            "service_quality": {
                "управляющая_компания": 0,
                "коммунальные_службы": 0,
                "уборка": 0,
                "безопасность": 0
            },
            "improvement_suggestions": ["Попробуйте анализ позже"],
            "key_topics": ["техническая проблема"],
            "urgent_issues": [
                {
                    "issue": "Система анализа недоступна",
                    "related_messages": [
                        {
                            "text": "Сервис анализа временно недоступен",
                            "date": datetime.now().isoformat(),
                            "author": "Система"
                        }
                    ]
                }
            ]
        }


    def _validate_community_structure(self, result: Dict[str, Any]) -> bool:
        """Валидация структуры результата анализа сообщества с related_messages"""
        try:
            # Проверяем основные ключи
            required_keys = ['sentiment_summary', 'main_issues', 'service_quality', 'improvement_suggestions', 'key_topics', 'urgent_issues']
            
            if not all(key in result for key in required_keys):
                logger.warning(f"❌ Missing required keys in community analysis. Expected: {required_keys}")
                return False
            
            # Проверяем структуру sentiment_summary
            sentiment_summary = result.get('sentiment_summary', {})
            sentiment_required = ['overall_mood', 'satisfaction_score', 'complaint_level']
            if not all(key in sentiment_summary for key in sentiment_required):
                logger.warning(f"❌ Invalid sentiment_summary structure")
                return False
            
            # Проверяем что main_issues это список
            main_issues = result.get('main_issues', [])
            if not isinstance(main_issues, list):
                logger.warning("❌ main_issues should be a list")
                return False
            
            # Проверяем структуру каждой проблемы в main_issues
            for issue in main_issues:
                if not isinstance(issue, dict):
                    logger.warning("❌ Each main issue should be a dictionary")
                    return False
                
                # Проверяем обязательные поля
                issue_required = ['category', 'issue', 'frequency']
                if not all(key in issue for key in issue_required):
                    logger.warning(f"❌ Issue missing required fields: {issue_required}")
                    return False
                
                # Проверяем related_messages (опционально, но если есть - должно быть списком)
                if 'related_messages' in issue:
                    if not isinstance(issue['related_messages'], list):
                        logger.warning("❌ related_messages should be a list")
                        return False
                    
                    # Проверяем структуру каждого сообщения
                    for msg in issue['related_messages']:
                        if not isinstance(msg, dict):
                            logger.warning("❌ Each related message should be a dictionary")
                            return False
                        
                        msg_required = ['text', 'date']
                        if not all(key in msg for key in msg_required):
                            logger.warning(f"❌ Related message missing required fields: {msg_required}")
                            return False
            
            # Проверяем структуру urgent_issues
            urgent_issues = result.get('urgent_issues', [])
            if not isinstance(urgent_issues, list):
                logger.warning("❌ urgent_issues should be a list")
                return False
            
            # Проверяем структуру каждой срочной проблемы
            for urgent in urgent_issues:
                if isinstance(urgent, str):
                    # Старый формат - просто строки, пропускаем
                    continue
                elif isinstance(urgent, dict):
                    # Новый формат - с related_messages
                    if 'issue' not in urgent:
                        logger.warning("❌ Urgent issue missing 'issue' field")
                        return False
                    
                    if 'related_messages' in urgent:
                        if not isinstance(urgent['related_messages'], list):
                            logger.warning("❌ urgent issue related_messages should be a list")
                            return False
            
            # Проверяем структуру service_quality
            service_quality = result.get('service_quality', {})
            if not isinstance(service_quality, dict):
                logger.warning("❌ service_quality should be a dictionary")
                return False
            
            logger.info("✅ Community analysis result structure is valid")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating community analysis structure: {e}")
            return False
    
    def _parse_community_response(self, response_text: str) -> Dict[str, Any]:
        """Парсинг ответа от OpenAI для анализа сообщества"""
        try:
            # Ищем JSON в ответе
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Валидируем структуру для анализа сообщества
                if self._validate_community_structure(result):
                    logger.info("Successfully parsed community analysis response")
                    return result
            
            logger.warning("Failed to parse community analysis response, using fallback")
            return self._get_community_fallback_result()
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in community analysis response: {e}")
            return self._get_community_fallback_result()
        except Exception as e:
            logger.error(f"Error parsing community analysis response: {e}")
            return self._get_community_fallback_result()

    def _validate_community_structure(self, result: Dict[str, Any]) -> bool:
        """Валидация структуры результата анализа сообщества"""
        try:
            # Проверяем основные ключи
            required_keys = ['sentiment_summary', 'main_issues', 'service_quality', 'improvement_suggestions', 'key_topics', 'urgent_issues']
            
            if not all(key in result for key in required_keys):
                logger.warning(f"Missing required keys in community analysis result. Expected: {required_keys}, Got: {list(result.keys())}")
                return False
            
            # Проверяем структуру sentiment_summary
            sentiment_summary = result.get('sentiment_summary', {})
            sentiment_required = ['overall_mood', 'satisfaction_score', 'complaint_level']
            if not all(key in sentiment_summary for key in sentiment_required):
                logger.warning(f"Invalid sentiment_summary structure. Expected: {sentiment_required}, Got: {list(sentiment_summary.keys())}")
                return False
            
            # Проверяем что main_issues это список
            if not isinstance(result.get('main_issues', []), list):
                logger.warning("main_issues should be a list")
                return False
            
            # Проверяем структуру service_quality
            service_quality = result.get('service_quality', {})
            if not isinstance(service_quality, dict):
                logger.warning("service_quality should be a dictionary")
                return False
            
            # Проверяем что остальные поля это списки
            list_fields = ['improvement_suggestions', 'key_topics', 'urgent_issues']
            for field in list_fields:
                if not isinstance(result.get(field, []), list):
                    logger.warning(f"{field} should be a list")
                    return False
            
            logger.info("Community analysis result structure is valid")
            return True
            
        except Exception as e:
            logger.error(f"Error validating community analysis structure: {e}")
            return False
        
    def _filter_significant_issues(
        self, 
        issues: List[Dict[str, Any]], 
        total_messages: int, 
        min_percentage: float = 7.0
    ) -> List[Dict[str, Any]]:
        """
        Фильтрация значимых проблем по правилу минимального процента
        
        Args:
            issues: Список проблем от OpenAI
            total_messages: Общее количество проанализированных сообщений
            min_percentage: Минимальный процент сообщений для значимой проблемы (по умолчанию 7%)
            
        Returns:
            Отфильтрованный список значимых проблем
        """
        if not issues or total_messages == 0:
            return issues
        
        filtered_issues = []
        
        logger.info(f"🔍 Фильтрация проблем: требуется минимум {min_percentage}% от {total_messages} сообщений")
        
        for issue in issues:
            # Считаем реальное количество related_messages
            related_messages = issue.get('related_messages', [])
            related_count = len(related_messages)
            
            # Вычисляем процент
            percentage = (related_count / total_messages) * 100 if total_messages > 0 else 0
            
            logger.info(f"📊 Проблема '{issue.get('issue', 'Unknown')}': {related_count}/{total_messages} = {percentage:.1f}%")
            
            if percentage >= min_percentage:
                filtered_issues.append(issue)
                logger.info(f"✅ Оставляем проблему (>= {min_percentage}%)")
            else:
                logger.info(f"❌ Убираем проблему как незначительную (< {min_percentage}%)")
        
        logger.info(f"🎯 Результат фильтрации: {len(filtered_issues)} из {len(issues)} проблем оставлено")
        
        return filtered_issues
    
    async def analyze_posts_comments(
        self,
        comments: List[Dict[str, Any]],
        posts_info: List[Dict[str, Any]],
        prompt: str = None,
        group_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Анализ комментариев к постам с фокусом на реакции и обратную связь
        
        Args:
            comments: Список комментариев к постам
            posts_info: Информация о постах
            prompt: Критерии анализа от пользователя
            group_name: Название группы
            
        Returns:
            Результат анализа комментариев к постам
        """
        try:
            logger.info(f"🔗 Starting posts comments analysis for group: {group_name}")
            
            # Проверяем входные данные
            if not comments:
                logger.warning("❌ No comments provided for posts analysis")
                return self._get_posts_fallback_result()
            
            # Системный промпт для анализа комментариев к постам
            system_prompt = """Ты - эксперт по анализу общественного мнения и реакций на публикации.

    Анализируй комментарии к постам для выявления:

    1. Общие реакции и настроения (поддержка/критика/нейтралитет)
    2. Основные темы обсуждения в комментариях  
    3. Конкретные проблемы и предложения от комментаторов
    4. Эмоциональный тон реакций
    5. Наиболее обсуждаемые аспекты постов

    ВАЖНО: Для каждой найденной темы или проблемы укажи конкретные комментарии, которые привели к этому выводу.

    Ответ должен быть в формате JSON:

    {
    "sentiment_summary": {
        "overall_mood": "общее настроение комментариев (позитивное/нейтральное/негативное)",
        "satisfaction_score": число от 0 до 100,
        "complaint_level": "уровень недовольства (низкий/средний/высокий)"
    },
    "main_issues": [
        {
        "category": "категория проблемы",
        "issue": "описание проблемы или темы",
        "frequency": число упоминаний,
        "related_messages": [
            {
            "text": "полный текст комментария",
            "date": "дата комментария",
            "author": "автор (если известен)",
            "post_link": "ссылка на пост"
            }
        ]
        }
    ],
    "post_reactions": {
        "положительные": число позитивных реакций,
        "нейтральные": число нейтральных реакций,  
        "негативные": число негативных реакций
    },
    "improvement_suggestions": ["список предложений по улучшению"],
    "key_topics": ["основные темы обсуждения"],
    "urgent_issues": [
        {
        "issue": "срочная проблема требующая внимания",
        "related_messages": [
            {
            "text": "комментарий об срочной проблеме",
            "date": "дата", 
            "author": "автор",
            "post_link": "ссылка на пост"
            }
        ]
        }
    ]
    }"""

            # Подготавливаем данные комментариев
            comment_texts = []
            for comment in comments[:50]:  # Ограничиваем для экономии токенов
                author = ""
                if comment.get('author'):
                    author_info = comment['author']
                    if author_info.get('username'):
                        author = f"@{author_info['username']}"
                    elif author_info.get('first_name'):
                        author = author_info.get('first_name', '')
                
                comment_texts.append({
                    'text': comment['text'][:500],  # Ограничиваем длину
                    'date': comment.get('date', ''),
                    'author': author,
                    'post_link': comment.get('post_link', '')
                })
            
            # Информация о постах
            posts_summary = []
            for post_info in posts_info:
                post_data = post_info.get('post_info', {})
                posts_summary.append({
                    'link': post_data.get('link', ''),
                    'message_id': post_data.get('message_id', ''),
                    'comments_count': post_info.get('comments_count', 0)
                })
            
            # Пользовательский промпт
            if not prompt or not prompt.strip():
                prompt = "Проанализируй реакции и комментарии к постам, выяви основные темы и настроения"
                
            user_prompt = f"""
    ГРУППА: {group_name}
    ЗАДАЧА: {prompt}

    АНАЛИЗИРУЕМЫЕ ПОСТЫ ({len(posts_summary)} шт.):
    """
            
            for i, post in enumerate(posts_summary):
                user_prompt += f"\n{i+1}. {post['link']} ({post['comments_count']} комментариев)"
            
            user_prompt += f"""

    КОММЕНТАРИИ К ПОСТАМ ({len(comment_texts)} шт.):
    """
            
            # Добавляем комментарии
            for i, comment in enumerate(comment_texts):
                author_info = f" от {comment['author']}" if comment['author'] else ""
                post_link = f" [Пост: {comment['post_link']}]" if comment['post_link'] else ""
                user_prompt += f"\n{i+1}. [{comment['date']}]{author_info}{post_link}: {comment['text']}"
            
            user_prompt += """

    ВАЖНЫЕ ИНСТРУКЦИИ:
    1. Для каждой проблемы в main_issues укажи ВСЕ комментарии, которые привели к этому выводу
    2. Для urgent_issues также укажи related_messages с полными комментариями
    3. Включай полный текст комментария, дату, автора и ссылку на пост
    4. Анализируй именно реакции на посты, а не общие настроения группы
    5. Определи какие посты вызвали больше всего дискуссий"""
            
            logger.info("📤 Sending posts comments analysis request to OpenAI...")
            
            # Запрос к OpenAI с таймаутом
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-4.1-2025-04-14",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=8000 # Увеличиваем для related_messages
                ),
                timeout=240.0
            )
            
            logger.info("✅ Received posts comments analysis response from OpenAI")
            
            # Парсим ответ
            result = self._parse_posts_response(response.choices[0].message.content)
            
            # Применяем фильтрацию 7% к main_issues
            if 'main_issues' in result and result['main_issues']:
                result['main_issues'] = self._filter_significant_issues(
                    result['main_issues'], 
                    len(comments),
                    min_percentage=7.0
                )
            
            logger.info("✅ Posts comments analysis completed successfully")
            return result
            
        except asyncio.TimeoutError:
            logger.error("⏰ OpenAI request timed out for posts comments analysis")
            return self._get_posts_fallback_result()
        except Exception as e:
            logger.error(f"💥 Error in posts comments analysis: {str(e)}")
            return self._get_posts_fallback_result()


    def _parse_posts_response(self, response_text: str) -> Dict[str, Any]:
        """Парсинг ответа от OpenAI для анализа комментариев к постам"""
        try:
            logger.info("Parsing OpenAI response for posts analysis...")
            
            # Убираем лишние символы и пробелы
            response_text = response_text.strip()
            
            # Пытаемся найти JSON блок разными способами
            json_str = None
            
            # Способ 1: Ищем первый { и последний }
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
            
            # Способ 2: Если не нашли, ищем между ```json и ```
            if not json_str:
                json_start = response_text.find('```json')
                if json_start != -1:
                    json_start += 7  # длина '```json'
                    json_end = response_text.find('```', json_start)
                    if json_end != -1:
                        json_str = response_text[json_start:json_end].strip()
            
            # Способ 3: Если все еще не нашли, берем весь текст
            if not json_str:
                json_str = response_text
            
            # Очищаем JSON от возможных проблем
            json_str = json_str.replace('\n', ' ')
            json_str = json_str.replace('\r', ' ')
            json_str = json_str.replace('\t', ' ')
            
            # Убираем множественные пробелы
            import re
            json_str = re.sub(r'\s+', ' ', json_str)
            
            # Пытаемся распарсить JSON
            result = json.loads(json_str)
            
            # Валидируем структуру
            if self._validate_posts_structure(result):
                logger.info("Successfully parsed and validated posts analysis response")
                return result
            else:
                logger.warning("Parsed JSON but structure validation failed")
                return self._get_posts_fallback_result()
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in posts analysis: {e}")
            logger.error(f"Problematic JSON: {json_str[:500] if 'json_str' in locals() else 'N/A'}")
            return self._get_posts_fallback_result()
            
        except Exception as e:
            logger.error(f"Unexpected error parsing posts response: {e}")
            return self._get_posts_fallback_result()


    def _validate_posts_structure(self, result: Dict[str, Any]) -> bool:
        """Валидация структуры результата анализа комментариев к постам"""
        try:
            # Проверяем основные ключи
            required_keys = ['sentiment_summary', 'main_issues', 'post_reactions', 'improvement_suggestions', 'key_topics', 'urgent_issues']
            
            if not all(key in result for key in required_keys):
                logger.warning(f"Missing required keys in posts analysis result. Expected: {required_keys}, Got: {list(result.keys())}")
                return False
            
            # Проверяем структуру sentiment_summary
            sentiment_summary = result.get('sentiment_summary', {})
            sentiment_required = ['overall_mood', 'satisfaction_score', 'complaint_level']
            if not all(key in sentiment_summary for key in sentiment_required):
                logger.warning(f"Invalid sentiment_summary structure. Expected: {sentiment_required}, Got: {list(sentiment_summary.keys())}")
                return False
            
            # Проверяем что main_issues это список
            if not isinstance(result.get('main_issues', []), list):
                logger.warning("main_issues should be a list")
                return False
            
            # Проверяем структуру post_reactions
            post_reactions = result.get('post_reactions', {})
            if not isinstance(post_reactions, dict):
                logger.warning("post_reactions should be a dictionary")
                return False
            
            logger.info("Posts comments analysis result structure is valid")
            return True
            
        except Exception as e:
            logger.error(f"Error validating posts analysis structure: {e}")
            return False


    def _get_posts_fallback_result(self) -> Dict[str, Any]:
        """Fallback результат для анализа комментариев к постам"""
        return {
            "sentiment_summary": {
                "overall_mood": "анализ недоступен",
                "satisfaction_score": 0,
                "complaint_level": "неопределен"
            },
            "main_issues": [
                {
                    "category": "Техническая", 
                    "issue": "Анализ временно недоступен", 
                    "frequency": 1,
                    "related_messages": [
                        {
                            "text": "Анализ не может быть выполнен в данный момент",
                            "date": datetime.now().isoformat(),
                            "author": "Система",
                            "post_link": ""
                        }
                    ]
                }
            ],
            "post_reactions": {
                "положительные": 0,
                "нейтральные": 0,
                "негативные": 0
            },
            "improvement_suggestions": ["Попробуйте анализ позже"],
            "key_topics": ["техническая проблема"],
            "urgent_issues": [
                {
                    "issue": "Система анализа недоступна",
                    "related_messages": [
                        {
                            "text": "Сервис анализа временно недоступен",
                            "date": datetime.now().isoformat(),
                            "author": "Система", 
                            "post_link": ""
                        }
                    ]
                }
            ]
        }
    
    async def analyze_potential_client(
        self,
        message_text: str,
        product_name: str,
        keywords: List[str],
        matched_keywords: List[str],
        author_info: Dict[str, Any],
        chat_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Анализ сообщения на предмет потенциального клиента
        
        Args:
            message_text: Текст сообщения пользователя
            product_name: Название продукта/услуги
            keywords: Все ключевые слова шаблона
            matched_keywords: Найденные ключевые слова в сообщении
            author_info: Данные автора сообщения
            chat_info: Данные чата/группы
            
        Returns:
            Результат анализа с confidence, intent_type, reasoning и всеми данными
        """
        try:
            system_prompt = """Ты - эксперт по анализу намерений клиентов в сообщениях.
    Твоя задача - определить, является ли автор сообщения потенциальным покупателем товара/услуги.

    КРИТЕРИИ ОЦЕНКИ:
    - 1-3: Низкая вероятность (просто упоминание, информационный запрос без намерения покупки)
    - 4-6: Средняя вероятность (интерес, сравнение вариантов, изучение рынка)  
    - 7-8: Высокая вероятность (активный поиск, готовность к покупке, конкретные потребности)
    - 9-10: Очень высокая вероятность (срочная потребность, готов купить сейчас)

    ТИПЫ НАМЕРЕНИЙ:
    - "информация" - просто интересуется, изучает
    - "покупка" - готов купить, ищет где купить
    - "сравнение" - сравнивает варианты, выбирает
    - "продажа" - хочет продать (не клиент)
    - "другое" - реклама, спам, не связано с покупкой

    ОБЯЗАТЕЛЬНО включи в ответ все данные о сообщении, авторе и чате для удобства администратора.

    Отвечай только в формате JSON без дополнительного текста."""

            user_prompt = f"""
    Проанализируй сообщение пользователя:

    ПРОДУКТ/УСЛУГА: {product_name}
    КЛЮЧЕВЫЕ СЛОВА: {', '.join(keywords)}
    НАЙДЕННЫЕ СЛОВА: {', '.join(matched_keywords)}

    АВТОР СООБЩЕНИЯ:
    - ID: {author_info.get('telegram_id', 'неизвестен')}
    - Username: @{author_info.get('username', 'неизвестен')}
    - Имя: {author_info.get('first_name', 'неизвестно')}

    ЧАТ/ГРУППА:
    - ID: {chat_info.get('chat_id', 'неизвестен')}
    - Название: {chat_info.get('chat_name', 'неизвестно')}

    СООБЩЕНИЕ:
    "{message_text}"

    Оцени по шкале от 1 до 10 уверенность в том, что это потенциальный покупатель.
    Определи тип намерения.
    Объясни свой анализ.

    Ответь в формате JSON:
    {{
        "confidence": число от 1 до 10,
        "intent_type": "информация/покупка/сравнение/продажа/другое",
        "reasoning": "подробное объяснение анализа",
        "message_data": {{
            "text": "{message_text}",
            "author": {{
                "telegram_id": "{author_info.get('telegram_id', '')}",
                "username": "{author_info.get('username', '')}",
                "first_name": "{author_info.get('first_name', '')}"
            }},
            "chat": {{
                "chat_id": "{chat_info.get('chat_id', '')}",
                "chat_name": "{chat_info.get('chat_name', '')}"
            }}
        }}
    }}"""

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Быстрая модель для простого анализа
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Низкая температура для более точного анализа
                max_tokens=400    # Увеличиваем для включения данных
            )
            
            # Парсим JSON ответ
            result_text = response.choices[0].message.content.strip()
            
            # Убираем возможные markdown блоки
            if result_text.startswith('```json'):
                result_text = result_text[7:-3]
            elif result_text.startswith('```'):
                result_text = result_text[3:-3]
                
            result = json.loads(result_text)
            
            # Валидация результата
            if not isinstance(result.get('confidence'), (int, float)):
                result['confidence'] = 5
            if result['confidence'] < 1:
                result['confidence'] = 1
            elif result['confidence'] > 10:
                result['confidence'] = 10
                
            logger.info(f"AI analysis completed: confidence={result.get('confidence')}, intent={result.get('intent_type')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {
                "confidence": 5,
                "intent_type": "unknown", 
                "reasoning": "Ошибка парсинга ответа ИИ",
                "message_data": {
                    "text": message_text,
                    "author": author_info,
                    "chat": chat_info
                }
            }
        except Exception as e:
            logger.error(f"Error in AI client analysis: {e}")
            return {
                "confidence": 0,
                "intent_type": "unknown",
                "reasoning": f"Ошибка анализа: {str(e)}",
                "message_data": {
                    "text": message_text,
                    "author": author_info,
                    "chat": chat_info
                }
            }
        
    