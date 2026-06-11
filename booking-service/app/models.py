import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False)
    flight_id = Column(String, nullable=False)
    passenger_name = Column(String, nullable=False)
    passenger_email = Column(String, nullable=False)
    seat_count = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(BookingStatus, name="bookingstatus"), nullable=False,
                    default=BookingStatus.CONFIRMED)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("seat_count > 0", name="check_seat_count_positive"),
        CheckConstraint("total_price > 0", name="check_total_price_positive"),
    )
