import asyncio

from states import UserState


def test_state_and_dialog(redis_store):
    async def run():
        await redis_store.set_state(10, UserState.SEARCHING)
        await redis_store.set_dialog(10, "dlg-1")
        assert await redis_store.get_state(10) == UserState.SEARCHING
        assert await redis_store.get_dialog(10) == "dlg-1"

    asyncio.run(run())


def test_queue_fifo(redis_store):
    async def run():
        await redis_store.enqueue_search(1)
        await redis_store.enqueue_search(2)
        assert await redis_store.dequeue_search() == 1
        assert await redis_store.dequeue_search() == 2

    asyncio.run(run())