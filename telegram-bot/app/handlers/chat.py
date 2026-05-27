import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.states import ChatStates, AnalyzeStates
from app.keyboards.inline import cancel_keyboard
from app.services.orchestrator import OrchestratorClient

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "start_chat", ChatStates.chatting)
async def start_chat(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💬 <b>Режим вопросов по отчёту</b>\n\n"
        "Задай любой вопрос по своим транзакциям и налогам.\n"
        "Например: <i>«Почему эта транзакция облагается налогом?»</i> "
        "или <i>«Как уменьшить налоговую базу?»</i>\n\n"
        "Для нового анализа: /analyze",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(ChatStates.chatting, F.text)
async def handle_chat_message(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        from aiogram.types import ReplyKeyboardRemove
        await message.answer("Готово. Для нового анализа: /analyze", reply_markup=ReplyKeyboardRemove())
        return

    data = await state.get_data()
    wallet = data.get("wallet", "")
    report = data.get("report", {})

    if not report:
        await message.answer("Нет активного отчёта. Запусти /analyze сначала.")
        return

    thinking = await message.answer("🤔 Думаю...")

    client = OrchestratorClient()
    try:
        answer = await client.chat(
            wallet_address=wallet,
            question=message.text,
            report=report,
        )
        await thinking.edit_text(answer)
    except Exception as e:
        logger.exception("Ошибка в чате")
        await thinking.edit_text(f"❌ Ошибка: {str(e)[:200]}")
