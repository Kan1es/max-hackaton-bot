"""Which catalog rows are visible, and the one rule that governs demo data.

The hand-made demo catalog (`is_mock=True`) is a fallback: it is shown, next
to whatever real programs exist and labelled as demo data, until the
collector has gathered DEMO_CATALOG_MIN_REAL active real programs. A dozen
federal programs don't yet cover a self-employed person in Krasnodar; a
full catalog does. Hidden demo rows are never deleted — saved applications
may still point at them.
"""
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.support_program import SupportProgram


def active_programs():
    return select(SupportProgram).where(SupportProgram.is_active.is_(True))


async def refresh_demo_visibility(session: AsyncSession) -> bool:
    """Show demo rows until the real catalog is big enough. Returns their visibility."""
    real_active = await session.scalar(
        select(func.count()).select_from(SupportProgram).where(
            SupportProgram.is_mock.is_(False), SupportProgram.is_active.is_(True)
        )
    )
    show_demo = (real_active or 0) < settings.DEMO_CATALOG_MIN_REAL
    await session.execute(
        update(SupportProgram).where(SupportProgram.is_mock.is_(True)).values(is_active=show_demo)
    )
    return show_demo
