"""Test configuration.

These tests deliberately avoid a live database: the parts most likely to
break silently — the matching rules, initData verification and the option
validators — are pure functions over plain objects.
"""
import os
from dataclasses import dataclass
from typing import List, Optional

import pytest

os.environ.setdefault("MAX_BOT_TOKEN", "test-token")


@dataclass
class FakeProfile:
    status: Optional[str] = None
    region: Optional[str] = None
    industry: Optional[str] = None
    priority: Optional[str] = None


@dataclass
class FakeProgram:
    id: int = 1
    name: str = ""
    description: str = ""
    region: str = "Россия"
    industries: Optional[List[str]] = None
    eligible_status: str = ""
    type: str = "грант"

    def __post_init__(self):
        if self.industries is None:
            self.industries = []


@pytest.fixture
def profile():
    return FakeProfile(
        status="ИП", region="Москва", industry="IT", priority="Развитие"
    )


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """Keep tests offline even when a developer's .env has an OpenRouter key."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
