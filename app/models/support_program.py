from datetime import date
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from decimal import Decimal
from sqlalchemy import Boolean, Date, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application


class SupportProgram(Base, TimestampMixin):
    """Support program / grant / subsidy model."""
    __tablename__ = "support_programs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Structured criteria for matching engine (income limits, eligible age, target categories)
    eligibility_criteria: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)

    financial_benefit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    max_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="program",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SupportProgram id={self.id} title='{self.title}' category={self.category}>"
