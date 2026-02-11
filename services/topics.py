from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from typing import Any
from storage.redis_store import RedisStorage


@dataclass(slots=True)
class TopicService:
    redis: RedisStorage
    pg: Any
    topic_ttl_seconds: int

    async def create_topic(self, user_id: int, text: str) -> str:
        topic_id = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.topic_ttl_seconds)
        payload = {
            "text": text,
            "owner": user_id,
            "expires_at": expires_at.timestamp(),
            "active": True,
        }
        await self.redis.create_topic(topic_id, payload, self.topic_ttl_seconds)
        # Передаём expires_at как объект datetime (не строку)
        await self.pg.create_topic(topic_id, user_id, text, expires_at)
        return topic_id