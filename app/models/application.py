from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.support_program import SupportProgram


class Application(Base):
    """Program saved by the user into "Мои заявки" from the chat or mini-app."""
    __tablename__ = "applications"
    # A program is either in "Мои заявки" or it isn't — the uniqueness is
    # enforced here rather than only by a read-then-insert in the endpoint,
    # which would race between two taps on the bookmark button.
    __table_args__ = (
        UniqueConstraint("profile_id", "program_id", name="uq_applications_profile_program"),
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
    # status: saved, in_progress, submitted
    status: Mapped[str] = mapped_column(String(50), default="saved", index=True, nullable=False)
    # Ticked-off items of the program's doc_checklist, stored by their text
    # rather than by index so the marks survive an edit to the catalog.
    checked_docs: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite"), nullable=True, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    profile: Mapped["Profile"] = relationship("Profile", back_populates="applications")
    program: Mapped["SupportProgram"] = relationship("SupportProgram", back_populates="applications")

    def __repr__(self) -> str:
        return f"<Application id={self.id} profile_id={self.profile_id} program_id={self.program_id} status={self.status}>"
