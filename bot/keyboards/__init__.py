# bot/keyboards/__init__.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from typing import List

def create_keyboard(buttons: List[str], resize_keyboard: bool = True) -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру с кнопками в один столбец
    """
    keyboard = [[KeyboardButton(text=btn)] for btn in buttons]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=resize_keyboard)

# --- Состояние: IDLE ---
def get_idle_keyboard(has_active_topic: bool = False) -> ReplyKeyboardMarkup:
    if has_active_topic:
        buttons = [
            " Найти собеседника",
            " Смотреть темы",
            " Удалить тему"
        ]
    else:
        buttons = [
            " Найти собеседника",
            " Создать тему",
            " Смотреть темы"
        ]
    return create_keyboard(buttons)

# --- Состояние: SEARCHING ---
def get_searching_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        " Идёт поиск...",
        " Отменить поиск"
    ]
    return create_keyboard(buttons)

# --- Состояние: TOPIC_CREATED ---
def get_topic_created_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        " Найти собеседника",
        " Смотреть темы",
        " Удалить тему"
    ]
    return create_keyboard(buttons)

# --- Состояние: BROWSING_TOPICS ---
def get_browsing_topics_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        " Начать диалог",
        " Следующая тема",
        " Пожаловаться",
        " Назад"
    ]
    return create_keyboard(buttons)

# --- Состояние: DIALOG ---
def get_dialog_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        " Завершить диалог",
        " Пожаловаться"
    ]
    return create_keyboard(buttons)

# --- Состояние: DIALOG_ENDED ---
def get_dialog_ended_keyboard() -> ReplyKeyboardMarkup:
    return get_idle_keyboard(has_active_topic=False)

# --- Состояние: BANNED ---
def get_banned_keyboard() -> ReplyKeyboardMarkup:
    buttons = [" Вы временно ограничены"]
    return create_keyboard(buttons, resize_keyboard=False)
