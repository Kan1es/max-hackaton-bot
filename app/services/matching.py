"""Rule-based matching engine.

This is the *only* implementation of the matching rules: both the bot and the
mini-app get their recommendations from `GET /api/v1/programs/match/{id}`,
so a given profile always produces the same ranking everywhere.

Scoring is a weighted sum of independent "reasons". A program needs at least
`MIN_REASONS_TO_MATCH` reasons to be shown at all, and a hard region/status
filter runs first — a programme the user simply cannot apply for should never
reach the top-3, however well it matches otherwise.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.options import (
    INDUSTRY_KEYWORDS,
    PRIORITY_KIND_MAP,
    STATUS_EXCLUSIONS,
    STATUS_KEYWORDS,
)
from app.models.support_program import SupportProgram

MIN_REASONS_TO_MATCH = 2
TOP_N = 3

REASON_REGION = "доступна в вашем регионе"
REASON_INDUSTRY = "подходит по сфере"
REASON_PRIORITY = "соответствует вашему приоритету"
REASON_STATUS = "подходит вашему статусу"

# Weight per reason. Industry is the strongest signal because it is the only
# one derived from the programme's own description rather than a coarse label.
REASON_WEIGHTS = {
    REASON_INDUSTRY: 30.0,
    REASON_REGION: 25.0,
    REASON_PRIORITY: 25.0,
    REASON_STATUS: 20.0,
}


@dataclass
class ScoredProgram:
    program: SupportProgram
    score: float
    reasons: List[str] = field(default_factory=list)


def matches_region(program_region: Optional[str], region: Optional[str]) -> bool:
    if not region:
        return True
    text = (program_region or "").lower()
    if "росси" in text or "все регион" in text:
        return True
    return region.lower() in text


def industry_match(program: SupportProgram, industry: Optional[str]) -> bool:
    if not industry:
        return False
    corpus = " ".join(
        [program.name or "", program.description or "", *(program.industries or [])]
    ).lower()
    return any(term in corpus for term in INDUSTRY_KEYWORDS.get(industry, []))


def status_match(program: SupportProgram, status: Optional[str]) -> bool:
    if not status:
        return False
    text = (program.eligible_status or "").lower()
    return any(term in text for term in STATUS_KEYWORDS.get(status, []))


def status_excluded(program: SupportProgram, status: Optional[str]) -> bool:
    """True when the programme is explicitly closed to this kind of applicant."""
    if not status:
        return False
    text = (program.eligible_status or "").lower()
    if not text:
        return False
    markers = STATUS_EXCLUSIONS.get(status, [])
    if not any(marker in text for marker in markers):
        return False
    # An explicit mention of the user's own status overrides the exclusion.
    return not status_match(program, status)


def program_kind(program_type: Optional[str]) -> str:
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
        reasons.append(REASON_REGION)
    if industry_match(program, profile.industry):
        reasons.append(REASON_INDUSTRY)
    if program_kind(program.type) in PRIORITY_KIND_MAP.get(profile.priority or "", set()):
        reasons.append(REASON_PRIORITY)
    if status_match(program, profile.status):
        reasons.append(REASON_STATUS)
    return reasons


def score_reasons(reasons: List[str]) -> float:
    return sum(REASON_WEIGHTS.get(reason, 0.0) for reason in reasons)


def rank_programs(profile, programs: List[SupportProgram], limit: int = TOP_N) -> List[ScoredProgram]:
    scored: List[ScoredProgram] = []
    for program in programs:
        if not matches_region(program.region, profile.region):
            continue
        if status_excluded(program, profile.status):
            continue
        reasons = match_reasons(program, profile)
        if len(reasons) < MIN_REASONS_TO_MATCH:
            continue
        scored.append(
            ScoredProgram(program=program, score=score_reasons(reasons), reasons=reasons)
        )
    # Ties broken by id so the ordering is stable across calls.
    scored.sort(key=lambda item: (-item.score, item.program.id))
    return scored[:limit]
