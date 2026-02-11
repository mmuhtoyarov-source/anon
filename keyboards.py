from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


BTN_FIND = "Найти собеседника"
BTN_CREATE_TOPIC = "Создать тему"
BTN_BROWSE_TOPICS = "Смотреть темы"
BTN_CANCEL_SEARCH = "Отменить поиск"
BTN_CANCEL = "Отменить"
BTN_CONFIRM = "Подтвердить"
BTN_START_DIALOG = "Начать диалог"
BTN_NEXT_TOPIC = "Следующая тема"
BTN_REPORT = "Пожаловаться"
BTN_BACK = "Назад"
BTN_END_DIALOG = "Завершить диалог"



def one_col_keyboard(*labels: str) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=label)] for label in labels]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


MAIN_MENU_KB = one_col_keyboard(BTN_FIND, BTN_CREATE_TOPIC, BTN_BROWSE_TOPICS)
SEARCHING_KB = one_col_keyboard(BTN_CANCEL_SEARCH)
CREATE_TOPIC_KB = one_col_keyboard(BTN_CANCEL)
CONFIRM_TOPIC_KB = one_col_keyboard(BTN_CONFIRM, BTN_CANCEL)
BROWSE_TOPICS_KB = one_col_keyboard(BTN_START_DIALOG, BTN_NEXT_TOPIC, BTN_REPORT, BTN_BACK)
DIALOG_KB = one_col_keyboard(BTN_END_DIALOG, BTN_REPORT)
BANNED_KB = one_col_keyboard("Вы временно заблокированы")