"""Add FK from fare_leg_rules → timeframes

Revision ID: 5799d8c821a9
Revises: 344407203160
Create Date: 2025-07-19 20:27:35.400219

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5799d8c821a9'
down_revision = '344407203160'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('gtfs_fare_leg_rules') as batch_op:
        batch_op.create_foreign_key(
            "fk_fare_leg_rules_from_timeframe",
            "gtfs_timeframes",
            ["from_timeframe_group_id"],
            ["timeframe_group_id"],
        )
        batch_op.create_foreign_key(
            "fk_fare_leg_rules_to_timeframe",
            "gtfs_timeframes",
            ["to_timeframe_group_id"],
            ["timeframe_group_id"],
        )

def downgrade():
    with op.batch_alter_table('gtfs_fare_leg_rules') as batch_op:
        batch_op.drop_constraint(
            "fk_fare_leg_rules_from_timeframe",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_fare_leg_rules_to_timeframe",
            type_="foreignkey",
        )
    # ### end Alembic commands ###
