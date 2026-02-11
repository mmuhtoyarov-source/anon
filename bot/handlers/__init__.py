# bot/handlers/__init__.py
from aiogram import Dispatcher
from .start import register_start_handlers
from .search import register_search_handlers
from .topics import register_topics_handlers
from .dialogs import register_dialogs_handlers
from .admin import register_admin_handlers

def register_handlers(dp: Dispatcher, db):
    """Регистрация всех обработчиков"""
    register_start_handlers(dp, db)
    register_search_handlers(dp, db)
    register_topics_handlers(dp, db)
    register_dialogs_handlers(dp, db)
    register_admin_handlers(dp, db)
