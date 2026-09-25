import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import BotCommand

from bot.api_client import backend
from bot.config import settings
from bot.dialog import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot.main")

bot = Bot(settings.MAX_BOT_TOKEN)
dp = Dispatcher()
register_handlers(dp)


async def main() -> None:
    if not settings.MAX_BOT_TOKEN:
        raise RuntimeError(
            "MAX_BOT_TOKEN не задан. Получите токен у @MasterBot в MAX "
            "(https://dev.max.ru/docs) и укажите его в .env."
        )

    await bot.set_my_commands(
        BotCommand(name="/start", description="Начать / пройти опрос заново"),
    )

    try:
        if settings.USE_WEBHOOK:
            await dp.handle_webhook(bot=bot, host=settings.WEBHOOK_HOST, port=settings.WEBHOOK_PORT)
        else:
            await bot.delete_webhook()
            await dp.start_polling(bot)
    finally:
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
