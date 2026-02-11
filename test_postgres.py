import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect('postgresql://anon:anon@localhost:5433/anon_chat')
        await conn.execute('SELECT 1')
        print(' PostgreSQL OK')
    except Exception as e:
        print(f' PostgreSQL connection failed: {e}')
    finally:
        await conn.close()

asyncio.run(test())
