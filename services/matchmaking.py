from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
import logging

from states import UserState
from typing import Any
from storage.redis_store import RedisStorage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MatchmakingService:
    redis: RedisStorage
    pg: Any
    dialog_ttl_seconds: int

    async def begin_search(self, user_id: int) -> None:
        logger.info(f"begin_search: user={user_id}")
        await self.redis.set_state(user_id, UserState.SEARCHING)
        await self.redis.remove_from_queue(user_id)
        await self.redis.enqueue_search(user_id)
        logger.info(f"begin_search: user={user_id} added to queue")

    async def try_match(self, user_id: int) -> tuple[bool, str | None, int | None]:
        logger.info(f"try_match: user={user_id}")
        partner = await self._find_partner(user_id)
        if partner is None:
            logger.info(f"try_match: user={user_id}  no partner found")
            return False, None, None
        logger.info(f"try_match: user={user_id} matched with partner={partner}")
        dialog_id = str(uuid4())
        payload = {
            "user1": user_id,
            "user2": partner,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.now(timezone.utc).timestamp() + self.dialog_ttl_seconds,
        }
        await self.redis.create_dialog(dialog_id, payload, self.dialog_ttl_seconds)
        await self.redis.set_dialog(user_id, dialog_id)
        await self.redis.set_dialog(partner, dialog_id)
        await self.redis.set_state(user_id, UserState.IN_DIALOG)
        await self.redis.set_state(partner, UserState.IN_DIALOG)
        await self.pg.create_dialog(dialog_id, user_id, partner)
        logger.info(f"try_match: dialog={dialog_id} created for users {user_id} and {partner}")
        return True, dialog_id, partner

    async def cancel_search(self, user_id: int) -> None:
        logger.info(f"cancel_search: user={user_id}")
        await self.redis.remove_from_queue(user_id)
        await self.redis.set_state(user_id, UserState.IDLE)

    async def _find_partner(self, user_id: int) -> int | None:
        logger.info(f"_find_partner: looking for partner for user={user_id}")
        seen: list[int] = []
        partner: int | None = None
        while True:
            candidate = await self.redis.dequeue_search()
            if candidate is None:
                logger.info(f"_find_partner: queue is empty for user={user_id}")
                break
            logger.info(f"_find_partner: dequeued candidate={candidate}")
            if candidate == user_id:
                logger.info(f"_find_partner: candidate == user_id, skipping and re-adding")
                seen.append(candidate)
                continue
            state = await self.redis.get_state(candidate)
            logger.info(f"_find_partner: candidate={candidate} state={state}")
            if state == UserState.SEARCHING:
                partner = candidate
                logger.info(f"_find_partner: found suitable partner={partner}")
                break
            seen.append(candidate)
        # re-queue all seen candidates (except the matched partner)
        for item in seen:
            if item != partner:
                logger.info(f"_find_partner: re-queueing candidate={item}")
                await self.redis.enqueue_search(item)
        return partner