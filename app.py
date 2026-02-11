from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from dotenv import load_dotenv
from redis.asyncio import Redis

from bot_config import load_settings
from handlers.chat import router as chat_router
from services.dialogs import DialogService
from services.matchmaking import MatchmakingService
from services.topics import TopicService
from storage.postgres_store import PostgresStorage
from storage.redis_store import RedisStorage


class ServicesMiddleware(BaseMiddleware):
    def __init__(self, redis: RedisStorage, pg: PostgresStorage):
        self.redis = redis
        self.pg = pg

    async def __call__(self, handler, event, data):
        data["redis"] = self.redis
        data["pg"] = self.pg
        settings = data["settings"]
        data["matchmaking"] = MatchmakingService(self.redis, self.pg, settings.dialog_ttl_seconds)
        data["dialogs"] = DialogService(self.redis, self.pg, settings.ban_ttl_seconds)
        data["topics"] = TopicService(self.redis, self.pg, settings.topic_ttl_seconds)
        return await handler(event, data)


async def main() -> None:
    load_dotenv()
    settings = load_settings()
    logging.basicConfig(level=settings.log_level)

    bot = Bot(token=settings.bot_token)
    redis_client = Redis.from_url(settings.redis_url)
    redis_store = RedisStorage(redis_client)
    pg_store = await PostgresStorage.from_dsn(settings.postgres_dsn)

    dp = Dispatcher()
    dp["settings"] = settings
    dp.message.middleware(ServicesMiddleware(redis_store, pg_store))
    dp.include_router(chat_router)

    try:
        await dp.start_polling(bot, settings=settings)
    finally:
        await redis_client.aclose()
        await pg_store.close()


if __name__ == "__main__":
    asyncio.run(main())