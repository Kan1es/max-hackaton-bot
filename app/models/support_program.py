from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, Boolean, Date, JSON, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.application import Application


class SupportProgram(Base, TimestampMixin):
    """Catalog of support programs (grants, loans, tax breaks, subsidies).

    `amount`, `deadline` and `eligible_status` are kept as free text (not
    Decimal/Date/enum) because the source data describes them in prose
    (e.g. "до 500 000 000 руб.", "действует на постоянной основе") rather
    than clean structured values — the matcher runs keyword rules over them.

    `type` stores the raw "вид поддержки" (кредит/грант/субсидия/льгота) and
    is normalised into a coarse kind by `app.services.matching.program_kind`.
    `short_title` and `highlight` are presentation-only fields the mini-app
    renders instead of the (often very long) official `name`/`amount`.
    """
    __tablename__ = "support_programs"
    __table_args__ = (
        # One row per item of an official source, however often it is re-collected.
        UniqueConstraint("source", "external_id", name="uq_support_programs_source_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    short_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # text[] on Postgres. The SQLite variant exists only so the API test suite
    # can run without a database server; deployments always use Postgres.
    industries: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite"), nullable=True, default=list
    )
    eligible_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    highlight: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deadline: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    doc_checklist: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite"), nullable=True, default=list
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    # Date the catalog entry was last verified against the official source.
    checked_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- provenance, filled by app.collector for programs from official
    # portals. The hand-made demo catalog leaves them empty.
    # Collector adapter name, e.g. "corpmsp" or "msp_rf".
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # The item's id within its source, stable across collections.
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Hidden rows stay in the table (saved applications may point at them) but
    # are left out of the catalog, matching and the AI consultant: a closed
    # selection, an item that disappeared from its source, or a demo program
    # once real data exists.
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False, index=True
    )
    # False when the LLM judged the item not to be for small business (only
    # for budget institutions, large companies…). Kept, inactive, so the next
    # run recognises it by hash instead of paying for another extraction.
    is_relevant: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    # Last day applications are accepted, when the source states one.
    ends_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # sha256 of the source text the fields were extracted from: an unchanged
    # item is not sent through the LLM again.
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

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
