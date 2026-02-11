# bot/utils/antiflood.py
import asyncio
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from datetime import datetime, timedelta
from bot.config import settings
from bot.storage.redis_client import redis_client

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 30.0):
        super().__init__()
        self.rate_limit = rate_limit  # сообщений в секунду
        self.last_processed: Dict[int, datetime] = {}
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        
        # Проверка бана
        is_banned = await redis_client.is_user_banned(user_id)
        if is_banned:
            return
        
        # Per-user cooldown (храним в Redis)
        cooldown_key = f"cooldown:{user_id}"
        last_action = await redis_client.client.get(cooldown_key)
        
        if last_action:
            last_time = datetime.fromisoformat(last_action)
            if datetime.now() - last_time < timedelta(seconds=1):
                # Cooldown, игнорируем сообщение
                return
        
        # Global throttle (имитация лимитов Telegram)
        current_time = datetime.now()
        if user_id in self.last_processed:
            time_diff = (current_time - self.last_processed[user_id]).total_seconds()
            if time_diff < 1.0 / self.rate_limit:
                # Ждем перед обработкой следующего сообщения
                await asyncio.sleep(1.0 / self.rate_limit - time_diff)
        
        self.last_processed[user_id] = datetime.now()
        
        # Обновляем cooldown в Redis
        await redis_client.client.set(
            cooldown_key,
            datetime.now().isoformat(),
            ex=2
        )
        
        return await handler(event, data)
