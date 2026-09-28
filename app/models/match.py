from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.support_program import SupportProgram


class Match(Base):
    """Current recommendation set for a profile, kept for analytics.

    Upserted by GET /api/v1/programs/match/me rather than appended, so the
    table holds one row per (profile, program) instead of growing by three
    rows every time the mini-app is opened.
    """
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("profile_id", "program_id", name="uq_matches_profile_program"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    program_id: Mapped[int] = mapped_column(
        ForeignKey("support_programs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    profile: Mapped["Profile"] = relationship("Profile", back_populates="matches")
    program: Mapped["SupportProgram"] = relationship("SupportProgram", back_populates="matches")

    def __repr__(self) -> str:
        return f"<Match profile_id={self.profile_id} program_id={self.program_id} score={self.score}>"
