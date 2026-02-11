from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    bot_token: str
    redis_url: str
    postgres_dsn: str
    search_timeout_seconds: int = 20
    topic_ttl_seconds: int = 3600
    dialog_ttl_seconds: int = 3600
    ban_ttl_seconds: int = 3600
    cooldown_seconds: int = 3
    log_level: str = "INFO"



def load_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        postgres_dsn=os.getenv("POSTGRES_DSN", "postgresql://anon:anon@localhost:5432/anon_chat"),
        search_timeout_seconds=int(os.getenv("SEARCH_TIMEOUT_SECONDS", "20")),
        topic_ttl_seconds=int(os.getenv("TOPIC_TTL_SECONDS", "3600")),
        dialog_ttl_seconds=int(os.getenv("DIALOG_TTL_SECONDS", "3600")),
        ban_ttl_seconds=int(os.getenv("BAN_TTL_SECONDS", "3600")),
        cooldown_seconds=int(os.getenv("COOLDOWN_SECONDS", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )