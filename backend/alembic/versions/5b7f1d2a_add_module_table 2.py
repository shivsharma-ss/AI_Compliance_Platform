"""Add module table

Revision ID: 5b7f1d2a_add_module_table
Revises: 4b20dd215db0
Create Date: 2025-12-19 10:40:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5b7f1d2a_add_module_table'
down_revision = '4b20dd215db0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'module',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_module_id'), 'module', ['id'], unique=False)
    op.create_index(op.f('ix_module_name'), 'module', ['name'], unique=True)

    # Seed default modules
    op.execute(
        """
        INSERT INTO module (name, display_name, enabled) VALUES
        ('sentinel-presidio', 'Presidio PII Scanner', true),
        ('sentinel-toxicity', 'Toxicity Classifier', true),
        ('sentinel-eu-ai', 'EU AI Act Analyzer', true)
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_module_name'), table_name='module')
    op.drop_index(op.f('ix_module_id'), table_name='module')
    op.drop_table('module')
