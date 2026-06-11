"""Initial schema for flight service

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE flightstatus AS ENUM ('SCHEDULED', 'DEPARTED', 'CANCELLED', 'COMPLETED')")
    op.execute("CREATE TYPE reservationstatus AS ENUM ('ACTIVE', 'RELEASED', 'EXPIRED')")

    op.create_table(
        'flights',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flight_number', sa.String(10), nullable=False),
        sa.Column('airline', sa.String(100), nullable=False),
        sa.Column('origin', sa.String(3), nullable=False),
        sa.Column('destination', sa.String(3), nullable=False),
        sa.Column('departure_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arrival_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_seats', sa.Integer(), nullable=False),
        sa.Column('available_seats', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', postgresql.ENUM('SCHEDULED', 'DEPARTED', 'CANCELLED', 'COMPLETED',
                                             name='flightstatus', create_type=False), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('total_seats > 0', name='check_total_seats_positive'),
        sa.CheckConstraint('available_seats >= 0', name='check_available_seats_non_negative'),
        sa.CheckConstraint('price > 0', name='check_price_positive'),
    )
    op.create_index('ix_flights_origin_destination', 'flights', ['origin', 'destination'])
    op.create_index('ix_flights_departure_time', 'flights', ['departure_time'])

    op.create_table(
        'seat_reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flight_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seat_count', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'RELEASED', 'EXPIRED',
                                             name='reservationstatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['flight_id'], ['flights.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id', name='uq_seat_reservations_booking_id'),
        sa.CheckConstraint('seat_count > 0', name='check_seat_count_positive'),
    )
    op.create_index('ix_seat_reservations_booking_id', 'seat_reservations', ['booking_id'])


def downgrade() -> None:
    op.drop_table('seat_reservations')
    op.drop_table('flights')
    op.execute("DROP TYPE reservationstatus")
    op.execute("DROP TYPE flightstatus")
