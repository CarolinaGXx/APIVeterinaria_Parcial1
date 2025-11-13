"""add diagnostico and tratamiento to citas

Revision ID: 0002
Revises: 0001
Create Date: 2025-11-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add diagnostico and tratamiento columns to citas table
    op.add_column('citas', sa.Column('diagnostico', sa.String(500), nullable=True))
    op.add_column('citas', sa.Column('tratamiento', sa.String(500), nullable=True))


def downgrade() -> None:
    # Remove diagnostico and tratamiento columns from citas table
    op.drop_column('citas', 'tratamiento')
    op.drop_column('citas', 'diagnostico')
