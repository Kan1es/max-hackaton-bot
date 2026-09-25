from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.support_program import SupportProgram


class Application(Base, TimestampMixin):
    """Application submitted by a user for a support program."""
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    program_id: Mapped[int] = mapped_column(
        ForeignKey("support_programs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # status: draft, submitted, in_review, approved, rejected, completed
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True, nullable=False)
    applicant_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="applications")
    program: Mapped["SupportProgram"] = relationship("SupportProgram", back_populates="applications")

    def __repr__(self) -> str:
        return f"<Application id={self.id} user_id={self.user_id} program_id={self.program_id} status={self.status}>"
