import asyncio
import redis.asyncio as redis

async def test():
    try:
        r = redis.from_url('redis://localhost:6380/0')
        await r.ping()
        print(' Redis OK')
    except Exception as e:
        print(f' Redis connection failed: {e}')
    finally:
        await r.aclose()

asyncio.run(test())
