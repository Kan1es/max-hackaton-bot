from maxapi.types import CallbackButton, OpenAppButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from bot.options import PROFILE_INDUSTRY, PROFILE_PRIORITY, PROFILE_REGION, PROFILE_STATUS


def _one_per_row(values: list[str], prefix: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for value in values:
        builder.row(CallbackButton(text=value, payload=f"{prefix}:{value}"))
    return builder


def status_keyboard() -> InlineKeyboardBuilder:
    return _one_per_row(PROFILE_STATUS, "status")


def region_keyboard() -> InlineKeyboardBuilder:
    return _one_per_row(PROFILE_REGION, "region")


def industry_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    options = PROFILE_INDUSTRY
    for i in range(0, len(options), 2):
        pair = options[i:i + 2]
        builder.row(*(CallbackButton(text=v, payload=f"industry:{v}") for v in pair))
    return builder


def priority_keyboard() -> InlineKeyboardBuilder:
    return _one_per_row(PROFILE_PRIORITY, "priority")


def save_program_keyboard(program_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Сохранить", payload=f"save:{program_id}"))
    return builder


def open_miniapp_keyboard(bot_username: str, bot_user_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        OpenAppButton(text="Сравнить в приложении", web_app=bot_username, contact_id=bot_user_id)
    )
    return builder
