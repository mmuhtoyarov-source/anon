from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from functools import partial

from bot.storage.redis_client import redis_client
from bot.storage.postgres_client import Database
from bot.keyboards import (
    get_idle_keyboard, get_dialog_keyboard, get_banned_keyboard,
    get_dialog_ended_keyboard
)

async def cmd_start(message: Message, db: Database):
    """Обработчик команды /start"""
    print(f"DEBUG cmd_start: Начало обработки для пользователя {message.from_user.id}")\n    try:\n        await message.answer("Тестовое сообщение от бота")\n        print("DEBUG: Тестовое сообщение отправлено")\n    except Exception as e:\n        print(f"Ошибка отправки тестового сообщения: {e}")
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    try:
        # Регистрируем/обновляем пользователя в БД
        print(f"DEBUG: Регистрируем пользователя {user_id} в БД")
        user_data = await db.get_or_create_user(user_id, username, first_name, last_name)
        print(f"DEBUG: Данные пользователя из БД: {user_data}")
        
        # Проверяем бан
        is_banned = await redis_client.is_user_banned(user_id)
        print(f"DEBUG: Пользователь {user_id} забанен: {is_banned}")
        
        if is_banned:
            print(f"DEBUG: Пользователь {user_id} забанен, отправляем сообщение о бане")
            await message.answer(
                " Вы временно ограничены в использовании бота. Попробуйте позже.",
                reply_markup=get_banned_keyboard()
            )
            await redis_client.set_user_state(user_id, "BANNED")
            return
        
        # Получаем текущее состояние
        state = await redis_client.get_user_state(user_id)
        print(f"DEBUG: Текущее состояние пользователя {user_id}: {state}")
        
        if state in [None, "DIALOG_ENDED"]:
            # Проверяем, есть ли активная тема у пользователя
            try:
                has_active_topic = await redis_client.client.exists(f"user:{user_id}:topic_id") > 0
                print(f"DEBUG: У пользователя {user_id} есть активная тема: {has_active_topic}")
            except Exception as e:
                print(f"DEBUG: Ошибка при проверке активной темы: {e}")
                has_active_topic = False
            
            await redis_client.set_user_state(user_id, "IDLE")
            
            # Создаем клавиатуру
            try:
                keyboard = get_idle_keyboard(has_active_topic)
                print(f"DEBUG: Клавиатура создана успешно")
            except Exception as e:
                print(f"DEBUG: Ошибка при создании клавиатуры: {e}")
                keyboard = None
            
            # Отправляем сообщение
            response = await message.answer(
                " Добро пожаловать в анонимный чат!\n\n"
                "Выберите действие:",
                reply_markup=keyboard
            )
            print(f"DEBUG: Сообщение отправлено пользователю {user_id}, ID сообщения: {response.message_id}")
            
        elif state == "DIALOG":
            await message.answer(
                "Вы уже находитесь в диалоге. Используйте кнопки ниже:",
                reply_markup=get_dialog_keyboard()
            )
        elif state == "BANNED":
            await message.answer(
                " Вы временно ограничены в использовании бота. Попробуйте позже.",
                reply_markup=get_banned_keyboard()
            )
        else:
            # Для других состояний просто показываем соответствующую клавиатуру
            await show_state_keyboard(message, state, user_id)
            
    except Exception as e:
        print(f"ERROR: Исключение в cmd_start: {e}")
        import traceback
        traceback.print_exc()
        # Отправляем простой ответ, чтобы пользователь что-то увидел
        try:
            await message.answer("Произошла ошибка. Попробуйте еще раз.")
        except:
            pass

async def cmd_help(message: Message):
    """Обработчик команды /help"""
    print(f"DEBUG: Получена команда /help от пользователя {message.from_user.id}")
    help_text = ''' <b>Анонимный чат-бот</b>

<b>Основные возможности:</b>
  <b>Поиск собеседника</b> - случайный диалог
  <b>Создание темы</b> - другие смогут найти вас по теме
  <b>Просмотр тем</b> - выбор собеседника по интересам

<b>Правила:</b>
1. Уважайте собеседников
2. Не спамьте
3. Не передавайте личную информацию

<b>Команды:</b>
/start - главное меню
/help - эта справка
/cancel - отмена текущего действия'''
    await message.answer(help_text)
    print(f"DEBUG: Сообщение /help отправлено пользователю {message.from_user.id}")

async def cmd_cancel(message: Message):
    """Обработчик команды /cancel"""
    user_id = message.from_user.id
    state = await redis_client.get_user_state(user_id)
    
    if state == "SEARCHING":
        # Отменяем поиск
        await redis_client.remove_from_search_queue(user_id)
        await redis_client.set_user_state(user_id, "IDLE")
        
        has_active_topic = await redis_client.client.exists(f"user:{user_id}:topic_id") > 0
        await message.answer(
            " Поиск отменен.",
            reply_markup=get_idle_keyboard(has_active_topic)
        )
    else:
        await message.answer("Нечего отменять.")

async def show_state_keyboard(message: Message, state: str, user_id: int):
    """Показ клавиатуры в зависимости от состояния"""
    if state == "IDLE":
        has_active_topic = await redis_client.client.exists(f"user:{user_id}:topic_id") > 0
        await message.answer("Выберите действие:", 
                           reply_markup=get_idle_keyboard(has_active_topic))
    elif state == "DIALOG":
        await message.answer("Вы в диалоге:", 
                           reply_markup=get_dialog_keyboard())
    elif state == "BANNED":
        await message.answer(" Вы временно ограничены.", 
                           reply_markup=get_banned_keyboard())

def register_start_handlers(dp: Dispatcher, db: Database):
    dp.message.register(partial(cmd_start, db=db), CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_cancel, Command("cancel"))
    
    # Обработчик текстовых сообщений для показа клавиатуры
    dp.message.register(
        lambda msg: show_state_keyboard(msg, "IDLE", msg.from_user.id),
        F.text == "Главное меню"
    )

