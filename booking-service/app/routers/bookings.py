import uuid
import logging
from typing import Optional

import grpc
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.grpc_client import flight_client
from app.models import Booking, BookingStatus
from app.schemas import BookingCreate, BookingResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(body: BookingCreate, db: Session = Depends(get_db)):
    try:
        flight = flight_client.get_flight(body.flight_id)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Flight not found")
        raise HTTPException(status_code=503, detail="Flight service unavailable")

    booking_id = str(uuid.uuid4())

    try:
        flight_client.reserve_seats(
            flight_id=body.flight_id,
            seat_count=body.seat_count,
            booking_id=booking_id,
        )
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
            raise HTTPException(status_code=409, detail=e.details())
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Flight not found")
        raise HTTPException(status_code=503, detail="Could not reserve seats")

    total_price = body.seat_count * float(flight.price)
    booking = Booking(
        id=uuid.UUID(booking_id),
        user_id=body.user_id,
        flight_id=body.flight_id,
        passenger_name=body.passenger_name,
        passenger_email=body.passenger_email,
        seat_count=body.seat_count,
        total_price=total_price,
        status=BookingStatus.CONFIRMED,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    logger.info("Booking created: id=%s flight=%s seats=%d", booking_id, body.flight_id, body.seat_count)
    return booking


@router.get("/bookings", response_model=list[BookingResponse])
def list_bookings(user_id: str = Query(...), db: Session = Depends(get_db)):
    return db.query(Booking).filter(Booking.user_id == user_id).all()


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Booking is not CONFIRMED")

    try:
        flight_client.release_reservation(str(booking.id))
    except grpc.RpcError as e:
        if e.code() != grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=503, detail="Could not release reservation")

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    logger.info("Booking cancelled: id=%s", booking_id)
    return booking
