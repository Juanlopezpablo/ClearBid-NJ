"""NEW-03: etiquetas persistentes en tickets."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "l8m9n0p1q2r3"
down_revision = "k7l8m9n0p1q2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tickets", sa.Column("labels", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.create_index("ix_tickets_labels", "tickets", ["labels"], postgresql_using="gin")


def downgrade():
    op.drop_index("ix_tickets_labels", table_name="tickets")
    op.drop_column("tickets", "labels")
