import asyncpg
import asyncio
import sys

async def init_database():
    try:
        # Подключаемся к PostgreSQL
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='postgres'  # Подключаемся к стандартной базе данных
        )
        
        # Проверяем, существует ли база данных anon_chat
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'anon_chat'"
        )
        
        if not db_exists:
            print("Создаем базу данных 'anon_chat'...")
            await conn.execute("CREATE DATABASE anon_chat")
            print("База данных создана.")
        
        await conn.close()
        
        # Теперь подключаемся к anon_chat и создаем таблицы
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='anon_chat'
        )
        
        # Создаем таблицы
        print("Создаем таблицы...")
        
        await conn.execute('''
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ban_count INTEGER DEFAULT 0
            );
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS bans (
                ban_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                reason VARCHAR(500),
                banned_by BIGINT REFERENCES users(user_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            );
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                topic_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                view_count INTEGER DEFAULT 0
            );
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS dialogs (
                dialog_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                user1_id BIGINT REFERENCES users(user_id),
                user2_id BIGINT REFERENCES users(user_id),
                topic_id UUID REFERENCES topics(topic_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                ended_reason VARCHAR(100)
            );
        ''')
        
        print("Таблицы созданы успешно.")
        
        # Закрываем соединение
        await conn.close()
        print("Инициализация базы данных завершена.")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_database())
