from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from states import UserState


@dataclass(slots=True)
class RedisStorage:
    redis: Any

    async def set_state(self, user_id: int, state: UserState) -> None:
        await self.redis.set(f"user:{user_id}:state", state.value)

    async def get_state(self, user_id: int) -> UserState:
        raw = await self.redis.get(f"user:{user_id}:state")
        if raw is None:
            return UserState.IDLE
        return UserState(raw.decode() if isinstance(raw, bytes) else raw)

    async def set_dialog(self, user_id: int, dialog_id: str | None) -> None:
        key = f"user:{user_id}:dialog_id"
        if dialog_id is None:
            await self.redis.delete(key)
            return
        await self.redis.set(key, dialog_id)

    async def get_dialog(self, user_id: int) -> str | None:
        raw = await self.redis.get(f"user:{user_id}:dialog_id")
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw

    async def enqueue_search(self, user_id: int) -> None:
        await self.redis.rpush("search:queue", user_id)

    async def dequeue_search(self) -> int | None:
        raw = await self.redis.lpop("search:queue")
        if raw is None:
            return None
        return int(raw)

    async def remove_from_queue(self, user_id: int) -> None:
        await self.redis.lrem("search:queue", 0, user_id)

    async def create_topic(self, topic_id: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        await self.redis.hset(f"topic:{topic_id}", mapping={k: json.dumps(v) for k, v in payload.items()})
        await self.redis.expire(f"topic:{topic_id}", ttl_seconds)

    async def get_topic(self, topic_id: str) -> dict[str, Any] | None:
        raw = await self.redis.hgetall(f"topic:{topic_id}")
        if not raw:
            return None
        decoded = {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in raw.items()
        }
        return {k: json.loads(v) for k, v in decoded.items()}


    async def list_topic_ids(self) -> list[str]:
        keys = await self.redis.keys("topic:*")
        result: list[str] = []
        for key in keys:
            key_s = key.decode() if isinstance(key, bytes) else key
            result.append(key_s.split(":", 1)[1])
        result.sort()
        return result

    async def set_topic_draft(self, user_id: int, text: str | None) -> None:
        key = f"user:{user_id}:topic_draft"
        if text is None:
            await self.redis.delete(key)
            return
        await self.redis.set(key, text, ex=900)

    async def get_topic_draft(self, user_id: int) -> str | None:
        raw = await self.redis.get(f"user:{user_id}:topic_draft")
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw

    async def set_topic_cursor(self, user_id: int, topic_ids: list[str], idx: int = 0) -> None:
        await self.redis.set(f"user:{user_id}:topic_cursor", json.dumps({"topic_ids": topic_ids, "idx": idx}), ex=900)

    async def get_topic_cursor(self, user_id: int) -> tuple[list[str], int]:
        raw = await self.redis.get(f"user:{user_id}:topic_cursor")
        if raw is None:
            return [], 0
        blob = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        return blob["topic_ids"], blob["idx"]

    async def create_dialog(self, dialog_id: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        await self.redis.hset(f"dialog:{dialog_id}", mapping={k: json.dumps(v) for k, v in payload.items()})
        await self.redis.expire(f"dialog:{dialog_id}", ttl_seconds)

    async def get_dialog_payload(self, dialog_id: str) -> dict[str, Any] | None:
        raw = await self.redis.hgetall(f"dialog:{dialog_id}")
        if not raw:
            return None
        decoded = {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in raw.items()
        }
        return {k: json.loads(v) for k, v in decoded.items()}

    async def set_ttl_flag(self, prefix: str, user_id: int, ttl_seconds: int) -> None:
        await self.redis.set(f"{prefix}:{user_id}", "1", ex=ttl_seconds)

    async def has_ttl_flag(self, prefix: str, user_id: int) -> bool:
        return await self.redis.exists(f"{prefix}:{user_id}") == 1