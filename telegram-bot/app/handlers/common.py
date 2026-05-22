from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Привет! Я CryptoTax Assistant</b>\n\n"
        "Помогу разобраться с налогами на криптовалюту.\n\n"
        "Введи адрес Ethereum-кошелька — я проанализирую транзакции "
        "и подготовлю налоговый отчёт по правилам НДФЛ РФ 2025.\n\n"
        "📌 Команды:\n"
        "  /analyze — анализ кошелька\n"
        "  /help — справка",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ Нажми /analyze или просто введи адрес кошелька\n"
        "2️⃣ Выбери период (год или квартал)\n"
        "3️⃣ Дождись отчёта — это может занять до минуты\n"
        "4️⃣ Задай вопросы по отчёту прямо в чате\n\n"
        "💡 <b>Что анализируется:</b>\n"
        "  • ETH-транзакции через Etherscan\n"
        "  • Курс ETH/RUB на дату каждой транзакции\n"
        "  • Классификация: DEX-свопы, доход, переводы\n"
        "  • Расчёт НДФЛ по прогрессивной шкале 2025\n\n"
        "⚠️ Бот не является юридической консультацией.",
        parse_mode="HTML",
    )


@router.message(F.text == "❌ Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Отменено. Для нового анализа введи /analyze",
        reply_markup=ReplyKeyboardRemove(),
    )
