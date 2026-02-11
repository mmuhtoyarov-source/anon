# bot/handlers/search.py
import asyncio
from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.filters import StateFilter

from bot.storage.redis_client import redis_client
from bot.storage.postgres_client import Database
from bot.keyboards import (
    get_idle_keyboard, get_searching_keyboard, get_dialog_keyboard,
    get_dialog_ended_keyboard
)
from bot.config import settings

async def start_search(message: Message, db: Database):
    """Начало поиска собеседника"""
    user_id = message.from_user.id
    
    # Проверяем состояние
    state = await redis_client.get_user_state(user_id)
    if state != "IDLE":
        await message.answer("Сначала завершите текущее действие.")
        return
    
    # Добавляем в очередь поиска
    added = await redis_client.add_to_search_queue(user_id)
    if not added:
        await message.answer("Вы уже в очереди поиска.")
        return
    
    await redis_client.set_user_state(user_id, "SEARCHING")
    await message.answer(
        " Ищем собеседника...",
        reply_markup=get_searching_keyboard()
    )
    
    # Запускаем таймер поиска
    asyncio.create_task(search_with_timeout(user_id, db))

async def search_with_timeout(user_id: int, db: Database):
    """Поиск собеседника с таймаутом"""
    search_start = asyncio.get_event_loop().time()
    timeout = settings.SEARCH_TIMEOUT
    
    while asyncio.get_event_loop().time() - search_start < timeout:
        # Пытаемся найти пару
        match = await redis_client.find_match()
        
        if match:
            user1_id, user2_id = match
            
            # Создаем диалог
            dialog_id = await redis_client.create_dialog(user1_id, user2_id)
            if dialog_id:
                # Сохраняем в PostgreSQL
                await db.create_dialog(user1_id, user2_id)
                
                # Отправляем уведомления пользователям
                await notify_users_about_match(user1_id, user2_id, dialog_id, db)
                return
        
        await asyncio.sleep(1)  # Пауза между попытками
    
    # Таймаут - заканчиваем поиск
    await redis_client.remove_from_search_queue(user_id)
    await redis_client.set_user_state(user_id, "IDLE")
    
    # Отправляем сообщение о таймауте
    has_active_topic = await redis_client.client.exists(f"user:{user_id}:topic_id") > 0
    await send_message_to_user(
        user_id,
        " Не удалось найти собеседника за отведенное время. Попробуйте еще раз.",
        get_idle_keyboard(has_active_topic)
    )

async def cancel_search(message: Message):
    """Отмена поиска"""
    user_id = message.from_user.id
    
    removed = await redis_client.remove_from_search_queue(user_id)
    if removed:
        await redis_client.set_user_state(user_id, "IDLE")
        
        has_active_topic = await redis_client.client.exists(f"user:{user_id}:topic_id") > 0
        await message.answer(
            " Поиск отменен.",
            reply_markup=get_idle_keyboard(has_active_topic)
        )
    else:
        await message.answer("Вы не в поиске.")

async def notify_users_about_match(user1_id: int, user2_id: int, dialog_id: str, db: Database):
    """Уведомление пользователей о найденном собеседнике"""
    message_text = " Собеседник найден! Общайтесь анонимно."
    
    # Отправляем обоим пользователям
    for uid in [user1_id, user2_id]:
        await send_message_to_user(
            uid,
            message_text,
            get_dialog_keyboard()
        )

async def send_message_to_user(user_id: int, text: str, keyboard):
    """Отправка сообщения пользователю (заглушка)"""
    # В реальной реализации здесь будет обращение к боту
    pass

def register_search_handlers(dp: Dispatcher, db: Database):
    dp.message.register(start_search, F.text == " Найти собеседника")
    dp.message.register(cancel_search, F.text == " Отменить поиск")
