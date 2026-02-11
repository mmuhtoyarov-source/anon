# bot/handlers/dialogs.py
from aiogram import Dispatcher, F
from aiogram.types import Message, ContentType

from bot.storage.redis_client import redis_client
from bot.storage.postgres_client import Database
from bot.keyboards import get_dialog_ended_keyboard, get_idle_keyboard
from bot.config import settings

async def end_dialog(message: Message, db: Database):
    """Завершение диалога"""
    user_id = message.from_user.id
    
    # Получаем ID диалога
    dialog_id = await redis_client.client.get(f"user:{user_id}:dialog_id")
    if not dialog_id:
        await message.answer("Вы не в диалоге.")
        return
    
    # Завершаем диалог в Redis
    ended = await redis_client.end_dialog(dialog_id, "ended_by_user")
    if ended:
        # Сохраняем в PostgreSQL
        await db.end_dialog(dialog_id, "ended_by_user")
        
        await redis_client.set_user_state(user_id, "DIALOG_ENDED")
        
        # Отправляем уведомление собеседнику
        partner_id = await redis_client.get_dialog_partner(dialog_id, user_id)
        if partner_id:
            await notify_partner_about_end(partner_id, "Собеседник завершил диалог.")
        
        await message.answer(
            " Диалог завершен.",
            reply_markup=get_dialog_ended_keyboard()
        )

async def report_user(message: Message, db: Database):
    """Жалоба на собеседника"""
    user_id = message.from_user.id
    
    # Получаем ID диалога
    dialog_id = await redis_client.client.get(f"user:{user_id}:dialog_id")
    if not dialog_id:
        await message.answer("Вы не в диалоге.")
        return
    
    # Получаем собеседника
    partner_id = await redis_client.get_dialog_partner(dialog_id, user_id)
    if not partner_id:
        await message.answer("Собеседник не найден.")
        return
    
    # Баним собеседника
    await redis_client.ban_user(partner_id, settings.BAN_DURATION)
    
    # Сохраняем бан в БД
    await db.create_ban(partner_id, "Жалоба от пользователя", user_id, 1)
    
    # Завершаем диалог
    await redis_client.end_dialog(dialog_id, "report")
    await db.end_dialog(dialog_id, "report")
    
    await message.answer(
        " Жалоба отправлена. Собеседник заблокирован на 1 час.",
        reply_markup=get_dialog_ended_keyboard()
    )

async def forward_message(message: Message):
    """Пересылка сообщения собеседнику"""
    user_id = message.from_user.id
    
    # Проверяем, что пользователь в диалоге
    state = await redis_client.get_user_state(user_id)
    if state != "DIALOG":
        return
    
    # Получаем ID диалога
    dialog_id = await redis_client.client.get(f"user:{user_id}:dialog_id")
    if not dialog_id:
        return
    
    # Получаем собеседника
    partner_id = await redis_client.get_dialog_partner(dialog_id, user_id)
    if not partner_id:
        await message.answer("Собеседник не найден.")
        return
    
    # Обновляем TTL диалога при активности
    await redis_client.client.expire(f"dialog:{dialog_id}", settings.DIALOG_INACTIVITY_TTL)
    
    # Пересылаем сообщение (в реальной реализации)
    await forward_to_partner(partner_id, message)

async def forward_to_partner(partner_id: int, message: Message):
    """Пересылка сообщения партнеру (заглушка)"""
    # В реальной реализации здесь будет отправка через бота
    pass

async def notify_partner_about_end(partner_id: int, reason: str):
    """Уведомление партнера о завершении диалога"""
    await redis_client.set_user_state(partner_id, "DIALOG_ENDED")
    
    # Отправляем сообщение (в реальной реализации)
    pass

def register_dialogs_handlers(dp: Dispatcher, db: Database):
    dp.message.register(end_dialog, F.text == " Завершить диалог")
    dp.message.register(
        lambda msg: report_user(msg, db),
        F.text == " Пожаловаться"
    )
    
    # Обработка медиа-сообщений в диалоге
    dp.message.register(
        forward_message,
        F.content_type.in_([
            ContentType.TEXT,
            ContentType.VOICE,
            ContentType.VIDEO,
            ContentType.PHOTO,
            ContentType.STICKER
        ])
    )
