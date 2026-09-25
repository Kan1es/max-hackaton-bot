import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support_program import SupportProgram

SEED_FILE = Path(__file__).parent / "seed_data" / "support_programs.json"


async def seed_support_programs(session: AsyncSession) -> None:
    """Load the mock support-program catalog on first run.

    Same 19-program dataset used by the mini-app demo
    (miniapp/src/data/support_programs.json), converted to the
    `support_programs` schema. Every row is is_mock=True — real data
    integration (МСП.РФ / Госуслуги APIs) is out of scope for the hackathon
    MVP per the architecture doc's MoSCoW "Won't".
    """
    count = await session.scalar(select(func.count()).select_from(SupportProgram))
    if count:
        return

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    session.add_all(SupportProgram(**row) for row in data)
    await session.commit()
