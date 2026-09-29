"""Upsert collected items into support_programs.

Rules:
- rows are keyed by (source, external_id);
- an item whose text hasn't changed since the last run is not sent through
  the LLM again — it is only marked as seen today;
- if the LLM can't read an item, a previously stored version is kept as is;
- items that are not for small business are stored inactive, so they are
  recognised (by hash) and skipped next time instead of re-extracted;
- a program whose application window has closed is hidden;
- after a *complete* pass over a source, its rows that were not seen are
  hidden — a failed or truncated run never hides anything;
- finally the demo catalog is shown or hidden (app.services.catalog).
"""
import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import date
from typing import Awaitable, Callable, Optional, Set

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.base import RawItem, Source, source_client
from app.collector.extract import EXTRACTION_VERSION, ExtractedProgram, extract_program
from app.core.config import settings
from app.services.openrouter import daily_quota_exhausted
from app.models.support_program import SupportProgram
from app.services.catalog import refresh_demo_visibility

logger = logging.getLogger(__name__)

Extractor = Callable[[RawItem], Awaitable[Optional[ExtractedProgram]]]

_FIELDS = (
    "name", "short_title", "description", "type", "region", "industries", "eligible_status",
    "conditions", "amount", "highlight", "deadline", "ends_at", "doc_checklist",
)


@dataclass
class SyncStats:
    source: str
    seen: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    irrelevant: int = 0
    failed: int = 0
    extracted: int = 0
    hidden: int = 0
    complete: bool = False

    def __str__(self) -> str:
        return (
            f"{self.source}: seen={self.seen} created={self.created} updated={self.updated} "
            f"unchanged={self.unchanged} irrelevant={self.irrelevant} failed={self.failed} "
            f"llm_calls={self.extracted} "
            f"hidden={self.hidden} complete={self.complete}"
        )


def _is_open(ends_at: Optional[date], today: date) -> bool:
    return ends_at is None or ends_at >= today


async def sync_source(
    session: AsyncSession,
    source: Source,
    *,
    limit: int,
    extractor: Extractor = extract_program,
    llm_delay: float = 0.0,
    llm_budget: Optional[int] = None,
    dry_run: bool = False,
    today: Optional[date] = None,
) -> SyncStats:
    today = today or date.today()
    stats = SyncStats(source=source.name)
    seen: Set[str] = set()

    result = await session.execute(select(SupportProgram).where(SupportProgram.source == source.name))
    stored = {row.external_id: row for row in result.scalars().all()}

    async def counted(item):
        stats.extracted += 1
        return await extractor(item)

    async with source_client() as client:
        try:
            async for item in source.items(client, limit):
                if llm_budget is not None and stats.extracted >= llm_budget:
                    # Out of LLM budget for this run: stop without declaring
                    # the pass complete, the rest follows on the next run.
                    logger.info("%s: LLM budget of %s spent, stopping", source.name, llm_budget)
                    break
                stats.seen += 1
                seen.add(item.external_id)
                await _sync_item(session, source.name, item, stored, counted, stats, today, dry_run)
                if daily_quota_exhausted():
                    # Nothing more can be extracted today. Stop without
                    # declaring the pass complete; unchanged items are
                    # recognised by hash tomorrow, so the next run resumes.
                    logger.warning("%s: LLM daily quota used up, stopping after %s items",
                                   source.name, stats.seen)
                    break
                if not dry_run:
                    await session.commit()
                if llm_delay and stats.seen < limit:
                    await asyncio.sleep(llm_delay)
            else:
                # A run cut short by the limit hasn't seen everything the source has.
                stats.complete = stats.seen < limit
        except Exception:
            logger.exception("Source %s failed after %s items", source.name, stats.seen)

    if stats.complete and not dry_run:
        gone = [row for ext_id, row in stored.items() if ext_id not in seen and row.is_active]
        for row in gone:
            row.is_active = False
        stats.hidden += len(gone)

    if not dry_run:
        # Everything stored for the source whose window has closed since.
        closed = await session.execute(
            update(SupportProgram)
            .where(
                SupportProgram.source == source.name,
                SupportProgram.is_active.is_(True),
                SupportProgram.ends_at < today,
            )
            .values(is_active=False)
        )
        stats.hidden += closed.rowcount or 0
        await refresh_demo_visibility(session)
        await session.commit()

    logger.info("%s", stats)
    return stats


async def _sync_item(session, source_name, item, stored, extractor, stats, today, dry_run) -> None:
    row = stored.get(item.external_id)
    content_hash = hashlib.sha256(f"{EXTRACTION_VERSION}\n{item.text}".encode("utf-8")).hexdigest()

    if row is not None and row.content_hash == content_hash:
        stats.unchanged += 1
        row.checked_at = today.isoformat()
        row.is_active = row.is_relevant and _is_open(row.ends_at, today)
        return

    extracted = await extractor(item)
    if extracted is None:
        stats.failed += 1
        return

    if dry_run:
        logger.info("[dry-run] %s → %s", item.url, extracted.model_dump_json(exclude_none=True)[:800])

    if row is None:
        row = SupportProgram(source=source_name, external_id=item.external_id, is_mock=False)
        if not dry_run:
            session.add(row)
        stored[item.external_id] = row
        stats.created += 1
    else:
        stats.updated += 1

    for name in _FIELDS:
        setattr(row, name, getattr(extracted, name))
    row.source_url = item.url
    row.checked_at = today.isoformat()
    row.content_hash = content_hash
    row.is_mock = False
    row.is_relevant = extracted.relevant
    if not extracted.relevant:
        stats.irrelevant += 1
    row.is_active = extracted.relevant and _is_open(extracted.ends_at, today)


async def run_sources(session_factory, sources, *, limit: int, dry_run: bool = False):
    all_stats = []
    budget = settings.COLLECTOR_LLM_BUDGET
    for source in sources:
        async with session_factory() as session:
            stats = await sync_source(
                session, source, limit=limit, dry_run=dry_run,
                llm_delay=settings.COLLECTOR_LLM_DELAY, llm_budget=max(budget, 0),
            )
        budget -= stats.extracted
        all_stats.append(stats)
    return all_stats
