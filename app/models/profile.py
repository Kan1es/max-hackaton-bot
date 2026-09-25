from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.match import Match
    from app.models.application import Application


class Profile(Base, TimestampMixin):
    """Profile collected step-by-step by the bot dialog.

    Fields are nullable because they are filled incrementally as the user
    answers each question; the bot upserts this row after every step so the
    mini-app can pick up mid-dialog state (see PROFILE_STATUS/PROFILE_REGION/
    PROFILE_INDUSTRY/PROFILE_PRIORITY options in app/core/options.py, which
    must stay in sync with miniapp/src/data/programs.js `options`).
    """
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="profile")
    matches: Mapped[List["Match"]] = relationship(
        "Match",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Profile id={self.id} user_id={self.user_id} status={self.status}>"
