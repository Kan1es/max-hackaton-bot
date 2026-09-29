import argparse
import asyncio
import logging
import time

from app.collector.sources import get_sources
from app.collector.sync import run_sources
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services import openrouter
from app.services.openrouter import is_enabled as llm_enabled

logger = logging.getLogger("app.collector")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Collect support programs from official portals")
    parser.add_argument("--source", default=settings.COLLECTOR_SOURCES,
                        help="comma-separated adapters (default: COLLECTOR_SOURCES)")
    parser.add_argument("--limit", type=int, default=settings.COLLECTOR_MAX_ITEMS,
                        help="max items per source and run")
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and extract, log the result, write nothing")
    parser.add_argument("--loop", action="store_true",
                        help="repeat every COLLECTOR_INTERVAL_HOURS")
    args = parser.parse_args()

    sources = get_sources(args.source)
    if not llm_enabled():
        # Without the LLM nothing can be turned into catalog fields.
        raise SystemExit("OPENROUTER_API_KEY is not set — the collector needs the LLM")
    logger.info(
        "Collector: sources=%s limit=%s proxy=%s",
        args.source, args.limit, "yes" if settings.COLLECTOR_PROXY else "no",
    )

    while True:
        stats = await run_sources(AsyncSessionLocal, sources, limit=args.limit, dry_run=args.dry_run)
        for item in stats:
            logger.info("Done: %s", item)
        if not args.loop:
            return
        pause = settings.COLLECTOR_INTERVAL_HOURS * 3600
        if openrouter.daily_quota_exhausted():
            # The pass stopped on the LLM's daily quota: resume right after
            # the reset instead of losing a whole interval.
            pause = min(pause, openrouter._daily_quota_reset - time.time() + 120)
        logger.info("Next run in %.1f h", pause / 3600)
        await asyncio.sleep(pause)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s")
    asyncio.run(main())
