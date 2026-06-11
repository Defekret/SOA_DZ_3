import uuid
import logging
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

import flight_pb2
import flight_pb2_grpc

from app.database import SessionLocal
from app.models import Flight, SeatReservation, FlightStatus, ReservationStatus
from app import redis_client as cache

logger = logging.getLogger(__name__)

STATUS_TO_PROTO = {
    FlightStatus.SCHEDULED: flight_pb2.SCHEDULED,
    FlightStatus.DEPARTED: flight_pb2.DEPARTED,
    FlightStatus.CANCELLED: flight_pb2.CANCELLED,
    FlightStatus.COMPLETED: flight_pb2.COMPLETED,
}


def _dt_to_ts(dt: datetime) -> Timestamp:
    ts = Timestamp()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ts.FromDatetime(dt)
    return ts


def _flight_to_proto(f: Flight) -> flight_pb2.FlightInfo:
    return flight_pb2.FlightInfo(
        id=str(f.id),
        flight_number=f.flight_number,
        airline=f.airline,
        origin=f.origin,
        destination=f.destination,
        departure_time=_dt_to_ts(f.departure_time),
        arrival_time=_dt_to_ts(f.arrival_time),
        total_seats=f.total_seats,
        available_seats=f.available_seats,
        price=float(f.price),
        status=STATUS_TO_PROTO.get(f.status, flight_pb2.FLIGHT_STATUS_UNSPECIFIED),
    )


def _proto_to_dict(p: flight_pb2.FlightInfo) -> dict:
    return {
        "id": p.id,
        "flight_number": p.flight_number,
        "airline": p.airline,
        "origin": p.origin,
        "destination": p.destination,
        "departure_time": p.departure_time.ToJsonString(),
        "arrival_time": p.arrival_time.ToJsonString(),
        "total_seats": p.total_seats,
        "available_seats": p.available_seats,
        "price": p.price,
        "status": p.status,
    }


def _dict_to_proto(d: dict) -> flight_pb2.FlightInfo:
    dep_ts = Timestamp()
    dep_ts.FromJsonString(d["departure_time"])
    arr_ts = Timestamp()
    arr_ts.FromJsonString(d["arrival_time"])
    return flight_pb2.FlightInfo(
        id=d["id"],
        flight_number=d["flight_number"],
        airline=d["airline"],
        origin=d["origin"],
        destination=d["destination"],
        departure_time=dep_ts,
        arrival_time=arr_ts,
        total_seats=d["total_seats"],
        available_seats=d["available_seats"],
        price=d["price"],
        status=d["status"],
    )


class FlightServicer(flight_pb2_grpc.FlightServiceServicer):

    def SearchFlights(self, request, context):
        date_str = request.date or ""
        cached = cache.get_search(request.origin, request.destination, date_str)
        if cached is not None:
            return flight_pb2.SearchFlightsResponse(flights=[_dict_to_proto(d) for d in cached])

        db = SessionLocal()
        try:
            query = db.query(Flight).filter(
                Flight.origin == request.origin,
                Flight.destination == request.destination,
                Flight.status == FlightStatus.SCHEDULED,
            )
            if date_str:
                try:
                    filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    query = query.filter(
                        Flight.departure_time >= datetime(filter_date.year, filter_date.month, filter_date.day, 0, 0, 0),
                        Flight.departure_time < datetime(filter_date.year, filter_date.month, filter_date.day, 23, 59, 59),
                    )
                except ValueError:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT, "date must be YYYY-MM-DD")
                    return

            flights = query.all()
            protos = [_flight_to_proto(f) for f in flights]
            cache.set_search(request.origin, request.destination, date_str, [_proto_to_dict(p) for p in protos])
            logger.info("SearchFlights %s->%s date=%s: %d results", request.origin, request.destination, date_str, len(flights))
            return flight_pb2.SearchFlightsResponse(flights=protos)
        finally:
            db.close()

    def GetFlight(self, request, context):
        cached = cache.get_flight(request.flight_id)
        if cached is not None:
            return _dict_to_proto(cached)

        db = SessionLocal()
        try:
            flight = db.query(Flight).filter(Flight.id == request.flight_id).first()
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Flight {request.flight_id} not found")
                return

            proto = _flight_to_proto(flight)
            cache.set_flight(request.flight_id, _proto_to_dict(proto))
            logger.info("GetFlight %s", request.flight_id)
            return proto
        finally:
            db.close()

    def ReserveSeats(self, request, context):
        db = SessionLocal()
        try:
            existing = db.query(SeatReservation).filter(
                SeatReservation.booking_id == uuid.UUID(request.booking_id),
                SeatReservation.status == ReservationStatus.ACTIVE,
            ).first()
            if existing:
                logger.info("ReserveSeats idempotent: booking_id=%s", request.booking_id)
                return flight_pb2.ReserveSeatsResponse(
                    reservation_id=str(existing.id),
                    flight_id=str(existing.flight_id),
                    booking_id=str(existing.booking_id),
                    seat_count=existing.seat_count,
                    status=flight_pb2.ACTIVE,
                )

            # Lock flight row to prevent race conditions
            flight = db.query(Flight).filter(
                Flight.id == request.flight_id
            ).with_for_update().first()

            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Flight {request.flight_id} not found")
                return

            if flight.available_seats < request.seat_count:
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    f"Not enough seats: requested {request.seat_count}, available {flight.available_seats}",
                )
                return

            flight.available_seats -= request.seat_count
            reservation = SeatReservation(
                flight_id=flight.id,
                booking_id=uuid.UUID(request.booking_id),
                seat_count=request.seat_count,
                status=ReservationStatus.ACTIVE,
            )
            db.add(reservation)
            db.commit()
            db.refresh(reservation)

            cache.invalidate_flight(str(flight.id))
            cache.invalidate_search_for_flight(flight.origin, flight.destination)

            logger.info("ReserveSeats: %d seats for booking_id=%s flight_id=%s",
                        request.seat_count, request.booking_id, request.flight_id)
            return flight_pb2.ReserveSeatsResponse(
                reservation_id=str(reservation.id),
                flight_id=str(reservation.flight_id),
                booking_id=str(reservation.booking_id),
                seat_count=reservation.seat_count,
                status=flight_pb2.ACTIVE,
            )
        except grpc.RpcError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.exception("ReserveSeats unexpected error")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()

    def ReleaseReservation(self, request, context):
        db = SessionLocal()
        try:
            reservation = db.query(SeatReservation).filter(
                SeatReservation.booking_id == uuid.UUID(request.booking_id),
                SeatReservation.status == ReservationStatus.ACTIVE,
            ).with_for_update().first()

            if not reservation:
                context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Active reservation for booking_id={request.booking_id} not found",
                )
                return

            flight = db.query(Flight).filter(
                Flight.id == reservation.flight_id
            ).with_for_update().first()

            reservation.status = ReservationStatus.RELEASED
            flight.available_seats += reservation.seat_count
            db.commit()

            cache.invalidate_flight(str(flight.id))
            cache.invalidate_search_for_flight(flight.origin, flight.destination)

            logger.info("ReleaseReservation: booking_id=%s, returned %d seats",
                        request.booking_id, reservation.seat_count)
            return flight_pb2.ReleaseReservationResponse(
                success=True,
                message=f"Released {reservation.seat_count} seats",
            )
        except grpc.RpcError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.exception("ReleaseReservation unexpected error")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()
