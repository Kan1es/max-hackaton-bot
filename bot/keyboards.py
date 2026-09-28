from typing import List

from maxapi.types import CallbackButton, OpenAppButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from bot.options import get_options


def _one_per_row(values: List[str], prefix: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for value in values:
        builder.row(CallbackButton(text=value, payload=f"{prefix}:{value}"))
    return builder


def status_keyboard() -> InlineKeyboardBuilder:
    return _one_per_row(get_options().status, "status")


def region_keyboard() -> InlineKeyboardBuilder:
    return _one_per_row(get_options().region, "region")


def industry_keyboard() -> InlineKeyboardBuilder:
    """Two per row — there are seven industries and the labels are short."""
    builder = InlineKeyboardBuilder()
    options = get_options().industry
    for i in range(0, len(options), 2):
        pair = options[i:i + 2]
        builder.row(*(CallbackButton(text=v, payload=f"industry:{v}") for v in pair))
    return builder


def priority_keyboard() -> InlineKeyboardBuilder:
    return _one_per_row(get_options().priority, "priority")


def save_program_keyboard(program_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="⭐ Сохранить", payload=f"save:{program_id}"))
    return builder


def program_refs_keyboard(programs: List[dict]) -> InlineKeyboardBuilder:
    """One button per program the AI consultant referred to."""
    builder = InlineKeyboardBuilder()
    for program in programs:
        title = program["title"]
        if len(title) > 60:
            title = title[:57] + "…"
        builder.row(CallbackButton(text=f"📋 {title}", payload=f"program:{program['id']}"))
    return builder


def open_miniapp_keyboard(bot_username: str, bot_user_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        OpenAppButton(text="Сравнить в приложении", web_app=bot_username, contact_id=bot_user_id)
    )
    return builder
