import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.client.default import DefaultConnectionProperties

from bot.api_client import BackendError, backend
from bot.config import settings
from bot.dialog import register_handlers
from bot.options import set_options

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger("bot.main")

# maxapi authenticates by putting the token in an `access_token` query
# parameter. MAX has deprecated that and now answers 401 with
# "Query parameter access_token is deprecated, use Authorization header",
# which the library surfaces as a misleading InvalidToken("Неверный токен!").
# Passing the header on the underlying aiohttp session fixes it without
# patching the library; the redundant query parameter is accepted alongside it.
bot = Bot(
    settings.MAX_BOT_TOKEN,
    default_connection=DefaultConnectionProperties(
        headers={"Authorization": settings.MAX_BOT_TOKEN},
    ),
)
dp = Dispatcher()
register_handlers(dp)


def _check_config() -> None:
    if not settings.MAX_BOT_TOKEN:
        raise RuntimeError(
            "MAX_BOT_TOKEN не задан. Получите токен у @MasterBot в MAX "
            "(https://dev.max.ru/docs) и укажите его в .env."
        )
    if not settings.SERVICE_TOKEN:
        # Without it the backend only accepts the bot when it is running with
        # REQUIRE_SIGNED_INIT_DATA=False, which is a development-only setting.
        logger.warning(
            "SERVICE_TOKEN не задан — бот сможет обращаться к API только при "
            "REQUIRE_SIGNED_INIT_DATA=False. Для прода задайте общий секрет в .env."
        )


async def main() -> None:
    _check_config()

    # Dialog options come from the backend so the bot, the API and the
    # mini-app can never drift apart. Fail loudly if they can't be loaded:
    # keyboards built from stale local constants are worse than no bot.
    try:
        set_options(await backend.load_options())
    except BackendError as exc:
        await backend.close()
        raise RuntimeError(f"Бэкенд недоступен: {exc}") from exc
    logger.info("Опции диалога загружены из %s", settings.BACKEND_BASE_URL)

    # No set_my_commands here: MAX now serves only GET on /me and answers
    # 404 "Path /me is not recognized" to the PATCH that maxapi sends, which
    # logged an alarming error on every startup for no benefit. The command
    # list is configured in @MasterBot instead.

    try:
        if settings.USE_WEBHOOK:
            await dp.handle_webhook(bot=bot, host=settings.WEBHOOK_HOST, port=settings.WEBHOOK_PORT)
        else:
            await bot.delete_webhook()
            await dp.start_polling(bot)
    finally:
        await backend.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
