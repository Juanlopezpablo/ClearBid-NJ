"""Comprobantes persistentes para no duplicar comentarios al reintentar."""
from uuid import UUID as PyUUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, BaseEntity


class OfflineCommentOperation(Base, BaseEntity):
    __tablename__ = "offline_comment_operations"
    __table_args__ = (UniqueConstraint("author_id", "client_id", name="uq_offline_comment_author_client"),)
    author_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ticket_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    comment_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ticket_comments.id", ondelete="SET NULL"), nullable=True)
    body_hash: Mapped[str] = mapped_column(String(64), nullable=False)
