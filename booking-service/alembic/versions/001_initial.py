from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE bookingstatus AS ENUM ('CONFIRMED', 'CANCELLED')")

    op.create_table(
        'bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('flight_id', sa.String(), nullable=False),
        sa.Column('passenger_name', sa.String(), nullable=False),
        sa.Column('passenger_email', sa.String(), nullable=False),
        sa.Column('seat_count', sa.Integer(), nullable=False),
        sa.Column('total_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', postgresql.ENUM('CONFIRMED', 'CANCELLED',
                                             name='bookingstatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('seat_count > 0', name='check_seat_count_positive'),
        sa.CheckConstraint('total_price > 0', name='check_total_price_positive'),
    )
    op.create_index('ix_bookings_user_id', 'bookings', ['user_id'])


def downgrade() -> None:
    op.drop_table('bookings')
    op.execute("DROP TYPE bookingstatus")
