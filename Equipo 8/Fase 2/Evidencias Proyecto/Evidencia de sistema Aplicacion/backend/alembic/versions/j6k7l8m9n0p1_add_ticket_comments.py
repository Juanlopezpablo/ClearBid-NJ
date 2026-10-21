"""NEW-01: comentarios de tickets.

Revision ID: j6k7l8m9n0p1
Revises: i5j6k7l8m9n0
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "j6k7l8m9n0p1"
down_revision = "i5j6k7l8m9n0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ticket_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mention_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("ticket_id", "author_id", "created_at"):
        op.create_index(f"ix_ticket_comments_{column}", "ticket_comments", [column])


def downgrade():
    op.drop_table("ticket_comments")

