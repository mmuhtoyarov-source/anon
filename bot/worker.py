# bot/worker.py
import asyncio
import logging
from datetime import datetime, timedelta
from bot.config import settings
from bot.storage.redis_client import redis_client
from bot.storage.postgres_client import Database

class Worker:
    def __init__(self):
        self.redis = redis_client
        self.db = Database(settings.DATABASE_URL)
        self.running = True
        
    async def process_queue(self):
        """Обработка задач из очереди"""
        while self.running:
            try:
                # Блокирующее чтение из очереди
                task = await self.redis.blpop(settings.QUEUE_NAME, timeout=1)
                
                if task:
                    _, task_data = task
                    await self.handle_task(task_data)
                    
            except Exception as e:
                logging.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)
    
    async def handle_task(self, task_data: str):
        """Обработка конкретной задачи"""
        # Парсим задачу
        # Формат: task_type:data
        parts = task_data.split(":", 1)
        if len(parts) != 2:
            return
            
        task_type, data = parts
        
        try:
            if task_type == "send_message":
                # Отправка сообщения с backoff
                await self.send_message_with_backoff(data)
            elif task_type == "cleanup_dialog":
                # Очистка диалога по TTL
                await self.cleanup_dialog(data)
            elif task_type == "cleanup_topic":
                # Очистка темы по TTL
                await self.cleanup_topic(data)
            elif task_type == "notify":
                # Отложенное уведомление
                await self.send_notification(data)
        except Exception as e:
            logging.error(f"Task handling error: {e}")
    
    async def send_message_with_backoff(self, data: str):
        """Отправка сообщения с экспоненциальным backoff"""
        # Реализация с учетом лимитов Telegram
        pass
    
    async def cleanup_dialog(self, dialog_id: str):
        """Очистка диалога по истечении TTL"""
        # Атомарные операции в Redis
        script = """
        local dialog_key = KEYS[1]
        local user1_key = KEYS[2]
        local user2_key = KEYS[3]
        
        -- Получаем данные диалога
        local dialog_data = redis.call('HGETALL', dialog_key)
        if #dialog_data == 0 then
            return 0
        end
        
        -- Очищаем состояния пользователей
        redis.call('DEL', user1_key)
        redis.call('DEL', user2_key)
        
        -- Удаляем диалог
        redis.call('DEL', dialog_key)
        
        return 1
        """
        
        await self.redis.eval(
            script,
            3,
            f"dialog:{dialog_id}",
            f"user:{dialog_id}:1:state",
            f"user:{dialog_id}:2:state"
        )
    
    async def cleanup_topic(self, topic_id: str):
        """Очистка темы по истечении TTL"""
        # Атомарное удаление темы
        keys = [f"topic:{topic_id}", "topics:active"]
        args = [topic_id]
        
        await self.redis.eval(
            "redis.call('DEL', KEYS[1]); redis.call('SREM', KEYS[2], ARGV[1])",
            len(keys),
            *keys,
            *args
        )
    
    async def send_notification(self, data: str):
        """Отправка уведомления"""
        # Реализация отправки уведомлений
        pass
    
    async def run(self):
        """Основной цикл воркера"""
        await self.redis.initialize(settings.REDIS_URL, settings.REDIS_POOL_SIZE)
        await self.db.connect()
        
        logging.info("Worker started")
        
        try:
            await self.process_queue()
        except KeyboardInterrupt:
            self.running = False
        finally:
            await self.redis.aclose()
            await self.db.disconnect()

async def main():
    if not settings.USE_WORKERS:
        logging.info("Workers are disabled in config")
        return
        
    worker = Worker()
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())

