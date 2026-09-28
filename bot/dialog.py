"""Bot dialog: profile collection, matching, and hand-off to the mini-app.

Every answered step is synced to Postgres immediately, so a half-finished
dialog is already visible to the mini-app, which reads the same profile
through the same API.

Once the profile is filled, any free-text message goes to the AI consultant
(POST /assistant/ask), which answers from the same catalog and returns the
programs it relied on as buttons that open the full cards.
"""
import asyncio
import logging
from typing import Awaitable, Callable, List, Optional

from maxapi import F
from maxapi.context import MemoryContext
from maxapi.enums.sender_action import SenderAction
from maxapi.types import BotStarted, Command, CommandStart, MessageCallback, MessageCreated

from bot.api_client import BackendError, backend
from bot.config import settings
from bot.keyboards import (
    industry_keyboard,
    open_miniapp_keyboard,
    priority_keyboard,
    program_refs_keyboard,
    region_keyboard,
    save_program_keyboard,
    status_keyboard,
)
from bot.options import get_options
from bot.states import ProfileForm

logger = logging.getLogger("bot.dialog")

Send = Callable[..., Awaitable[object]]

WELCOME_TEXT = (
    "Привет! Я — навигатор мер поддержки бизнеса 💙\n\n"
    "Отвечу на несколько коротких вопросов и подберу гранты, льготные займы, "
    "субсидии и налоговые льготы, которые подходят именно вам.\n\n"
    "А ещё я умею отвечать на вопросы: просто напишите, что хотите узнать, — "
    "ИИ-консультант ответит по каталогу программ."
)

HELP_TEXT = (
    "Что я умею:\n\n"
    "/start — пройти опрос заново и подобрать программы\n"
    "/my — мои сохранённые программы\n"
    "/help — эта справка\n\n"
    "💬 Или просто задайте вопрос своими словами, например:\n"
    "• «Какие гранты есть для самозанятых?»\n"
    "• «Какие документы нужны для льготного займа?»\n"
    "• «Чем субсидия отличается от гранта?»"
)

ASSISTANT_HINT = (
    "💬 Остались вопросы? Напишите их прямо сюда — например, "
    "«какие документы нужны для первой программы?». ИИ-консультант ответит по каталогу."
)

ASSISTANT_DISCLAIMER = "🤖 Ответ ИИ — перед подачей сверьте условия у организатора."

FORM_REMINDER = "Чтобы продолжить подбор, выберите вариант в сообщении выше или отправьте /start."

APPLICATION_STATUS_LABELS = {
    "saved": "⭐ сохранено",
    "in_progress": "📝 готовлю документы",
    "submitted": "📨 заявка подана",
}

# MAX rejects messages longer than 4000 characters.
MAX_MESSAGE_LENGTH = 4000
# How many previous messages (user + assistant) the consultant sees.
ASSISTANT_HISTORY_TURNS = 6
TYPING_REFRESH_SECONDS = 4.0

NO_MATCHES_TEXT = (
    "Пока не нашёл подходящих программ под ваш профиль 🙁\n"
    "Попробуйте другой регион или сферу — отправьте /start, чтобы пройти опрос заново."
)

BACKEND_ERROR_TEXT = (
    "Не получилось связаться с сервисом подбора 😔\n"
    "Попробуйте ещё раз через минуту или отправьте /start."
)


def _program_card_text(program: dict, position: Optional[int] = None, total: Optional[int] = None) -> str:
    header = f"📋 {program.get('short_title') or program['name']}"
    if position and total:
        header = f"{position}/{total} · {header}"
    lines = [header, ""]

    if program.get("short_title"):
        lines.append(f"Официальное название: {program['name']}\n")
    if program.get("description"):
        lines.append(f"{program['description']}\n")
    if program.get("reasons"):
        lines.append("✅ Почему подходит: " + ", ".join(program["reasons"]))
    if program.get("type"):
        lines.append(f"🏷 Вид поддержки: {program['type']}")
    if program.get("amount"):
        lines.append(f"💰 Сумма: {program['amount']}")
    if program.get("deadline"):
        lines.append(f"⏰ Срок: {program['deadline']}")
    if program.get("eligible_status"):
        lines.append(f"👤 Кто может получить: {program['eligible_status']}")
    if program.get("conditions"):
        lines.append(f"\nУсловия: {program['conditions']}")
    if program.get("doc_checklist"):
        lines.append("\n📎 Документы:")
        lines += [f"• {doc}" for doc in program["doc_checklist"]]
    if program.get("source_url"):
        lines.append(f"\n🔗 Источник: {program['source_url']}")
    if program.get("is_mock"):
        checked = program.get("checked_at")
        suffix = f" · данные проверены {checked}" if checked else ""
        lines.append(f"\n⚠️ Тестовые данные демо-каталога{suffix}. "
                     "Перед подачей проверьте условия у организатора.")
    return _fit_message("\n".join(lines))


def _fit_message(text: str) -> str:
    if len(text) <= MAX_MESSAGE_LENGTH:
        return text
    return text[:MAX_MESSAGE_LENGTH - 1].rstrip() + "…"


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


async def _send_miniapp_invite(send: Send, bot) -> None:
    """Offer the mini-app, falling back to a plain link if the native button
    can't be built (the bot's own identity isn't always resolved yet)."""
    try:
        me = bot.me
        await send(
            text="Сравнить программы бок о бок и отметить документы удобнее в приложении 👇",
            attachments=[open_miniapp_keyboard(me.username, me.user_id).as_markup()],
        )
        return
    except Exception:
        logger.warning("Не удалось собрать кнопку mini app", exc_info=True)

    if settings.MINIAPP_URL:
        await send(text=f"Сравнить программы в приложении: {settings.MINIAPP_URL}")


async def _send_results(send: Send, bot, max_user_id: int) -> None:
    """Send every matched program as its own card with a Save button.

    Previously only the single-result case produced cards, so the common
    top-3 answer showed no programs at all and the Save button was
    unreachable — which in turn meant "Мои заявки" could never fill up.
    """
    programs = await backend.match_programs(max_user_id)

    if not programs:
        await send(text=NO_MATCHES_TEXT)
        return

    await send(text=f"Нашёл подходящие программы: {len(programs)}. Вот они 👇")

    total = len(programs)
    for position, program in enumerate(programs, start=1):
        await send(
            text=_program_card_text(program, position, total),
            attachments=[save_program_keyboard(program["id"]).as_markup()],
        )

    if total > 1:
        await _send_miniapp_invite(send, bot)

    await send(text=ASSISTANT_HINT)


async def _keep_typing(bot, chat_id: int) -> None:
    """Hold the "typing…" indicator while the consultant thinks.

    MAX drops the indicator after a few seconds, and a free LLM may take
    much longer than that under load, so it is refreshed periodically.
    """
    while True:
        try:
            await bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
        except Exception:
            logger.debug("Не удалось отправить индикатор набора", exc_info=True)
        await asyncio.sleep(TYPING_REFRESH_SECONDS)


async def _answer_question(event: MessageCreated, context: MemoryContext, question: str) -> None:
    user_id = event.message.sender.user_id
    data = await context.get_data()
    history: List[dict] = data.get("ai_history", [])

    typing = asyncio.create_task(_keep_typing(event.bot, event.message.recipient.chat_id))
    try:
        reply = await backend.ask_assistant(user_id, question, history)
    except BackendError:
        await event.message.answer(BACKEND_ERROR_TEXT)
        return
    finally:
        typing.cancel()

    answer = reply.get("answer") or ""
    programs = reply.get("programs") or []

    text = answer if reply.get("is_stub") else f"{answer}\n\n{ASSISTANT_DISCLAIMER}"
    attachments = [program_refs_keyboard(programs).as_markup()] if programs else []
    await event.message.answer(text=_fit_message(text), attachments=attachments)

    # Only real LLM answers go into the history: a keyword-search stub is not
    # something the model said and would only confuse it on the next turn.
    if not reply.get("is_stub"):
        history = history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer[:1500]},
        ]
        await context.update_data(ai_history=history[-ASSISTANT_HISTORY_TURNS:])


def register_handlers(dp) -> None:

    @dp.on_started()
    async def _on_started():
        logger.info("Бот навигатора мер поддержки запущен")

    @dp.bot_started()
    async def on_bot_started(event: BotStarted, context: MemoryContext):
        send = lambda **kw: event.bot.send_message(chat_id=event.chat_id, **kw)
        try:
            await context.clear()
            await backend.upsert_profile(event.user.user_id)
            await send(text=WELCOME_TEXT)
            await _ask_status(send, context)
        except BackendError:
            await send(text=BACKEND_ERROR_TEXT)

    @dp.message_created(CommandStart())
    async def on_start(event: MessageCreated, context: MemoryContext):
        try:
            await context.clear()
            await backend.upsert_profile(event.message.sender.user_id)
            await event.message.answer(WELCOME_TEXT)
            await _ask_status(event.message.answer, context)
        except BackendError:
            await event.message.answer(BACKEND_ERROR_TEXT)

    # --- Команды (до шагов анкеты, чтобы текстовые шаги их не перехватили) ---
    @dp.message_created(Command("help"))
    async def on_help(event: MessageCreated, context: MemoryContext):
        await event.message.answer(HELP_TEXT)

    @dp.message_created(Command("my"))
    async def on_my(event: MessageCreated, context: MemoryContext):
        try:
            applications = await backend.list_applications(event.message.sender.user_id)
        except BackendError:
            await event.message.answer(BACKEND_ERROR_TEXT)
            return

        if not applications:
            await event.message.answer(
                "Сохранённых программ пока нет. Нажмите «⭐ Сохранить» на карточке программы — "
                "она появится здесь и в приложении."
            )
            return

        refs = []
        lines = [f"Мои заявки: {len(applications)}", ""]
        for application in applications:
            program = application.get("program") or {}
            title = program.get("short_title") or program.get("name") or f"Программа #{application['program_id']}"
            status = APPLICATION_STATUS_LABELS.get(application["status"], application["status"])
            docs_total = len(program.get("doc_checklist") or [])
            docs = f" · документы {len(application.get('checked_docs') or [])}/{docs_total}" if docs_total else ""
            lines.append(f"• {title} — {status}{docs}")
            refs.append({"id": application["program_id"], "title": title})

        await event.message.answer(
            text=_fit_message("\n".join(lines)),
            attachments=[program_refs_keyboard(refs).as_markup()],
        )
        await _send_miniapp_invite(event.message.answer, event.bot)

    # --- Шаг 1: статус ---
    @dp.message_callback(F.callback.payload.startswith("status:"), ProfileForm.status)
    async def on_status(event: MessageCallback, context: MemoryContext):
        _, value = event.callback.payload.split(":", 1)
        try:
            await backend.upsert_profile(event.callback.user.user_id, status=value)
        except BackendError:
            await event.answer(notification="Сервис недоступен, попробуйте ещё раз")
            return
        await event.message.delete()
        await _ask_region(event.message.answer, context)

    # --- Шаг 2: регион ---
    @dp.message_callback(F.callback.payload.startswith("region:"), ProfileForm.region)
    async def on_region(event: MessageCallback, context: MemoryContext):
        _, value = event.callback.payload.split(":", 1)
        await event.message.delete()

        if value == get_options().other_region_label:
            await context.set_state(ProfileForm.region_custom)
            await event.message.answer("Напишите название вашего региона:")
            return

        try:
            await backend.upsert_profile(event.callback.user.user_id, region=value)
        except BackendError:
            await event.message.answer(BACKEND_ERROR_TEXT)
            return
        await _ask_industry(event.message.answer, context)

    @dp.message_created(F.message.body.text, ProfileForm.region_custom)
    async def on_region_custom(event: MessageCreated, context: MemoryContext):
        value = event.message.body.text.strip()
        if not value:
            await event.message.answer("Название региона не может быть пустым — попробуйте ещё раз:")
            return
        try:
            await backend.upsert_profile(event.message.sender.user_id, region=value)
        except BackendError:
            await event.message.answer(BACKEND_ERROR_TEXT)
            return
        await _ask_industry(event.message.answer, context)

    # --- Шаг 3: сфера деятельности (кнопки, либо текст -> NLP-классификатор) ---
    @dp.message_callback(F.callback.payload.startswith("industry:"), ProfileForm.industry)
    async def on_industry_callback(event: MessageCallback, context: MemoryContext):
        _, value = event.callback.payload.split(":", 1)
        try:
            await backend.upsert_profile(event.callback.user.user_id, industry=value)
        except BackendError:
            await event.answer(notification="Сервис недоступен, попробуйте ещё раз")
            return
        await event.message.delete()
        await _ask_priority(event.message.answer, context)

    @dp.message_created(F.message.body.text, ProfileForm.industry)
    async def on_industry_text(event: MessageCreated, context: MemoryContext):
        user_id = event.message.sender.user_id
        try:
            industry, confidence = await backend.classify_industry(
                user_id, event.message.body.text
            )
            if industry and confidence >= settings.CLASSIFY_CONFIDENCE_THRESHOLD:
                await backend.upsert_profile(user_id, industry=industry)
                await event.message.answer(f"Определил сферу как «{industry}».")
                await _ask_priority(event.message.answer, context)
                return
        except BackendError:
            await event.message.answer(BACKEND_ERROR_TEXT)
            return

        await event.message.answer(
            text="Не уверен, что правильно понял сферу — выберите, пожалуйста, из списка:",
            attachments=[industry_keyboard().as_markup()],
        )

    # --- Шаг 4: приоритет -> matching -> выдача результата ---
    @dp.message_callback(F.callback.payload.startswith("priority:"), ProfileForm.priority)
    async def on_priority(event: MessageCallback, context: MemoryContext):
        _, value = event.callback.payload.split(":", 1)
        user_id = event.callback.user.user_id
        try:
            await backend.upsert_profile(user_id, priority=value)
            await context.set_state(None)
            await event.message.delete()
            await _send_results(event.message.answer, event.bot, user_id)
        except BackendError:
            await event.message.answer(BACKEND_ERROR_TEXT)

    # --- «Сохранить» на карточке программы (работает вне состояний формы) ---
    @dp.message_callback(F.callback.payload.startswith("save:"))
    async def on_save(event: MessageCallback, context: MemoryContext):
        program_id = int(event.callback.payload.split(":", 1)[1])
        try:
            # The backend resolves the profile from the caller, so there is no
            # profile id to lose when the bot restarts and memory state is gone.
            await backend.save_application(event.callback.user.user_id, program_id)
        except BackendError:
            await event.answer(notification="Не удалось сохранить, попробуйте ещё раз")
            return
        await event.answer(notification="Сохранено в «Мои заявки» ✅")

    # --- Карточка программы по кнопке из ответа ИИ-консультанта ---
    @dp.message_callback(F.callback.payload.startswith("program:"))
    async def on_program(event: MessageCallback, context: MemoryContext):
        program_id = int(event.callback.payload.split(":", 1)[1])
        try:
            program = await backend.get_program(program_id)
        except BackendError:
            await event.answer(notification="Не удалось открыть программу, попробуйте ещё раз")
            return
        await event.message.answer(
            text=_program_card_text(program),
            attachments=[save_program_keyboard(program["id"]).as_markup()],
        )

    # --- Свободный текст -> ИИ-консультант ---
    # Registered last: maxapi runs the first matching handler, so the form's
    # own text steps (custom region, industry description) take precedence.
    @dp.message_created(F.message.body.text)
    async def on_free_text(event: MessageCreated, context: MemoryContext):
        text = event.message.body.text.strip()
        if not text:
            return
        if text.startswith("/"):
            await event.message.answer("Не знаю такой команды.\n\n" + HELP_TEXT)
            return

        await _answer_question(event, context, text)

        # A question asked mid-form pushes the step's buttons out of view.
        if await context.get_state() in (ProfileForm.status, ProfileForm.region, ProfileForm.priority):
            await event.message.answer(FORM_REMINDER)
