# bot/main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.storage.redis_client import redis_client
from bot.storage.postgres_client import Database
from bot.handlers import register_handlers
from bot.utils.antiflood import ThrottlingMiddleware

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Инициализация клиентов
    await redis_client.initialize(settings.REDIS_URL, settings.REDIS_POOL_SIZE)
    db = Database(settings.DATABASE_URL)
    await db.connect()
    
    # Создание бота и диспетчера
    bot = Bot(
        token=settings.TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Регистрация middleware
    dp.message.middleware(ThrottlingMiddleware(rate_limit=settings.MESSAGES_PER_SECOND))
    
    # Регистрация хендлеров
    register_handlers(dp, db)
    
    try:
        await dp.start_polling(bot)
    finally:
        await redis_client.aclose()
        await db.disconnect()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

