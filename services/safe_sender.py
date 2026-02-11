from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import Message

logger = logging.getLogger(__name__)


async def safe_reply(message: Message, text: str, **kwargs) -> Message | None:
    return await _retry_op(lambda: message.answer(text, **kwargs))


async def safe_send_message(bot: Bot, chat_id: int, text: str, **kwargs) -> Message | None:
    return await _retry_op(lambda: bot.send_message(chat_id, text, **kwargs))


async def safe_copy_to(message: Message, chat_id: int) -> Message | None:
    return await _retry_op(lambda: message.send_copy(chat_id=chat_id))


async def _retry_op(operation: Callable[[], Awaitable[Message]], retries: int = 3):
    delay = 1.0
    for _ in range(retries):
        try:
            return await operation()
        except TelegramRetryAfter as exc:
            wait_time = max(exc.retry_after, delay)
            logger.warning("Rate limit reached, waiting %.2f sec", wait_time)
            await asyncio.sleep(wait_time)
            delay *= 2
    logger.error("Failed to execute Telegram API call after retries")
    return None