from __future__ import annotations

import asyncpg


SCHEMA_SQL = """
create table if not exists users (
  telegram_id bigint primary key,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  ban_until timestamptz
);
create table if not exists dialogs (
  id text primary key,
  user1 bigint not null,
  user2 bigint not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  reason text
);
create table if not exists topics (
  id text primary key,
  user_id bigint not null,
  text text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);
create table if not exists reports (
  id bigserial primary key,
  from_id bigint not null,
  target_id bigint not null,
  reason text,
  created_at timestamptz not null default now()
);
"""


class PostgresStorage:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def from_dsn(cls, dsn: str) -> "PostgresStorage":
        pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=4)
        store = cls(pool)
        await store.init_schema()
        return store

    async def close(self) -> None:
        await self.pool.close()

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)

    async def upsert_user(self, user_id: int) -> None:
        sql = """
        insert into users(telegram_id)
        values($1)
        on conflict (telegram_id)
        do update set last_seen_at = now();
        """
        async with self.pool.acquire() as conn:
            await conn.execute(sql, user_id)

    async def create_dialog(self, dialog_id: str, user1: int, user2: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "insert into dialogs(id, user1, user2) values($1, $2, $3)",
                dialog_id,
                user1,
                user2,
            )

    async def end_dialog(self, dialog_id: str, reason: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "update dialogs set ended_at=now(), reason=$2 where id=$1",
                dialog_id,
                reason,
            )

    async def create_topic(self, topic_id: str, user_id: int, text: str, expires_at) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "insert into topics(id, user_id, text, expires_at) values($1, $2, $3, $4)",
                topic_id,
                user_id,
                text,
                expires_at,  # теперь передаём datetime напрямую
            )

    async def create_report(self, from_id: int, target_id: int, reason: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "insert into reports(from_id, target_id, reason) values($1, $2, $3)",
                from_id,
                target_id,
                reason,
            )