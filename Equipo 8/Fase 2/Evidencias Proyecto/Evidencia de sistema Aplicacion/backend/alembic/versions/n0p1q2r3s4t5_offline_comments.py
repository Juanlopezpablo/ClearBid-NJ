"""NEW-09: comprobantes de sincronización diferida de comentarios."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "n0p1q2r3s4t5"
down_revision = "m9n0p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("offline_comment_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ticket_comments.id", ondelete="SET NULL")),
        sa.Column("body_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("author_id", "client_id", name="uq_offline_comment_author_client"),
    )
    op.create_index("ix_offline_comment_operations_created_at", "offline_comment_operations", ["created_at"])


def downgrade():
    op.drop_table("offline_comment_operations")
