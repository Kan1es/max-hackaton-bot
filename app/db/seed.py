import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support_program import SupportProgram
from app.services.catalog import refresh_demo_visibility

logger = logging.getLogger("app.db.seed")

SEED_FILE = Path(__file__).parent / "seed_data" / "support_programs.json"


async def seed_support_programs(session: AsyncSession) -> None:
    """Sync the mock support-program catalog into Postgres on startup.

    Rows are matched by `name` and updated in place rather than inserted only
    once, so editing the seed file (or adding a column to the model) takes
    effect on the next restart instead of silently doing nothing because the
    table already had rows. Only `is_mock` rows are touched — real catalog
    entries collected from official portals are left alone, and the demo
    rows stay hidden while any of those is active.
    """
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))

    result = await session.execute(select(SupportProgram).where(SupportProgram.is_mock.is_(True)))
    existing = {program.name: program for program in result.scalars().all()}

    created = 0
    for row in data:
        program = existing.get(row["name"])
        if program is None:
            session.add(SupportProgram(**row))
            created += 1
            continue
        for key, value in row.items():
            setattr(program, key, value)

    await session.flush()
    shown = await refresh_demo_visibility(session)
    await session.commit()
    logger.info(
        "Seeded support programs: %s new, %s refreshed, demo catalog %s",
        created, len(data) - created, "shown" if shown else "hidden (real programs present)",
    )
