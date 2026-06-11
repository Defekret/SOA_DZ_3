import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr


class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class BookingCreate(BaseModel):
    user_id: str
    flight_id: str
    passenger_name: str
    passenger_email: EmailStr
    seat_count: int


class BookingResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    flight_id: str
    passenger_name: str
    passenger_email: str
    seat_count: int
    total_price: Decimal
    status: BookingStatus
    created_at: datetime

    model_config = {"from_attributes": True}
