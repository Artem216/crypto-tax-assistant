from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="2024", callback_data="period:2024"),
            InlineKeyboardButton(text="2023", callback_data="period:2023"),
        ],
        [
            InlineKeyboardButton(text="2025", callback_data="period:2025"),
            InlineKeyboardButton(text="Другой", callback_data="period:custom"),
        ],
    ])


def after_report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Задать вопрос по отчёту", callback_data="start_chat")],
        [InlineKeyboardButton(text="🔄 Анализировать другой кошелёк", callback_data="new_analysis")],
    ])


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
