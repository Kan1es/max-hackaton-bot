"""Turn the text of an official page into catalog fields with the LLM.

Official pages describe a program in long legal prose; the matcher and the
cards need short, uniform fields. The prompt pins down the vocabulary the
matcher's keyword rules look for (app/core/options.py), so an extracted
program is matched exactly like a hand-written one.
"""
import json
import logging
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ValidationError, field_validator

from app.collector.base import RawItem
from app.core.config import settings
from app.core.options import PROFILE_INDUSTRY
from app.services.openrouter import chat_completion

logger = logging.getLogger(__name__)

# Part of every item's content hash: bump it when the prompt or the fields
# change, and the next run re-extracts everything instead of trusting rows
# produced by the old prompt.
EXTRACTION_VERSION = "3"

SYSTEM_PROMPT = """Ты извлекаешь сведения о мере государственной поддержки бизнеса из текста \
официального источника и возвращаешь строго один JSON-объект без пояснений и без markdown.

Поля:
- "relevant": true, если меру могут получить самозанятые, индивидуальные предприниматели, \
начинающие предприниматели или малый и средний бизнес (МСП). false — если получатели только \
бюджетные учреждения, муниципалитеты, крупные компании, только НКО, только физлица не для бизнеса, \
или это вообще не конкретная мера поддержки. Справочные и обзорные страницы тоже false: \
критерии отнесения к МСП, описание сайта или платформы, раздел-оглавление со ссылками \
на другие меры, новости.
- "name": официальное название меры (до 300 символов).
- "short_title": короткое понятное название до 60 символов.
- "description": 1–2 предложения простым языком: что даёт мера и кому.
- "type": одно из: "грант", "субсидия", "льготный кредит", "льготный заём", "налоговая льгота", \
"гарантия", "консультации и обучение", "имущественная поддержка", "поддержка".
- "region": "Россия (все регионы)" для федеральных мер, иначе название субъекта РФ, \
например "Москва", "Московская область", "Краснодарский край", "Санкт-Петербург".
- "industries": список отраслей строчными буквами (например "производство", "сельское хозяйство", \
"туризм", "it", "торговля", "услуги", "креативные индустрии"); пустой список, если ограничений нет.
- "eligible_status": кто может получить — явно используй слова «самозанятые», \
«индивидуальные предприниматели», «субъекты МСП», «начинающие предприниматели», \
«юрлица», «физлица», если они подходят.
- "conditions": главные условия в 1–3 предложениях.
- "amount": размер поддержки как в источнике (например "до 500 000 руб."), или null.
- "highlight": очень кратко для карточки, например "до 500 000 ₽" или "ставка 3%", или null.
- "deadline": срок приёма заявок текстом, или null.
- "ends_at": последний день приёма заявок в формате ГГГГ-ММ-ДД, или null, если не указан.
- "doc_checklist": список необходимых документов (короткие пункты, не больше 10), может быть пустым.

Пиши только по-русски, кратко и только то, что есть в тексте. Не выдумывай суммы, сроки \
и документы. Ответ — только JSON, без текста до и после."""

# Applicant words the matcher's STATUS_KEYWORDS react to. When the model's own
# eligibility summary names one of them, the measure is for small business
# whatever the model put in "relevant" — it contradicted itself in practice.
_SMALL_BUSINESS = ("самозанят", "индивидуальн", "предпринимат", "мсп", "малого и среднего")

# Industries the matcher knows, as a hint for the "industries" field.
_INDUSTRY_HINT = ", ".join(i.lower() for i in PROFILE_INDUSTRY)


class ExtractedProgram(BaseModel):
    relevant: bool
    name: str
    short_title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    region: Optional[str] = None
    industries: List[str] = []
    eligible_status: Optional[str] = None
    conditions: Optional[str] = None
    amount: Optional[str] = None
    highlight: Optional[str] = None
    deadline: Optional[str] = None
    ends_at: Optional[date] = None
    doc_checklist: List[str] = []

    @field_validator("industries", "doc_checklist", mode="before")
    @classmethod
    def _list_or_empty(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(v).strip() for v in value if str(v).strip()]

    @field_validator("ends_at", mode="before")
    @classmethod
    def _date_or_none(cls, value):
        if not value or value in ("null", "none"):
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @field_validator("name", mode="before")
    @classmethod
    def _clip_name(cls, value):
        return str(value or "").strip()[:500]

    @field_validator("short_title", mode="before")
    @classmethod
    def _clip_title(cls, value):
        return str(value).strip()[:255] if value else None


def parse_extraction(content: str) -> Optional[ExtractedProgram]:
    """The first-to-last brace span of the reply, validated; None if unusable."""
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        program = ExtractedProgram.model_validate(json.loads(content[start:end + 1]))
    except (ValueError, ValidationError):
        return None
    return program if program.name else None


async def extract_program(item: RawItem) -> Optional[ExtractedProgram]:
    content = await chat_completion(
        [
            {"role": "system", "content": SYSTEM_PROMPT + f"\n\nОтрасли, которые знает подбор: {_INDUSTRY_HINT}."},
            {"role": "user", "content": f"Источник: {item.url}\nЗаголовок: {item.title}\n\n{item.text}"},
        ],
        max_tokens=2500,
        timeout=settings.COLLECTOR_LLM_TIMEOUT,
    )
    if content is None:
        return None
    program = parse_extraction(content)
    if program is None:
        logger.warning("Unusable extraction for %s (%s chars): %.150s … %s",
                       item.url, len(content), content, content[-150:])
        return None
    status = (program.eligible_status or "").lower()
    if not program.relevant and any(word in status for word in _SMALL_BUSINESS):
        program = program.model_copy(update={"relevant": True})
    # Structured values from the source beat the model's reading of the prose.
    return program.model_copy(update={k: v for k, v in item.known.items() if v})
