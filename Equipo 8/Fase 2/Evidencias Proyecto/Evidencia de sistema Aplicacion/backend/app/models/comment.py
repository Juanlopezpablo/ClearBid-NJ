from uuid import UUID as PyUUID

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, BaseEntity


class TicketComment(Base, BaseEntity):
    __tablename__ = "ticket_comments"

    ticket_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mention_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

