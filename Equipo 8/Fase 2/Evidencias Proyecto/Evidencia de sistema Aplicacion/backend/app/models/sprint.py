"""Iteraciones de desarrollo por aplicación, independientes de las épicas."""
from datetime import date, datetime
from uuid import UUID as PyUUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, BaseEntity


class Sprint(Base, BaseEntity):
    __tablename__ = "sprints"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_sprints_dates"),
        CheckConstraint("status IN ('PLANNED', 'ACTIVE', 'FINISHED')", name="ck_sprints_status"),
        Index("uq_sprints_active_application", "application_id", unique=True,
              postgresql_where=text("status = 'ACTIVE'"), sqlite_where=text("status = 'ACTIVE'")),
    )

    application_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    goal: Mapped[str] = mapped_column(String(2000), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PLANNED", server_default="PLANNED")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_completed: Mapped[int | None] = mapped_column(Integer, nullable=True)
