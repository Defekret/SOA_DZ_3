import time
import logging

import grpc

import flight_pb2
import flight_pb2_grpc
from app.config import settings

logger = logging.getLogger(__name__)

_RETRYABLE = {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED}
_MAX_RETRIES = 3
_BACKOFF_MS = [100, 200, 400]

_DEADLINES = {
    "search": 5.0,
    "get": 3.0,
    "reserve": 10.0,
    "release": 10.0,
}


def _metadata():
    return [("x-api-key", settings.flight_service_api_key)]


def _retry(fn, *args, timeout: float, **kwargs):
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, timeout=timeout, **kwargs)
        except grpc.RpcError as exc:
            if exc.code() not in _RETRYABLE:
                raise
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _BACKOFF_MS[attempt] / 1000
                logger.warning(
                    "gRPC %s failed (attempt %d/%d), retrying in %.0fms",
                    fn.__name__ if hasattr(fn, "__name__") else "call",
                    attempt + 1,
                    _MAX_RETRIES,
                    _BACKOFF_MS[attempt],
                )
                time.sleep(delay)
    raise last_exc


class FlightServiceClient:
    def __init__(self):
        self._channel = grpc.insecure_channel(settings.flight_service_url)
        self._stub = flight_pb2_grpc.FlightServiceStub(self._channel)

    def search_flights(self, origin: str, destination: str, date: str = "") -> flight_pb2.SearchFlightsResponse:
        req = flight_pb2.SearchFlightsRequest(origin=origin, destination=destination, date=date)
        return _retry(self._stub.SearchFlights, req, metadata=_metadata(), timeout=_DEADLINES["search"])

    def get_flight(self, flight_id: str) -> flight_pb2.FlightInfo:
        req = flight_pb2.GetFlightRequest(flight_id=flight_id)
        return _retry(self._stub.GetFlight, req, metadata=_metadata(), timeout=_DEADLINES["get"])

    def reserve_seats(self, flight_id: str, seat_count: int, booking_id: str) -> flight_pb2.ReserveSeatsResponse:
        req = flight_pb2.ReserveSeatsRequest(
            flight_id=flight_id,
            seat_count=seat_count,
            booking_id=booking_id,
        )
        return _retry(self._stub.ReserveSeats, req, metadata=_metadata(), timeout=_DEADLINES["reserve"])

    def release_reservation(self, booking_id: str) -> flight_pb2.ReleaseReservationResponse:
        req = flight_pb2.ReleaseReservationRequest(booking_id=booking_id)
        return _retry(self._stub.ReleaseReservation, req, metadata=_metadata(), timeout=_DEADLINES["release"])


flight_client = FlightServiceClient()
