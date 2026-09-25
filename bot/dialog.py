"""Bot dialog: profile collection (steps 1-3 of the architecture doc) plus
matching and hand-off to the mini-app (steps 3-4).

Every answered step is immediately synced to Postgres via `backend.upsert_profile`,
so a partially-completed dialog is already visible to anything else reading
the same profile (e.g. the mini-app, once it talks to the API instead of its
local mock store).
"""
import logging
from typing import Awaitable, Callable

from maxapi import F
from maxapi.context import MemoryContext
from maxapi.types import BotStarted, CommandStart, MessageCallback, MessageCreated

from bot.api_client import backend
from bot.keyboards import (
    industry_keyboard,
    open_miniapp_keyboard,
    priority_keyboard,
    region_keyboard,
    save_program_keyboard,
    status_keyboard,
)
from bot.options import CLASSIFY_CONFIDENCE_THRESHOLD, OTHER_REGION_LABEL
from bot.states import ProfileForm

logger = logging.getLogger("bot.dialog")

Send = Callable[..., Awaitable[object]]

WELCOME_TEXT = (
    "Привет! Я — навигатор мер поддержки бизнеса 💙\n\n"
    "Отвечу на несколько коротких вопросов и подберу гранты, льготные займы, "
    "субсидии и налоговые льготы, которые подходят именно вам."
)

NO_MATCHES_TEXT = (
    "Пока не нашёл подходящих программ под ваш профиль 🙁\n"
    "Попробуйте другой регион или сферу — отправьте /start, чтобы пройти опрос заново."
)


def _program_card_text(program: dict) -> str:
    lines = [f"📋 {program['name']}", ""]
    if program.get("type"):
        lines.append(f"🏷 Вид поддержки: {program['type']}")
    if program.get("amount"):
        lines.append(f"💰 Сумма: {program['amount']}")
    if program.get("deadline"):
        lines.append(f"⏰ Срок: {program['deadline']}")
    if program.get("conditions"):
        lines.append(f"\nУсловия: {program['conditions']}")
    if program.get("doc_checklist"):
        lines.append("\n📎 Документы:")
        lines += [f"• {doc}" for doc in program["doc_checklist"]]
    if program.get("source_url"):
        lines.append(f"\n🔗 Источник: {program['source_url']}")
    if program.get("is_mock"):
        lines.append("\n⚠️ Тестовые данные (демо-каталог хакатона)")
    return "\n".join(lines)


async def _ask_status(send: Send, context: MemoryContext) -> None:
    await context.set_state(ProfileForm.status)
    await send(text="Какой у вас статус?", attachments=[status_keyboard().as_markup()])


async def _ask_region(send: Send, context: MemoryContext) -> None:
    await context.set_state(ProfileForm.region)
    await send(text="В каком регионе вы работаете?", attachments=[region_keyboard().as_markup()])


async def _ask_industry(send: Send, context: MemoryContext) -> None:
    await context.set_state(ProfileForm.industry)
    await send(
        text="Расскажите о сфере деятельности — выберите вариант или опишите её своими словами:",
        attachments=[industry_keyboard().as_markup()],
    )


async def _ask_priority(send: Send, context: MemoryContext) -> None:
    await context.set_state(ProfileForm.priority)
    await send(text="Что для вас сейчас важнее всего?", attachments=[priority_keyboard().as_markup()])


async def _send_results(send: Send, bot, profile_id: int) -> None:
    programs = await backend.match_programs(profile_id)

    if not programs:
        await send(text=NO_MATCHES_TEXT)
        return

    if len(programs) == 1:
        program = programs[0]
        await send(text=_program_card_text(program), attachments=[save_program_keyboard(program["id"]).as_markup()])
        return

    await send(text=f"Нашёл {len(programs)} подходящие программы поддержки. Сравнить удобнее в приложении 👇")
    me = bot.me
    await send(
        text="Открыть сравнение программ",
        attachments=[open_miniapp_keyboard(me.username, me.user_id).as_markup()],
    )


def register_handlers(dp) -> None:

    @dp.on_started()
    async def _on_started():
        logger.info("Бот навигатора мер поддержки запущен")

    @dp.bot_started()
    async def on_bot_started(event: BotStarted, context: MemoryContext):
        await context.clear()
        await backend.upsert_profile(event.user.user_id)
        await event.bot.send_message(chat_id=event.chat_id, text=WELCOME_TEXT)
        await _ask_status(
            lambda **kw: event.bot.send_message(chat_id=event.chat_id, **kw), context
        )

    @dp.message_created(CommandStart())
    async def on_start(event: MessageCreated, context: MemoryContext):
        await context.clear()
        await backend.upsert_profile(event.message.sender.user_id)
        await event.message.answer(WELCOME_TEXT)
        await _ask_status(event.message.answer, context)

    # --- Шаг 1: статус ---
    @dp.message_callback(ProfileForm.status)
    async def on_status(event: MessageCallback, context: MemoryContext):
        _, value = event.callback.payload.split(":", 1)
        await backend.upsert_profile(event.callback.user.user_id, status=value)
        await event.message.delete()
        await _ask_region(event.message.answer, context)

    # --- Шаг 2: регион ---
    @dp.message_callback(ProfileForm.region)
    async def on_region(event: MessageCallback, context: MemoryContext):
        _, value = event.callback.payload.split(":", 1)
        await event.message.delete()

        if value == OTHER_REGION_LABEL:
            await context.set_state(ProfileForm.region_custom)
            await event.message.answer("Напишите название вашего региона:")
            return

        await backend.upsert_profile(event.callback.user.user_id, region=value)
        await _ask_industry(event.message.answer, context)

    @dp.message_created(F.message.body.text, ProfileForm.region_custom)
    async def on_region_custom(event: MessageCreated, context: MemoryContext):
        value = event.message.body.text.strip()
        await backend.upsert_profile(event.message.sender.user_id, region=value)
        await _ask_industry(event.message.answer, context)

    # --- Шаг 3: сфера деятельности (кнопки, либо текст -> NLP-классификатор) ---
    @dp.message_callback(ProfileForm.industry)
    async def on_industry_callback(event: MessageCallback, context: MemoryContext):
        _, value = event.callback.payload.split(":", 1)
        await backend.upsert_profile(event.callback.user.user_id, industry=value)
        await event.message.delete()
        await _ask_priority(event.message.answer, context)

    @dp.message_created(F.message.body.text, ProfileForm.industry)
    async def on_industry_text(event: MessageCreated, context: MemoryContext):
        industry, confidence = await backend.classify_industry(event.message.body.text)

        if industry and confidence >= CLASSIFY_CONFIDENCE_THRESHOLD:
            await backend.upsert_profile(event.message.sender.user_id, industry=industry)
            await event.message.answer(f"Определил сферу как «{industry}».")
            await _ask_priority(event.message.answer, context)
            return

        await event.message.answer(
            text="Не уверен, что правильно понял сферу — выберите, пожалуйста, из списка:",
            attachments=[industry_keyboard().as_markup()],
        )

    # --- Шаг 4: приоритет -> matching -> выдача результата ---
    @dp.message_callback(ProfileForm.priority)
    async def on_priority(event: MessageCallback, context: MemoryContext):
        _, value = event.callback.payload.split(":", 1)
        profile = await backend.upsert_profile(event.callback.user.user_id, priority=value)

        await context.set_state(None)
        await context.update_data(profile_id=profile["id"])

        await event.message.delete()
        await _send_results(event.message.answer, event.bot, profile["id"])

    # --- «Сохранить» на карточке программы (работает вне состояний формы) ---
    @dp.message_callback(F.callback.payload.contains("save:"))
    async def on_save(event: MessageCallback, context: MemoryContext):
        program_id = int(event.callback.payload.split(":", 1)[1])
        data = await context.get_data()
        profile_id = data.get("profile_id")

        if profile_id is None:
            await event.answer(notification="Не нашёл ваш профиль — отправьте /start")
            return

        await backend.save_application(profile_id, program_id)
        await event.answer(notification="Сохранено в «Мои заявки» ✅")
