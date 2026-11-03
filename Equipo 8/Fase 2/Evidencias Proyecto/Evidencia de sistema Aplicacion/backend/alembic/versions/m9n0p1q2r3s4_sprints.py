"""NEW-05: planificación de sprints por aplicación."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "m9n0p1q2r3s4"
down_revision = "l8m9n0p1q2r3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("goal", sa.String(2000), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PLANNED"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("closed_total", sa.Integer()),
        sa.Column("closed_completed", sa.Integer()),
        sa.CheckConstraint("end_date >= start_date", name="ck_sprints_dates"),
        sa.CheckConstraint("status IN ('PLANNED', 'ACTIVE', 'FINISHED')", name="ck_sprints_status"),
    )
    op.create_index("ix_sprints_application_id", "sprints", ["application_id"])
    op.create_index("ix_sprints_created_at", "sprints", ["created_at"])
    op.create_index("ix_sprints_updated_at", "sprints", ["updated_at"])
    op.create_index("uq_sprints_active_application", "sprints", ["application_id"], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.add_column("tickets", sa.Column("sprint_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_tickets_sprint_id", "tickets", "sprints", ["sprint_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_tickets_sprint_id", "tickets", ["sprint_id"])


def downgrade():
    op.drop_index("ix_tickets_sprint_id", table_name="tickets")
    op.drop_constraint("fk_tickets_sprint_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "sprint_id")
    op.drop_table("sprints")
