# backend/app/api/v1/telegram.py - ОЧИЩЕННАЯ ВЕРСИЯ

from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
import asyncio
import logging
import traceback
from datetime import datetime

from app.core.database import supabase_client
from app.services.telegram_service import telegram_service

router = APIRouter()
logger = logging.getLogger(__name__)

# ===== ГРУППЫ =====

@router.get("/groups")
async def get_telegram_groups():
    """Получить все Telegram группы"""
    try:
        result = supabase_client.table('telegram_groups').select("*").execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting telegram groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/groups/{group_id}")
async def get_telegram_group(group_id: str):
    """Получить детали конкретной группы"""
    try:
        result = supabase_client.table('telegram_groups').select("*").eq('id', group_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Group not found")
            
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting telegram group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/groups/{group_id}/messages")
async def get_group_messages(group_id: str):
    """Получить сообщения из группы"""
    try:
        group = supabase_client.table('telegram_groups').select("*").eq('id', group_id).execute()
        
        if not group.data:
            raise HTTPException(status_code=404, detail="Group not found")
            
        telegram_group_id = group.data[0]["group_id"]
        
        messages = await telegram_service.get_group_messages(
            telegram_group_id, 
            limit=100,
            get_users=True
        )
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/groups/{group_id}/moderators")
async def get_group_moderators(group_id: str):
    """Получить модераторов группы"""
    try:
        group = supabase_client.table('telegram_groups').select("*").eq('id', group_id).execute()
        
        if not group.data:
            raise HTTPException(status_code=404, detail="Group not found")
            
        telegram_group_id = group.data[0]["group_id"]
        
        moderators = await telegram_service.get_moderators(telegram_group_id)
        
        return moderators
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting moderators for group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ТЕСТОВЫЕ ЭНДПОИНТЫ =====

@router.get("/groups/{group_id}/test-methods")
async def test_message_retrieval_methods(group_id: str):
    """Тест различных методов получения сообщений"""
    try:
        group = supabase_client.table('telegram_groups').select("*").eq('id', group_id).execute()
        
        if not group.data:
            raise HTTPException(status_code=404, detail="Group not found")
            
        telegram_group_id = group.data[0]["group_id"]
        
        results = {
            "methods_tested": {},
            "recommended_method": None
        }
        
        # Тест 1: get_messages
        try:
            entity = await telegram_service.get_entity(telegram_group_id)
            messages_result = await telegram_service.client.get_messages(entity, limit=5)
            
            results["methods_tested"]["get_messages"] = {
                "status": "success",
                "count": len([m for m in messages_result if m]),
                "method": "direct"
            }
        except Exception as e:
            results["methods_tested"]["get_messages"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Тест 2: iter_messages
        try:
            entity = await telegram_service.get_entity(telegram_group_id)
            count = 0
            async for message in telegram_service.client.iter_messages(entity, limit=5):
                count += 1
                if count >= 5:
                    break
                    
            results["methods_tested"]["iter_messages"] = {
                "status": "success",
                "count": count,
                "method": "iterator"
            }
        except Exception as e:
            results["methods_tested"]["iter_messages"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Определяем рекомендуемый метод
        if results["methods_tested"].get("get_messages", {}).get("status") == "success":
            results["recommended_method"] = "get_messages"
        elif results["methods_tested"].get("iter_messages", {}).get("status") == "success":
            results["recommended_method"] = "iter_messages"
        else:
            results["recommended_method"] = "none_working"
        
        return {
            "status": "success",
            "telegram_group_id": telegram_group_id,
            "results": results
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}