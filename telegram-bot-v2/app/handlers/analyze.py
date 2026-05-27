import re
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

from app.states import AnalyzeStates, ChatStates
from app.keyboards.inline import period_keyboard, after_report_keyboard, cancel_keyboard
from app.services.orchestrator import OrchestratorClient
from app.services.formatter import format_report
from app.services.blockchain import BlockchainVerifier

router = Router()
logger = logging.getLogger(__name__)

ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def is_valid_eth_address(addr: str) -> bool:
    return bool(ETH_ADDRESS_RE.match(addr.strip()))


@router.message(Command("analyze"))
async def cmd_analyze(message: Message, state: FSMContext):
    await state.set_state(AnalyzeStates.waiting_wallet)
    await message.answer(
        "🔑 Введи адрес Ethereum-кошелька:\n"
        "<i>Пример: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


# Перехватываем адрес введённый не через команду (просто вставил в чат)
@router.message(F.text.regexp(r"^0x[a-fA-F0-9]{40}$"))
async def wallet_from_text(message: Message, state: FSMContext):
    current = await state.get_state()
    if current not in (AnalyzeStates.waiting_wallet, None):
        return  # идёт другой процесс

    wallet = message.text.strip()
    await state.update_data(wallet=wallet)
    await state.set_state(AnalyzeStates.waiting_period)
    await message.answer(
        f"✅ Кошелёк принят: <code>{wallet}</code>\n\n"
        "📅 Выбери налоговый период:",
        parse_mode="HTML",
        reply_markup=period_keyboard(),
    )


@router.message(AnalyzeStates.waiting_wallet)
async def handle_wallet_input(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=ReplyKeyboardRemove())
        return

    wallet = message.text.strip() if message.text else ""
    if not is_valid_eth_address(wallet):
        await message.answer(
            "❌ Некорректный адрес. Ethereum-адрес должен начинаться с <code>0x</code> "
            "и содержать 42 символа.\n\nПопробуй ещё раз:",
            parse_mode="HTML",
        )
        return

    await state.update_data(wallet=wallet)
    await state.set_state(AnalyzeStates.waiting_period)
    await message.answer(
        f"✅ Кошелёк: <code>{wallet}</code>\n\n📅 Выбери налоговый период:",
        parse_mode="HTML",
        reply_markup=period_keyboard(),
    )


@router.callback_query(F.data.startswith("period:"), AnalyzeStates.waiting_period)
async def handle_period_choice(callback: CallbackQuery, state: FSMContext):
    period = callback.data.split(":")[1]

    if period == "custom":
        await state.set_state(AnalyzeStates.waiting_custom_period)
        await callback.message.edit_text(
            "✏️ Введи период вручную (например: <code>2023</code> или <code>Q1 2024</code>):",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.answer()
    await _start_analysis(callback.message, state, period, edit=True)


@router.message(AnalyzeStates.waiting_custom_period)
async def handle_custom_period(message: Message, state: FSMContext):
    period = message.text.strip() if message.text else ""
    if not period or len(period) > 20:
        await message.answer("❌ Некорректный период. Попробуй ещё раз:")
        return
    await _start_analysis(message, state, period, edit=False)


async def _start_analysis(message: Message, state: FSMContext, period: str, edit: bool):
    data = await state.get_data()
    wallet = data.get("wallet", "")

    await state.set_state(AnalyzeStates.analyzing)

    text = (
        f"⏳ <b>Анализирую кошелёк...</b>\n\n"
        f"🔑 <code>{wallet}</code>\n"
        f"📅 Период: {period}\n\n"
        f"<i>Это может занять до 1 минуты — идёт запрос к Etherscan, "
        f"CoinGecko и ИИ-классификатор.</i>"
    )

    if edit:
        status_msg = await message.edit_text(text, parse_mode="HTML")
    else:
        status_msg = await message.answer(text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

    client = OrchestratorClient()
    try:
        result = await client.analyze_wallet(
            wallet_address=wallet,
            period=period,
        )

        report_text = format_report(result)

        # Верификация отчёта в блокчейне
        blockchain_text = ""
        try:
            verifier = BlockchainVerifier()
            bc_result = await verifier.submit_report(wallet, result.get("report", {}))
            if not bc_result.get("skipped"):
                tx = bc_result["tx_hash"]
                blockchain_text = (
                    f"\n\n🔗 <b>Записано в блокчейн (Sepolia)</b>\n"
                    f"TX: <a href='https://sepolia.etherscan.io/tx/{tx}'>{tx[:16]}...{tx[-6:]}</a>"
                )
        except Exception as e:
            logger.warning("Ошибка верификации в блокчейне: %s", e)

        # Сохраняем отчёт для последующего чата
        await state.update_data(report=result.get("report", {}), period=period)
        await state.set_state(ChatStates.chatting)

        await status_msg.edit_text(
            report_text + blockchain_text,
            parse_mode="HTML",
            reply_markup=after_report_keyboard(),
        )

    except Exception as e:
        logger.exception("Ошибка при анализе кошелька %s", wallet)
        await state.clear()

        error_detail = str(e)
        if "404" in error_detail:
            msg = "📭 Транзакции не найдены для этого кошелька за выбранный период."
        elif "502" in error_detail:
            msg = "⚠️ Один из сервисов временно недоступен. Попробуй позже."
        else:
            msg = f"❌ Произошла ошибка: <code>{error_detail[:200]}</code>"

        await status_msg.edit_text(
            msg + "\n\nДля нового анализа введи /analyze",
            parse_mode="HTML",
        )


@router.callback_query(F.data == "new_analysis")
async def new_analysis(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AnalyzeStates.waiting_wallet)
    await callback.message.answer(
        "🔑 Введи адрес нового кошелька:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()
