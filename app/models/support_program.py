from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.application import Application


class SupportProgram(Base, TimestampMixin):
    """Catalog of support programs (grants, loans, tax breaks, subsidies).

    `amount` and `deadline` are kept as free text (not Decimal/Date) because
    the source data describes them in prose (e.g. "до 500 000 000 руб.",
    "действует на постоянной основе") rather than clean structured values.
    `type` is a lightweight addition beyond the original architecture sketch:
    it stores the raw "вид поддержки" (кредит/грант/субсидия/льгота) and is
    used by the rule-based matcher to score against the user's `priority`,
    mirroring miniapp/src/data/programs.js `programKind()`.
    """
    __tablename__ = "support_programs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industries: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True, default=list)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    deadline: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    doc_checklist: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    matches: Mapped[List["Match"]] = relationship(
        "Match",
        back_populates="program",
        cascade="all, delete-orphan",
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="program",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SupportProgram id={self.id} name='{self.name}' is_mock={self.is_mock}>"
