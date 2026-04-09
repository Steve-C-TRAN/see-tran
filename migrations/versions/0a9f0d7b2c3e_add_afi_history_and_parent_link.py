from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0a9f0d7b2c3e'
down_revision = '1b412d7114be'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ---- AFI: parent_afi_id + indexes (guarded) ----
    afi_cols = {c['name'] for c in insp.get_columns('agency_function_implementations')}

    # Add column + FK only if column missing
    if 'parent_afi_id' not in afi_cols:
        with op.batch_alter_table('agency_function_implementations', schema=None) as batch_op:
            batch_op.add_column(sa.Column('parent_afi_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_afi_parent_afi_id',
                'agency_function_implementations',
                ['parent_afi_id'], ['id'],
                ondelete='SET NULL'
            )

    # Ensure indexes exist (create if missing)
    afi_indexes = {ix['name'] for ix in insp.get_indexes('agency_function_implementations')}
    if 'ix_afi_parent_afi_id' not in afi_indexes:
        op.create_index('ix_afi_parent_afi_id', 'agency_function_implementations', ['parent_afi_id'], unique=False)
    if 'idx_afi_agency_function' not in afi_indexes:
        op.create_index('idx_afi_agency_function', 'agency_function_implementations', ['agency_id', 'function_id'], unique=False)

    # ---- AFI history table (guarded) ----
    has_hist = insp.has_table('agency_function_implementation_history')
    if not has_hist:
        op.create_table(
            'agency_function_implementation_history',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('afi_id', sa.Integer(), sa.ForeignKey('agency_function_implementations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('changed_by', sa.String(length=100), nullable=True),
            sa.Column('old_values', sa.JSON(), nullable=True),
            sa.Column('new_values', sa.JSON(), nullable=True),
        )

    # Ensure history indexes exist
    hist_indexes = set()
    if insp.has_table('agency_function_implementation_history'):
        hist_indexes = {ix['name'] for ix in insp.get_indexes('agency_function_implementation_history')}
    if 'ix_afi_history_afi_id' not in hist_indexes:
        op.create_index('ix_afi_history_afi_id', 'agency_function_implementation_history', ['afi_id'], unique=False)
    if 'ix_afi_history_timestamp' not in hist_indexes:
        op.create_index('ix_afi_history_timestamp', 'agency_function_implementation_history', ['timestamp'], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ---- AFI history indexes + table ----
    if insp.has_table('agency_function_implementation_history'):
        hist_indexes = {ix['name'] for ix in insp.get_indexes('agency_function_implementation_history')}
        if 'ix_afi_history_timestamp' in hist_indexes:
            op.drop_index('ix_afi_history_timestamp', table_name='agency_function_implementation_history')
        if 'ix_afi_history_afi_id' in hist_indexes:
            op.drop_index('ix_afi_history_afi_id', table_name='agency_function_implementation_history')
        op.drop_table('agency_function_implementation_history')

    # ---- AFI indexes + column/FK ----
    afi_indexes = {ix['name'] for ix in insp.get_indexes('agency_function_implementations')}
    if 'idx_afi_agency_function' in afi_indexes:
        op.drop_index('idx_afi_agency_function', table_name='agency_function_implementations')
    if 'ix_afi_parent_afi_id' in afi_indexes:
        op.drop_index('ix_afi_parent_afi_id', table_name='agency_function_implementations')

    afi_cols = {c['name'] for c in insp.get_columns('agency_function_implementations')}
    if 'parent_afi_id' in afi_cols:
        # Drop FK only if it exists; SQLite inspection is limited, so guard by name and ignore if missing.
        try:
            with op.batch_alter_table('agency_function_implementations', schema=None) as batch_op:
                batch_op.drop_constraint('fk_afi_parent_afi_id', type_='foreignkey')
        except Exception:
            pass
        with op.batch_alter_table('agency_function_implementations', schema=None) as batch_op:
            batch_op.drop_column('parent_afi_id')
