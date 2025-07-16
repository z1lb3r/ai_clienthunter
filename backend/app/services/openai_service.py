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
        chat_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Упрощенный анализ сообщения - простое бинарное решение: клиент или не клиент
        
        Args:
            message_text: Текст сообщения пользователя
            product_name: Название продукта/услуги
            keywords: Все ключевые слова шаблона
            matched_keywords: Найденные ключевые слова в сообщении
            author_info: Данные автора сообщения
            chat_info: Данные чата/группы
            
        Returns:
            Простой результат: is_client (bool) + объяснение
        """
        try:
            # Простой системный промпт
            system_prompt = """Ты анализируешь сообщения для поиска потенциальных клиентов.

    ЗАДАЧА: Определить, хочет ли автор сообщения КУПИТЬ/ПРИОБРЕСТИ товары или услуги из указанных ключевых слов.

    ВАЖНО: Мы ищем ПОКУПАТЕЛЕЙ, а не продавцов услуг!

    ОТВЕТ ТОЛЬКО: "ДА" или "НЕТ" + краткое объяснение (1-2 предложения)."""

            user_prompt = f"""
    Анализируемое сообщение: "{message_text}"

    Ключевые слова продукта/услуги: {', '.join(matched_keywords)}

    Автор: @{author_info.get('username', 'неизвестен')}
    Чат: {chat_info.get('chat_name', 'неизвестно')}

    Хочет ли автор КУПИТЬ/ПРИОБРЕСТИ что-то из ключевых слов?"""

            # Отправляем запрос в OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.1
            )

            ai_response = response.choices[0].message.content.strip()
            
            # Определяем результат
            is_client = ai_response.lower().startswith('да')
            
            result = {
                'is_client': is_client,
                'reasoning': ai_response,
                'matched_keywords': matched_keywords,
                'author_info': author_info,
                'chat_info': chat_info,
                'message_text': message_text[:200] + '...' if len(message_text) > 200 else message_text
            }
            
            logger.info(f"AI Analysis Result: {'✅ КЛИЕНТ' if is_client else '❌ НЕ КЛИЕНТ'} - {ai_response[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in OpenAI analysis: {e}")
            
            # В случае ошибки считаем потенциальным клиентом (безопасный fallback)
            return {
                'is_client': True,
                'reasoning': f'Ошибка AI анализа: {str(e)}. Сообщение сохранено для ручной проверки.',
                'matched_keywords': matched_keywords,
                'author_info': author_info,
                'chat_info': chat_info,
                'message_text': message_text[:200] + '...' if len(message_text) > 200 else message_text
            }
    
   
    
# Глобальный экземпляр сервиса
openai_service = OpenAIService()