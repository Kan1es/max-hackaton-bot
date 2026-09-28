"""Dialog options, loaded from the backend at startup.

These lists used to be copy-pasted in three places (backend, bot, mini-app)
with a comment asking everyone to keep them in sync by hand. They now come
from `GET /api/v1/options/`, whose source of truth is app/core/options.py.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DialogOptions:
    status: List[str] = field(default_factory=list)
    region: List[str] = field(default_factory=list)
    industry: List[str] = field(default_factory=list)
    priority: List[str] = field(default_factory=list)
    other_region_label: str = "Другой регион"

    @classmethod
    def from_api(cls, payload: Dict) -> "DialogOptions":
        return cls(
            status=payload["status"],
            region=payload["region"],
            industry=payload["industry"],
            priority=payload["priority"],
            other_region_label=payload["other_region_label"],
        )


_options: Optional[DialogOptions] = None


def set_options(options: DialogOptions) -> None:
    global _options
    _options = options


def get_options() -> DialogOptions:
    if _options is None:
        raise RuntimeError(
            "Опции диалога не загружены — вызовите load_options() до старта поллинга."
        )
    return _options
