import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Создание пула соединений"""
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=5,
            max_size=20,
            command_timeout=60
        )

    async def disconnect(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()

    async def get_or_create_user(self, user_id: int, username: str,
                                 first_name: str, last_name: str = "") -> Dict[str, Any]:
        """Получение или создание пользователя"""
        query = """
        INSERT INTO users (user_id, username, first_name, last_name, last_seen)
        VALUES ($1, $2, $3, $4, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            last_seen = NOW()
        RETURNING *
        """

        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(query, user_id, username, first_name, last_name)
                return dict(row) if row else {}
            except Exception as e:
                print(f"Ошибка при создании пользователя: {e}")
                return {}

    async def create_ban(self, user_id: int, reason: str,
                        banned_by: Optional[int] = None, duration_hours: int = 1) -> str:
        """Создание записи о бане"""
        query = """
        INSERT INTO bans (user_id, reason, banned_by, expires_at)
        VALUES ($1, $2, $3, NOW() + INTERVAL '1 hour' * $4)
        RETURNING ban_id
        """

        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchval(query, user_id, reason, banned_by, duration_hours)
                return str(result)
            except Exception as e:
                print(f"Ошибка при создании бана: {e}")
                return ""

    async def create_topic(self, user_id: int, title: str,
                          description: str) -> str:
        """Создание темы"""
        query = """
        INSERT INTO topics (user_id, title, description, expires_at)
        VALUES ($1, $2, $3, NOW() + INTERVAL '1 hour')
        RETURNING topic_id
        """

        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchval(query, user_id, title, description)
                return str(result)
            except Exception as e:
                print(f"Ошибка при создании темы: {e}")
                return ""

    async def create_dialog(self, user1_id: int, user2_id: int,
                           topic_id: Optional[str] = None) -> str:
        """Создание диалога"""
        query = """
        INSERT INTO dialogs (user1_id, user2_id, topic_id)
        VALUES ($1, $2, $3)
        RETURNING dialog_id
        """

        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchval(query, user1_id, user2_id, topic_id)
                return str(result)
            except Exception as e:
                print(f"Ошибка при создании диалога: {e}")
                return ""

    async def end_dialog(self, dialog_id: str, reason: str):
        """Завершение диалога"""
        query = """
        UPDATE dialogs
        SET ended_at = NOW(), ended_reason = $2
        WHERE dialog_id = $1
        """

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(query, dialog_id, reason)
            except Exception as e:
                print(f"Ошибка при завершении диалога: {e}")

    async def get_active_bans(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение активных банов пользователя"""
        query = """
        SELECT * FROM bans
        WHERE user_id = $1 AND is_active = TRUE AND expires_at > NOW()
        """

        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch(query, user_id)
                return [dict(row) for row in rows]
            except Exception as e:
                print(f"Ошибка при получении банов: {e}")
                return []

    async def cleanup_expired(self):
        """Очистка истекших записей"""
        queries = [
            "UPDATE bans SET is_active = FALSE WHERE expires_at <= NOW() AND is_active = TRUE",
            "UPDATE topics SET is_active = FALSE WHERE expires_at <= NOW() AND is_active = TRUE"
        ]

        async with self.pool.acquire() as conn:
            for query in queries:
                try:
                    await conn.execute(query)
                except Exception as e:
                    print(f"Ошибка при очистке: {e}")
