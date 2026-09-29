"""AI consultant: answers free-form questions about support programs.

The relevant part of the catalog goes into the prompt — programs matched to
the profile first, then those the question mentions — so the model answers
strictly from our data instead of from its own memory —
it must not invent programs, amounts or deadlines. The programs it relies on
are returned as ids, which lets the bot attach buttons to the real cards.

When the LLM is unavailable (no key, rate limit, timeout) the consultant
degrades to a keyword search over the same catalog, so the user still gets
something useful instead of an error.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from app.core.config import settings
from app.models.support_program import SupportProgram
from app.services.matching import rank_programs
from app.services.openrouter import chat_completion

logger = logging.getLogger(__name__)

MAX_REFERENCED_PROGRAMS = 3
# A real catalog runs to hundreds of programs; the prompt carries this many.
MAX_PROMPT_PROGRAMS = 30

SYSTEM_PROMPT = """Ты — ИИ-консультант бота «Навигатор мер поддержки» в мессенджере MAX. \
Помогаешь самозанятым, начинающим и действующим ИП разобраться в грантах, льготных займах, \
субсидиях и налоговых льготах.

Правила:
- Отвечай только на основе каталога программ ниже. Не придумывай программы, суммы, сроки, \
документы и ссылки, которых нет в каталоге. Если в каталоге нет ответа — честно скажи об этом \
и посоветуй проверить у организатора программы или в центре «Мой бизнес».
- Учитывай профиль пользователя. Программы с пометкой «подходит по профилю» подобраны \
под него — предлагай их в первую очередь. Если регион пользователя известен, не предлагай \
региональные программы других регионов, пока он сам о них не спросит.
- Отвечай только на русском языке (никаких иероглифов и слов на других языках), дружелюбно и по делу: 2–6 коротких предложений или короткий список. \
Без markdown-разметки (без **, #, таблиц) — только обычный текст и символ «•» для списков.
- Не обещай, что поддержку точно одобрят: окончательное решение принимает организатор.
- На вопросы не про поддержку бизнеса мягко возвращай разговор к мерам поддержки.
- В самой последней строке ответа перечисли номера программ из каталога, на которые \
опирается ответ, в формате «ПРОГРАММЫ: 3, 7» (не больше трёх). Если ни одна не подходит, \
напиши «ПРОГРАММЫ: -».

Профиль пользователя:
{profile}

Каталог программ:
{catalog}"""

FALLBACK_INTRO = (
    "ИИ-консультант сейчас перегружен, поэтому отвечаю поиском по каталогу."
)
FALLBACK_FOUND = " Вот программы, которые похожи на ваш вопрос — откройте карточку, чтобы увидеть условия и документы."
FALLBACK_NOTHING = (
    " По вашему вопросу ничего не нашёл. Попробуйте переформулировать или повторите вопрос через минуту."
)

# Usually on its own last line, but some models append it to the paragraph.
_PROGRAMS_LINE = re.compile(r"\s*ПРОГРАММЫ\s*:[ \t]*([\d,; \t-]*)", re.IGNORECASE)
_MARKDOWN = re.compile(r"\*\*|__|^#+\s*", re.MULTILINE)
# Qwen occasionally slips into Chinese mid-sentence; drop those runs rather
# than show them to a Russian-speaking user.
_CJK = re.compile(r"[\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]+")
_WORD = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)

# Words that carry no search signal in a question about support measures.
_STOPWORDS = {
    "как", "что", "где", "какие", "какой", "какая", "для", "мне", "меня", "можно", "нужно",
    "есть", "или", "это", "при", "the", "получить", "подать", "хочу", "если", "там", "так",
    "мой", "моя", "мои", "про", "под", "без", "его", "она", "они", "чем", "уже", "еще", "ещё",
}


@dataclass
class HistoryTurn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class AssistantAnswer:
    text: str
    program_ids: List[int] = field(default_factory=list)
    is_stub: bool = False


def _profile_text(profile) -> str:
    rows = [
        ("Статус", profile.status),
        ("Регион", profile.region),
        ("Сфера", profile.industry),
        ("Приоритет", profile.priority),
    ]
    filled = [f"{label}: {value}" for label, value in rows if value]
    return "\n".join(filled) if filled else "Профиль ещё не заполнен."


def _program_text(program: SupportProgram, matched: bool) -> str:
    title = program.short_title or program.name
    lines = [f"[{program.id}] {title}" + (" — подходит по профилю" if matched else "")]
    if program.short_title:
        lines.append(f"Официальное название: {program.name}")
    for label, value in (
        ("Вид", program.type),
        ("Регион", program.region),
        ("Описание", program.description),
        ("Кто может получить", program.eligible_status),
        ("Условия", program.conditions),
        ("Сумма", program.amount),
        ("Срок", program.deadline),
    ):
        if value:
            lines.append(f"{label}: {value}")
    if program.industries:
        lines.append("Отрасли: " + ", ".join(program.industries))
    if program.doc_checklist:
        lines.append("Документы: " + "; ".join(program.doc_checklist))
    return "\n".join(lines)


def select_prompt_programs(
    profile, programs: Sequence[SupportProgram], question: str = ""
) -> List[SupportProgram]:
    """Matched programs, then ones the question is about, then the rest — capped."""
    by_id = {p.id: p for p in programs}
    ranked = [item.program.id for item in rank_programs(profile, list(programs), limit=len(programs) or 1)]
    mentioned = keyword_search(question, programs, limit=MAX_PROMPT_PROGRAMS) if question else []
    ordered: List[int] = []
    for pid in [*ranked, *mentioned, *sorted(by_id)]:
        if pid not in ordered:
            ordered.append(pid)
    return [by_id[pid] for pid in ordered[:MAX_PROMPT_PROGRAMS]]


def build_system_prompt(profile, programs: Sequence[SupportProgram], question: str = "") -> str:
    matched_ids = {item.program.id for item in rank_programs(profile, list(programs), limit=len(programs) or 1)}
    # Matched programs first: the model leans on what it reads early.
    selected = select_prompt_programs(profile, programs, question)
    catalog = "\n\n".join(_program_text(p, p.id in matched_ids) for p in selected)
    return SYSTEM_PROMPT.format(profile=_profile_text(profile), catalog=catalog)


def parse_answer(content: str, known_ids: Sequence[int]) -> AssistantAnswer:
    """Split the model's reply into user-facing text and referenced program ids."""
    known = set(known_ids)
    program_ids: List[int] = []

    match = None
    for match in _PROGRAMS_LINE.finditer(content):
        pass
    if match is not None:
        for raw in re.findall(r"\d+", match.group(1)):
            pid = int(raw)
            if pid in known and pid not in program_ids:
                program_ids.append(pid)
        content = content[:match.start()] + content[match.end():]

    text = _MARKDOWN.sub("", content)
    text = _CJK.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # The model sometimes cites catalog numbers inline as "[3]"; they mean
    # nothing to the user, who gets buttons for those programs instead.
    text = re.sub(r"\s*\[\d+\]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return AssistantAnswer(text=text, program_ids=program_ids[:MAX_REFERENCED_PROGRAMS])


def _stem(word: str) -> str:
    # Crude Russian stemming: drop a two-letter ending and cap the length, so
    # "гранты" finds "грант" and "субсидии" finds "субсидия".
    return word[:max(4, len(word) - 2)][:7]


def keyword_search(question: str, programs: Sequence[SupportProgram], limit: int = MAX_REFERENCED_PROGRAMS) -> List[int]:
    terms = {
        _stem(w.lower()) for w in _WORD.findall(question)
        if len(w) > 2 and w.lower() not in _STOPWORDS
    }
    if not terms:
        return []

    scored = []
    for program in programs:
        haystack = " ".join(filter(None, [
            program.name, program.short_title, program.description, program.type,
            program.conditions, program.eligible_status, " ".join(program.industries or []),
        ])).lower()
        hits = sum(1 for term in terms if term in haystack)
        if hits:
            scored.append((-hits, program.id))
    return [pid for _, pid in sorted(scored)[:limit]]


def fallback_answer(question: str, programs: Sequence[SupportProgram]) -> AssistantAnswer:
    ids = keyword_search(question, programs)
    text = FALLBACK_INTRO + (FALLBACK_FOUND if ids else FALLBACK_NOTHING)
    return AssistantAnswer(text=text, program_ids=ids, is_stub=True)


async def answer_question(
    question: str,
    profile,
    programs: Sequence[SupportProgram],
    history: Optional[Sequence[HistoryTurn]] = None,
) -> AssistantAnswer:
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": build_system_prompt(profile, programs, question)}
    ]
    for turn in history or []:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": question})

    content = await chat_completion(
        messages,
        max_tokens=700,
        timeout=settings.ASSISTANT_TIMEOUT,
        temperature=0.3,
    )
    if content is None:
        return fallback_answer(question, programs)

    answer = parse_answer(content, [p.id for p in programs])
    if not answer.text:
        logger.warning("Assistant answer was empty after parsing: %.200s", content)
        return fallback_answer(question, programs)
    return answer
