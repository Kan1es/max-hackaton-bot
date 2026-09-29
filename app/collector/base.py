import re
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Optional, Protocol

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}

# What an extraction prompt can hold comfortably; official pages are long.
MAX_ITEM_TEXT = 12000


@dataclass
class RawItem:
    external_id: str
    url: str
    title: str
    text: str
    # Values the source states in structured form; they win over the LLM's
    # reading of the text.
    known: Dict[str, object] = field(default_factory=dict)


class Source(Protocol):
    name: str

    def items(self, client: httpx.AsyncClient, limit: int) -> AsyncIterator[RawItem]:
        ...


def source_client(**kwargs) -> httpx.AsyncClient:
    """HTTP client for government sites, via the Russian proxy when configured."""
    return httpx.AsyncClient(
        proxy=settings.COLLECTOR_PROXY or None,
        headers=BROWSER_HEADERS,
        timeout=httpx.Timeout(30.0, connect=15.0),
        follow_redirects=True,
        **kwargs,
    )


_SPACES = re.compile(r"[ \t\u00a0]+")
_BLANK_LINES = re.compile(r"\n\s*\n+")


def page_text(html: str) -> str:
    """Readable text of a page: main content without scripts, menus and footers."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form"]):
        tag.decompose()
    root = soup.find("main") or soup.find(class_=re.compile(r"(content|detail|support)")) or soup.body or soup
    text = _SPACES.sub(" ", root.get_text("\n"))
    return _BLANK_LINES.sub("\n\n", text).strip()


def clip(text: Optional[str], limit: int = MAX_ITEM_TEXT) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"
