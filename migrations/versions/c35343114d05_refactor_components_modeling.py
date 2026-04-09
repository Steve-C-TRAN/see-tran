"""refactor components modeling

Revision ID: c35343114d05
Revises: 62d165f8257e
Create Date: 2025-09-07 09:25:02.692983

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c35343114d05'
down_revision = '62d165f8257e'
branch_labels = None
depends_on = None


def upgrade():
    """Drop legacy component columns (SQLite batch mode re-creates table)."""
    with op.batch_alter_table('components', schema=None) as batch_op:
        # Removed explicit drop_constraint(None, ...) calls because Alembic cannot drop unnamed constraints.
        # In batch mode, removing the FK columns will implicitly remove their constraints when table is recreated.
        for col in [
            'parent_component_id', 'lifecycle_stage', 'vendor_id', 'is_composite',
            'update_frequency', 'support_end_date', 'known_issues', 'deployment_date', 'version'
        ]:
            try:
                batch_op.drop_column(col)
            except Exception:
                # Safe guard: if column already gone (re-run), ignore
                pass


def downgrade():
    """Recreate legacy component columns and FK constraints (with explicit names)."""
    with op.batch_alter_table('components', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version', sa.VARCHAR(length=50), nullable=True))
        batch_op.add_column(sa.Column('deployment_date', sa.DATE(), nullable=True))
        batch_op.add_column(sa.Column('known_issues', sa.VARCHAR(length=500), nullable=True))
        batch_op.add_column(sa.Column('support_end_date', sa.DATE(), nullable=True))
        batch_op.add_column(sa.Column('update_frequency', sa.VARCHAR(length=50), nullable=True))
        batch_op.add_column(sa.Column('is_composite', sa.BOOLEAN(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('vendor_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('lifecycle_stage', sa.VARCHAR(length=10), nullable=True))
        batch_op.add_column(sa.Column('parent_component_id', sa.INTEGER(), nullable=True))
        # Explicitly named FKs to support future clean drops if needed
        batch_op.create_foreign_key('fk_components_vendor_id_vendors', 'vendors', ['vendor_id'], ['id'])
        batch_op.create_foreign_key('fk_components_parent_component_id_components', 'components', ['parent_component_id'], ['id'])
