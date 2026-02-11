import os
from dotenv import load_dotenv
import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError

async def check_token():
    load_dotenv()
    token = os.getenv('BOT_TOKEN')
    if not token:
        print(' BOT_TOKEN не найден в .env файле')
        return
    print(f'Проверка токена: {token[:5]}...{token[-5:]}')
    bot = Bot(token=token)
    try:
        me = await bot.get_me()
        print(f' Токен валидный! Бот: @{me.username} (ID: {me.id})')
    except TelegramUnauthorizedError:
        print(' Токен невалидный (Unauthorized)')
    except Exception as e:
        print(f' Ошибка: {e}')
    finally:
        await bot.session.close()

asyncio.run(check_token())
