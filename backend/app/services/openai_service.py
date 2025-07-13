# backend/app/services/openai_service.py - ОЧИЩЕННАЯ ВЕРСИЯ

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        """Инициализация OpenAI сервиса"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("✅ OpenAI Service initialized")
    
    async def analyze_potential_client(
        self,
        message_text: str,
        product_name: str,
        keywords: List[str],
        matched_keywords: List[str],
        author_info: Dict[str, Any],
        chat_info: Dict[str, Any],
        custom_prompt: str
    ) -> Dict[str, Any]:
        """
        Анализ сообщения на предмет потенциального клиента с кастомным промптом
        
        Args:
            message_text: Текст сообщения пользователя
            product_name: Название продукта/услуги
            keywords: Все ключевые слова шаблона
            matched_keywords: Найденные ключевые слова в сообщении
            author_info: Данные автора сообщения
            chat_info: Данные чата/группы
            custom_prompt: Кастомный промпт для анализа
            
        Returns:
            Результат анализа с confidence, intent_type, reasoning и всеми данными
        """
        try:
            # Используем кастомный промпт как system_prompt
            system_prompt = custom_prompt

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

    Верни результат СТРОГО в JSON формате:
    {{
        "confidence": число_от_1_до_10,
        "intent_type": "информация|покупка|сравнение|продажа|другое",
        "reasoning": "Подробное объяснение анализа",
        "message_data": {{
            "text": "{message_text}",
            "matched_keywords": {matched_keywords},
            "author": {{
                "id": "{author_info.get('telegram_id', '')}",
                "username": "{author_info.get('username', '')}",
                "name": "{author_info.get('first_name', '')} {author_info.get('last_name', '')}"
            }},
            "chat": {{
                "id": "{chat_info.get('chat_id', '')}",
                "name": "{chat_info.get('chat_name', '')}"
            }}
        }}
    }}"""

            logger.info("📤 Sending client analysis request to OpenAI with custom prompt...")
            
            # Запрос к OpenAI
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-4o-mini", 
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,  # Низкая температура для более стабильных результатов
                    max_tokens=2000
                ),
                timeout=60.0
            )
            
            logger.info("✅ Received client analysis response from OpenAI")
            
            # Парсим ответ
            result = self._parse_client_response(response.choices[0].message.content)
            
            logger.info(f"🎯 Analysis result: confidence={result.get('confidence', 0)}, intent={result.get('intent_type', 'unknown')}")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("⏰ OpenAI request timed out for client analysis")
            return self._get_client_fallback_result(message_text, author_info, chat_info)
        except Exception as e:
            logger.error(f"❌ Error in potential client analysis: {e}")
            return self._get_client_fallback_result(message_text, author_info, chat_info)
    
    def _parse_client_response(self, response_text: str) -> Dict[str, Any]:
        """Парсинг ответа OpenAI для анализа клиентов"""
        try:
            # Удаляем возможные markdown блоки
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # Парсим JSON
            result = json.loads(cleaned_text)
            
            # Валидация обязательных полей
            if 'confidence' not in result:
                result['confidence'] = 5
            if 'intent_type' not in result:
                result['intent_type'] = 'unknown'
            if 'reasoning' not in result:
                result['reasoning'] = 'Анализ выполнен'
            
            # Убеждаемся что confidence в правильном диапазоне
            result['confidence'] = max(1, min(10, int(result['confidence'])))
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"Raw response: {response_text}")
            return self._get_client_fallback_result("", {}, {})
        except Exception as e:
            logger.error(f"❌ Error parsing client analysis response: {e}")
            return self._get_client_fallback_result("", {}, {})
    
    def _get_client_fallback_result(
        self, 
        message_text: str, 
        author_info: Dict[str, Any], 
        chat_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback результат для анализа клиентов при ошибках"""
        return {
            "confidence": 5,
            "intent_type": "unknown",
            "reasoning": "Не удалось выполнить анализ через ИИ. Требуется ручная проверка.",
            "message_data": {
                "text": message_text,
                "matched_keywords": [],
                "author": {
                    "id": author_info.get('telegram_id', ''),
                    "username": author_info.get('username', ''),
                    "name": f"{author_info.get('first_name', '')} {author_info.get('last_name', '')}"
                },
                "chat": {
                    "id": chat_info.get('chat_id', ''),
                    "name": chat_info.get('chat_name', '')
                }
            },
            "error": True
        }

# Глобальный экземпляр сервиса
openai_service = OpenAIService()