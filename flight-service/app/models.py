import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, CheckConstraint, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class FlightStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    DEPARTED = "DEPARTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class Flight(Base):
    __tablename__ = "flights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_number = Column(String(10), nullable=False)
    airline = Column(String(100), nullable=False)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    departure_time = Column(DateTime(timezone=True), nullable=False)
    arrival_time = Column(DateTime(timezone=True), nullable=False)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(FlightStatus, name="flightstatus"), nullable=False, default=FlightStatus.SCHEDULED)

    __table_args__ = (
        CheckConstraint("total_seats > 0", name="check_total_seats_positive"),
        CheckConstraint("available_seats >= 0", name="check_available_seats_non_negative"),
        CheckConstraint("price > 0", name="check_price_positive"),
    )


class SeatReservation(Base):
    __tablename__ = "seat_reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    booking_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    seat_count = Column(Integer, nullable=False)
    status = Column(Enum(ReservationStatus, name="reservationstatus"), nullable=False,
                    default=ReservationStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("seat_count > 0", name="check_seat_count_positive"),
    )
