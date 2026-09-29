"""corpmsp.ru — the SME Corporation's own federal programs (preferential
loans, leasing, guarantees, property support, programs for young
entrepreneurs…). A handful of pages rather than a catalog, but reachable
without a Russian IP, so it provides real data even without the tunnel.

The adapter follows every link of the "для бизнеса" section; pages that
aren't support measures (criteria, news hubs) are marked irrelevant by the
LLM and stay hidden.
"""
import re
from typing import AsyncIterator
from urllib.parse import urljoin

import httpx

from app.collector.base import RawItem, clip, page_text

BASE = "https://corpmsp.ru"
SECTION = f"{BASE}/to-business/"
_LINK = re.compile(r'href="(/to-business/[a-z0-9_-]+(?:/[a-z0-9_-]+)*/)"')


def section_links(html: str):
    return sorted({m for m in _LINK.findall(html) if m != "/to-business/"})


class CorpMspSource:
    name = "corpmsp"

    async def items(self, client: httpx.AsyncClient, limit: int) -> AsyncIterator[RawItem]:
        response = await client.get(SECTION)
        response.raise_for_status()
        for path in section_links(response.text)[:limit]:
            url = urljoin(BASE, path)
            page = await client.get(url)
            if page.status_code != 200:
                continue
            text = page_text(page.text)
            title = text.split("\n", 1)[0][:200]
            yield RawItem(external_id=path, url=url, title=title, text=clip(text))
