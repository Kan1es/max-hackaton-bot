"""Rule-based matching engine.

Mirrors the client-side logic in miniapp/src/data/programs.js (matchesRegion,
industryMatch, matchReasons, rankPrograms) so the bot and the mini-app agree
on the same programs for the same profile, backed by the same Postgres rows
instead of two independent mock catalogs.
"""
from dataclasses import dataclass
from typing import List

from app.core.options import INDUSTRY_KEYWORDS, PRIORITY_KIND_MAP
from app.models.support_program import SupportProgram

MIN_REASONS_TO_MATCH = 2
TOP_N = 3


@dataclass
class ScoredProgram:
    program: SupportProgram
    score: float
    reasons: List[str]


def matches_region(program_region: str | None, region: str | None) -> bool:
    if not region:
        return True
    text = (program_region or "").lower()
    if "росси" in text or "все регион" in text:
        return True
    return region.lower() in text


def industry_match(program: SupportProgram, industry: str | None) -> bool:
    if not industry:
        return False
    corpus = " ".join(
        [program.name or "", program.description or "", *(program.industries or [])]
    ).lower()
    terms = INDUSTRY_KEYWORDS.get(industry, [])
    return any(term in corpus for term in terms)


def program_kind(program_type: str | None) -> str:
    text = (program_type or "").lower()
    if "кредит" in text or "займ" in text:
        return "Кредит"
    if "грант" in text:
        return "Грант"
    if "субсид" in text or "компенсац" in text:
        return "Субсидия"
    if "льгота" in text or "взнос" in text:
        return "Льгота"
    return "Поддержка"


def match_reasons(program: SupportProgram, profile) -> List[str]:
    reasons: List[str] = []
    if matches_region(program.region, profile.region):
        reasons.append("доступна в вашем регионе")
    if industry_match(program, profile.industry):
        reasons.append("подходит по сфере")
    kind = program_kind(program.type)
    if kind in PRIORITY_KIND_MAP.get(profile.priority or "", set()):
        reasons.append("соответствует вашему приоритету")
    return reasons


def rank_programs(profile, programs: List[SupportProgram]) -> List[ScoredProgram]:
    scored = []
    for program in programs:
        if not matches_region(program.region, profile.region):
            continue
        reasons = match_reasons(program, profile)
        if len(reasons) < MIN_REASONS_TO_MATCH:
            continue
        scored.append(ScoredProgram(program=program, score=len(reasons) * 10.0, reasons=reasons))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:TOP_N]
