from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.support_program import SupportProgram


class Match(Base):
    """Result of the rule-based matching engine, kept for history/analytics."""
    __tablename__ = "matches"

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
