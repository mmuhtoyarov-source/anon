import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Telegram
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_POOL_SIZE = 10
    
    # PostgreSQL
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/anon_chat')
    
    # Настройки приложения
    SEARCH_TIMEOUT = 20  # секунд
    TOPIC_TTL = 3600  # 1 час в секундах
    DIALOG_INACTIVITY_TTL = 1800  # 30 минут
    BAN_DURATION = 3600  # 1 час
    MESSAGES_PER_SECOND = 30.0  # Лимит Telegram
    
    # Воркеры (опционально)
    USE_WORKERS = os.getenv('USE_WORKERS', 'false').lower() == 'true'
    QUEUE_NAME = "anon_chat_queue"

settings = Settings()
