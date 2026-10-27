"""NEW-02: documentos asociados a incidencias.

Revision ID: k7l8m9n0p1q2
Revises: j6k7l8m9n0p1
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "k7l8m9n0p1q2"
down_revision = "j6k7l8m9n0p1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_documents_incident_id", "documents", "incidents",
                          ["incident_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_documents_incident_id", "documents", ["incident_id"])
    op.drop_constraint("ck_documents_has_target", "documents", type_="check")
    op.create_check_constraint("ck_documents_has_target", "documents",
                               "epic_id IS NOT NULL OR ticket_id IS NOT NULL OR incident_id IS NOT NULL")


def downgrade():
    # Evitar borrar evidencias al retroceder: exigir retirarlas o reasociarlas antes.
    connection = op.get_bind()
    if connection.execute(sa.text(
        "SELECT 1 FROM documents WHERE incident_id IS NOT NULL LIMIT 1"
    )).first():
        raise RuntimeError("Hay adjuntos de incidencias. Reasócialos antes de revertir NEW-02.")
    op.drop_constraint("ck_documents_has_target", "documents", type_="check")
    op.create_check_constraint("ck_documents_has_target", "documents",
                               "epic_id IS NOT NULL OR ticket_id IS NOT NULL")
    op.drop_index("ix_documents_incident_id", table_name="documents")
    op.drop_constraint("fk_documents_incident_id", "documents", type_="foreignkey")
    op.drop_column("documents", "incident_id")

