from __future__ import annotations

from dataclasses import dataclass

from states import UserState
from typing import Any
from storage.redis_store import RedisStorage


@dataclass(slots=True)
class DialogService:
    redis: RedisStorage
    pg: Any
    ban_ttl_seconds: int

    async def get_partner(self, user_id: int) -> tuple[str, int] | tuple[None, None]:
        dialog_id = await self.redis.get_dialog(user_id)
        if dialog_id is None:
            return None, None
        payload = await self.redis.get_dialog_payload(dialog_id)
        if payload is None:
            return None, None
        partner = payload["user2"] if payload["user1"] == user_id else payload["user1"]
        return dialog_id, int(partner)

    async def finish_dialog(self, user_id: int, reason: str) -> int | None:
        dialog_id, partner = await self.get_partner(user_id)
        if dialog_id is None:
            await self.redis.set_state(user_id, UserState.IDLE)
            return None

        await self.redis.set_dialog(user_id, None)
        await self.redis.set_dialog(partner, None)
        await self.redis.set_state(user_id, UserState.IDLE)
        await self.redis.set_state(partner, UserState.IDLE)
        await self.pg.end_dialog(dialog_id, reason)
        return partner

    async def report_partner(self, from_id: int, reason: str = "spam") -> int | None:
        _dialog_id, target_id = await self.get_partner(from_id)
        if target_id is None:
            return None
        await self.pg.create_report(from_id, target_id, reason)
        await self.redis.set_ttl_flag("ban", target_id, self.ban_ttl_seconds)
        await self.finish_dialog(from_id, "report")
        return target_id