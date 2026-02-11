# bot/storage/redis_client.py
import redis.asyncio as redis
from typing import Optional, Any, Dict, List, Tuple
import json

class RedisClient:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        
    async def initialize(self, url: str, pool_size: int = 10):
        """Инициализация Redis клиента"""
        self.client = redis.from_url(
            url,
            max_connections=pool_size,
            decode_responses=True
        )
        
    async def aclose(self):
        """Закрытие соединения"""
        if self.client:
            await self.client.aclose()
    
    # --- User State Management ---
    async def set_user_state(self, user_id: int, state: str) -> bool:
        """Установка состояния пользователя (атомарно)"""
        key = f"user:{user_id}:state"
        return await self.client.set(key, state, nx=True) or \
               await self.client.set(key, state)
    
    async def get_user_state(self, user_id: int) -> Optional[str]:
        """Получение состояния пользователя"""
        return await self.client.get(f"user:{user_id}:state")
    
    async def delete_user_state(self, user_id: int) -> bool:
        """Удаление состояния пользователя"""
        return await self.client.delete(f"user:{user_id}:state") > 0
    
    # --- Dialog Management ---
    async def create_dialog(self, user1_id: int, user2_id: int, topic_id: Optional[str] = None) -> Optional[str]:
        """Создание диалога (атомарная операция)"""
        script = """
        local user1_key = KEYS[1]
        local user2_key = KEYS[2]
        local search_queue = KEYS[3]
        
        -- Проверяем, что оба пользователя в состоянии SEARCHING
        local state1 = redis.call('GET', user1_key)
        local state2 = redis.call('GET', user2_key)
        
        if state1 ~= 'SEARCHING' or state2 ~= 'SEARCHING' then
            return nil
        end
        
        -- Удаляем пользователей из очереди поиска
        redis.call('LREM', search_queue, 0, ARGV[1])
        redis.call('LREM', search_queue, 0, ARGV[2])
        
        -- Генерируем ID диалога
        local dialog_id = ARGV[3]
        
        -- Создаем запись о диалоге
        local dialog_key = 'dialog:' .. dialog_id
        redis.call('HSET', dialog_key,
            'user1_id', ARGV[1],
            'user2_id', ARGV[2],
            'topic_id', ARGV[4] or '',
            'created_at', ARGV[5]
        )
        
        -- Устанавливаем TTL для диалога (30 минут)
        redis.call('EXPIRE', dialog_key, 1800)
        
        -- Обновляем состояния пользователей
        redis.call('SET', user1_key, 'DIALOG')
        redis.call('SET', user2_key, 'DIALOG')
        
        -- Сохраняем ссылку на диалог
        redis.call('SET', 'user:' .. ARGV[1] .. ':dialog_id', dialog_id)
        redis.call('SET', 'user:' .. ARGV[2] .. ':dialog_id', dialog_id)
        
        return dialog_id
        """
        
        import uuid
        dialog_id = str(uuid.uuid4())
        
        result = await self.client.eval(
            script,
            3,
            f"user:{user1_id}:state",
            f"user:{user2_id}:state",
            "search:queue",
            str(user1_id),
            str(user2_id),
            dialog_id,
            topic_id or "",
            str(datetime.now())
        )
        
        return result
    
    async def get_dialog_partner(self, dialog_id: str, user_id: int) -> Optional[int]:
        """Получение ID собеседника в диалоге"""
        dialog_key = f"dialog:{dialog_id}"
        dialog_data = await self.client.hgetall(dialog_key)
        
        if not dialog_data:
            return None
            
        user1_id = int(dialog_data.get('user1_id', 0))
        user2_id = int(dialog_data.get('user2_id', 0))
        
        return user2_id if user1_id == user_id else user1_id if user2_id == user_id else None
    
    async def end_dialog(self, dialog_id: str, reason: str = "ended_by_user") -> bool:
        """Завершение диалога (атомарно)"""
        script = """
        local dialog_key = KEYS[1]
        
        -- Получаем данные диалога
        local dialog = redis.call('HGETALL', dialog_key)
        if #dialog == 0 then
            return 0
        end
        
        local user1_id = nil
        local user2_id = nil
        
        -- Извлекаем ID пользователей
        for i = 1, #dialog, 2 do
            if dialog[i] == 'user1_id' then
                user1_id = dialog[i+1]
            elseif dialog[i] == 'user2_id' then
                user2_id = dialog[i+1]
            end
        end
        
        if not user1_id or not user2_id then
            return 0
        end
        
        -- Обновляем состояние пользователей
        redis.call('SET', 'user:' .. user1_id .. ':state', 'DIALOG_ENDED')
        redis.call('SET', 'user:' .. user2_id .. ':state', 'DIALOG_ENDED')
        
        -- Удаляем ссылки на диалог
        redis.call('DEL', 'user:' .. user1_id .. ':dialog_id')
        redis.call('DEL', 'user:' .. user2_id .. ':dialog_id')
        
        -- Добавляем причину завершения
        redis.call('HSET', dialog_key, 'ended_reason', ARGV[1])
        
        -- Устанавливаем короткий TTL для cleanup
        redis.call('EXPIRE', dialog_key, 60)
        
        return 1
        """
        
        result = await self.client.eval(
            script,
            1,
            f"dialog:{dialog_id}",
            reason
        )
        
        return bool(result)
    
    # --- Search Queue ---
    async def add_to_search_queue(self, user_id: int) -> bool:
        """Добавление пользователя в очередь поиска (FIFO)"""
        # Проверяем, что пользователь не уже в очереди
        key = f"user:{user_id}:searching"
        
        # SETNX для атомарной проверки
        added = await self.client.set(key, "1", nx=True, ex=30)
        if not added:
            return False
            
        # Добавляем в очередь
        await self.client.lpush("search:queue", str(user_id))
        return True
    
    async def remove_from_search_queue(self, user_id: int) -> bool:
        """Удаление пользователя из очереди поиска"""
        key = f"user:{user_id}:searching"
        await self.client.delete(key)
        
        removed = await self.client.lrem("search:queue", 0, str(user_id))
        return removed > 0
    
    async def find_match(self) -> Optional[Tuple[int, int]]:
        """Поиск пары собеседников (атомарная операция)"""
        script = """
        local queue_key = KEYS[1]
        
        -- Проверяем длину очереди
        local queue_len = redis.call('LLEN', queue_key)
        if queue_len < 2 then
            return nil
        end
        
        -- Берем двух пользователей с конца очереди (FIFO)
        local user2_id = redis.call('RPOP', queue_key)
        local user1_id = redis.call('RPOP', queue_key)
        
        if not user1_id or not user2_id then
            -- Возвращаем обратно, если что-то пошло не так
            if user1_id then
                redis.call('RPUSH', queue_key, user1_id)
            end
            if user2_id then
                redis.call('RPUSH', queue_key, user2_id)
            end
            return nil
        end
        
        -- Удаляем временные ключи поиска
        redis.call('DEL', 'user:' .. user1_id .. ':searching')
        redis.call('DEL', 'user:' .. user2_id .. ':searching')
        
        return {user1_id, user2_id}
        """
        
        result = await self.client.eval(script, 1, "search:queue")
        if result:
            return int(result[0]), int(result[1])
        return None
    
    # --- Topic Management ---
    async def create_topic(self, user_id: int, title: str, description: str) -> str:
        """Создание темы"""
        import uuid
        topic_id = str(uuid.uuid4())
        
        topic_key = f"topic:{topic_id}"
        topic_data = {
            "user_id": str(user_id),
            "title": title,
            "description": description,
            "created_at": str(datetime.now()),
            "view_count": "0"
        }
        
        # Сохраняем тему
        await self.client.hset(topic_key, mapping=topic_data)
        await self.client.expire(topic_key, 3600)  # 1 час TTL
        
        # Добавляем в множество активных тем
        await self.client.sadd("topics:active", topic_id)
        
        # Сохраняем связь пользователь -> тема
        await self.client.set(f"user:{user_id}:topic_id", topic_id)
        
        return topic_id
    
    async def get_random_topic(self, exclude_user_id: int) -> Optional[Dict[str, Any]]:
        """Получение случайной темы (исключая темы пользователя)"""
        # Получаем все активные темы
        topics = await self.client.smembers("topics:active")
        if not topics:
            return None
        
        for topic_id in topics:
            topic_data = await self.client.hgetall(f"topic:{topic_id}")
            if topic_data and int(topic_data.get("user_id", 0)) != exclude_user_id:
                # Увеличиваем счетчик просмотров
                await self.client.hincrby(f"topic:{topic_id}", "view_count", 1)
                return {"topic_id": topic_id, **topic_data}
        
        return None
    
    async def delete_topic(self, topic_id: str) -> bool:
        """Удаление темы"""
        topic_key = f"topic:{topic_id}"
        topic_data = await self.client.hgetall(topic_key)
        
        if not topic_data:
            return False
        
        user_id = topic_data.get("user_id")
        
        # Удаляем тему
        await self.client.delete(topic_key)
        await self.client.srem("topics:active", topic_id)
        
        # Удаляем связь пользователь -> тема
        if user_id:
            await self.client.delete(f"user:{user_id}:topic_id")
        
        return True
    
    # --- Ban Management ---
    async def ban_user(self, user_id: int, duration: int = 3600) -> bool:
        """Бан пользователя"""
        ban_key = f"ban:{user_id}"
        
        # Устанавливаем бан с TTL
        await self.client.set(ban_key, "1", ex=duration)
        
        # Обновляем состояние пользователя
        await self.set_user_state(user_id, "BANNED")
        
        return True
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Проверка, забанен ли пользователь"""
        return await self.client.exists(f"ban:{user_id}") > 0

redis_client = RedisClient()

