"""NEW-13: contenido de documentos para búsqueda unificada."""
from alembic import op
import sqlalchemy as sa
revision = "o1p2q3r4s5t6"
down_revision = "n0p1q2r3s4t5"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("documents", sa.Column("search_text", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("search_status", sa.String(20), nullable=False, server_default="pending"))

def downgrade():
    op.drop_column("documents", "search_status")
    op.drop_column("documents", "search_text")
