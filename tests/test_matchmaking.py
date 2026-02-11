import asyncio

from services.matchmaking import MatchmakingService
from states import UserState


def test_matchmaking_pairs_two_users(redis_store, fake_pg):
    async def run():
        service = MatchmakingService(redis_store, fake_pg, 3600)
        await service.begin_search(1)
        await service.begin_search(2)
        matched, dialog_id, partner = await service.try_match(1)

        assert matched is True
        assert dialog_id is not None
        assert partner == 2
        assert await redis_store.get_state(1) == UserState.IN_DIALOG
        assert await redis_store.get_state(2) == UserState.IN_DIALOG

    asyncio.run(run())