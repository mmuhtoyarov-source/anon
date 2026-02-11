# bot/handlers/topics.py
from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.storage.redis_client import redis_client
from bot.storage.postgres_client import Database
from bot.keyboards import (
    get_idle_keyboard, get_topic_created_keyboard,
    get_browsing_topics_keyboard, get_dialog_keyboard
)
from bot.config import settings

class TopicCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()

async def create_topic_start(message: Message, state: FSMContext):
    """Начало создания темы"""
    user_id = message.from_user.id
    
    # Проверяем, есть ли уже активная тема
    has_active_topic = await redis_client.client.exists(f"user:{user_id}:topic_id") > 0
    if has_active_topic:
        await message.answer(
            "У вас уже есть активная тема. Удалите ее сначала.",
            reply_markup=get_topic_created_keyboard()
        )
        return
    
    await state.set_state(TopicCreation.waiting_for_title)
    await message.answer(" Введите название темы (до 200 символов):")

async def process_topic_title(message: Message, state: FSMContext):
    """Обработка названия темы"""
    if len(message.text) > 200:
        await message.answer("Название слишком длинное. Введите до 200 символов:")
        return
    
    await state.update_data(title=message.text)
    await state.set_state(TopicCreation.waiting_for_description)
    await message.answer(" Теперь введите описание темы:")

async def process_topic_description(message: Message, state: FSMContext, db: Database):
    """Обработка описания темы и создание"""
    user_id = message.from_user.id
    data = await state.get_data()
    
    # Создаем тему в Redis
    topic_id = await redis_client.create_topic(
        user_id,
        data['title'],
        message.text
    )
    
    # Сохраняем в PostgreSQL
    await db.create_topic(user_id, data['title'], message.text)
    
    await state.clear()
    await redis_client.set_user_state(user_id, "TOPIC_CREATED")
    
    await message.answer(
        f" Тема создана!\n\n"
        f"<b>{data['title']}</b>\n"
        f"{message.text}\n\n"
        f"Тема будет активна {settings.TOPIC_TTL // 60} минут.",
        reply_markup=get_topic_created_keyboard()
    )

async def delete_topic(message: Message, db: Database):
    """Удаление активной темы"""
    user_id = message.from_user.id
    
    # Получаем ID темы
    topic_id = await redis_client.client.get(f"user:{user_id}:topic_id")
    if not topic_id:
        await message.answer("У вас нет активной темы.")
        return
    
    # Удаляем тему
    deleted = await redis_client.delete_topic(topic_id)
    if deleted:
        await redis_client.set_user_state(user_id, "IDLE")
        await message.answer(
            " Тема удалена.",
            reply_markup=get_idle_keyboard(has_active_topic=False)
        )

async def browse_topics(message: Message):
    """Просмотр тем"""
    user_id = message.from_user.id
    
    # Получаем случайную тему (исключая свои)
    topic = await redis_client.get_random_topic(user_id)
    
    if not topic:
        await message.answer(
            " Нет доступных тем. Создайте свою тему первым!",
            reply_markup=get_idle_keyboard(
                has_active_topic=await redis_client.client.exists(f"user:{user_id}:topic_id") > 0
            )
        )
        return
    
    await redis_client.set_user_state(user_id, "BROWSING_TOPICS")
    
    # Сохраняем текущую тему в сессии пользователя
    await redis_client.client.set(
        f"user:{user_id}:current_topic",
        topic['topic_id'],
        ex=300  # 5 минут TTL
    )
    
    topic_text = f"<b>{topic['title']}</b>\n\n{topic['description']}\n\n Просмотров: {topic['view_count']}"
    await message.answer(
        topic_text,
        reply_markup=get_browsing_topics_keyboard()
    )

async def next_topic(message: Message):
    """Следующая тема"""
    user_id = message.from_user.id
    
    # Получаем следующую случайную тему
    topic = await redis_client.get_random_topic(user_id)
    
    if not topic:
        await message.answer("Больше нет доступных тем.")
        return
    
    # Обновляем текущую тему
    await redis_client.client.set(
        f"user:{user_id}:current_topic",
        topic['topic_id'],
        ex=300
    )
    
    topic_text = f"<b>{topic['title']}</b>\n\n{topic['description']}\n\n Просмотров: {topic['view_count']}"
    await message.answer(
        topic_text,
        reply_markup=get_browsing_topics_keyboard()
    )

async def start_dialog_from_topic(message: Message, db: Database):
    """Начало диалога с автором темы"""
    user_id = message.from_user.id
    
    # Получаем текущую тему
    topic_id = await redis_client.client.get(f"user:{user_id}:current_topic")
    if not topic_id:
        await message.answer("Тема не найдена. Попробуйте выбрать другую.")
        return
    
    # Получаем данные темы
    topic_data = await redis_client.client.hgetall(f"topic:{topic_id}")
    if not topic_data:
        await message.answer("Тема не найдена.")
        return
    
    author_id = int(topic_data.get('user_id', 0))
    
    # Проверяем, доступен ли автор
    author_state = await redis_client.get_user_state(author_id)
    if author_state != "IDLE" and author_state != "TOPIC_CREATED":
        await message.answer(" Автор темы сейчас недоступен.")
        return
    
    # Пытаемся создать диалог
    dialog_id = await redis_client.create_dialog(user_id, author_id, topic_id)
    if dialog_id:
        await db.create_dialog(user_id, author_id, topic_id)
        
        # Делаем тему неактивной
        await redis_client.delete_topic(topic_id)
        
        # Уведомляем пользователей
        await notify_topic_dialog_started(user_id, author_id, topic_data['title'])
    else:
        await message.answer("Не удалось начать диалог. Попробуйте позже.")

async def notify_topic_dialog_started(user1_id: int, user2_id: int, topic_title: str):
    """Уведомление о начале диалога по теме"""
    message_text = f" Начался диалог по теме: <b>{topic_title}</b>\n\nОбщайтесь анонимно."
    
    for uid in [user1_id, user2_id]:
        await send_message_to_user(uid, message_text, get_dialog_keyboard())

async def back_from_browsing(message: Message):
    """Возврат из просмотра тем"""
    user_id = message.from_user.id
    
    # Проверяем, есть ли активная тема
    has_active_topic = await redis_client.client.exists(f"user:{user_id}:topic_id") > 0
    
    if has_active_topic:
        await redis_client.set_user_state(user_id, "TOPIC_CREATED")
        await message.answer(
            "Возврат в меню темы.",
            reply_markup=get_topic_created_keyboard()
        )
    else:
        await redis_client.set_user_state(user_id, "IDLE")
        await message.answer(
            "Возврат в главное меню.",
            reply_markup=get_idle_keyboard(has_active_topic=False)
        )

async def send_message_to_user(user_id: int, text: str, keyboard):
    """Отправка сообщения пользователю (заглушка)"""
    pass

def register_topics_handlers(dp: Dispatcher, db: Database):
    dp.message.register(create_topic_start, F.text == " Создать тему")
    dp.message.register(process_topic_title, TopicCreation.waiting_for_title)
    dp.message.register(
        lambda msg, state: process_topic_description(msg, state, db),
        TopicCreation.waiting_for_description
    )
    dp.message.register(delete_topic, F.text == " Удалить тему")
    dp.message.register(browse_topics, F.text == " Смотреть темы")
    dp.message.register(next_topic, F.text == " Следующая тема")
    dp.message.register(
        lambda msg: start_dialog_from_topic(msg, db),
        F.text == " Начать диалог"
    )
    dp.message.register(back_from_browsing, F.text == " Назад")
