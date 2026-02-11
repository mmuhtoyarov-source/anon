import asyncio

from services.dialogs import DialogService
from states import UserState


def test_report_applies_ban_and_resets_state(redis_store, fake_pg):
    async def run():
        await redis_store.create_dialog(
            "d-1",
            {"user1": 1, "user2": 2, "started_at": "now", "expires_at": 1},
            3600,
        )
        await redis_store.set_dialog(1, "d-1")
        await redis_store.set_dialog(2, "d-1")
        await redis_store.set_state(1, UserState.IN_DIALOG)
        await redis_store.set_state(2, UserState.IN_DIALOG)

        service = DialogService(redis_store, fake_pg, 3600)
        target = await service.report_partner(1)

        assert target == 2
        assert await redis_store.has_ttl_flag("ban", 2)
        assert await redis_store.get_state(1) == UserState.IDLE
        assert await redis_store.get_state(2) == UserState.IDLE

    asyncio.run(run())