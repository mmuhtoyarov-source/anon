# bot/handlers/admin.py
from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.storage.redis_client import redis_client
from bot.storage.postgres_client import Database

async def cmd_stats(message: Message, db: Database):
    """Статистика бота (только для админов)"""
    # Проверяем админские права (заглушка)
    if message.from_user.id not in [123456789]:  # Заменить на реальные ID админов
        return
    
    # Получаем статистику из Redis
    search_queue_len = await redis_client.client.llen("search:queue")
    active_topics = await redis_client.client.scard("topics:active")
    active_dialogs = len(await redis_client.client.keys("dialog:*")) // 2
    
    stats_text = (
        f" <b>Статистика бота</b>\n\n"
        f" В поиске: {search_queue_len}\n"
        f" Активных тем: {active_topics}\n"
        f" Активных диалогов: {active_dialogs}\n"
    )
    
    await message.answer(stats_text)

async def cmd_cleanup(message: Message, db: Database):
    """Очистка истекших записей"""
    if message.from_user.id not in [123456789]:
        return
    
    await db.cleanup_expired()
    await message.answer(" Очистка завершена.")

def register_admin_handlers(dp: Dispatcher, db: Database):
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_cleanup, Command("cleanup"))
