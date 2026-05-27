import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from app.handlers import common, analyze, chat

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(common.router)
    dp.include_router(analyze.router)
    dp.include_router(chat.router)

    logger.info("Бот запущен")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
