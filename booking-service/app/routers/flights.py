from typing import Optional

import grpc
from fastapi import APIRouter, HTTPException, Query

from app.grpc_client import flight_client

router = APIRouter()


def _flight_to_dict(f):
    return {
        "id": f.id,
        "flight_number": f.flight_number,
        "airline": f.airline,
        "origin": f.origin,
        "destination": f.destination,
        "departure_time": f.departure_time.ToJsonString(),
        "arrival_time": f.arrival_time.ToJsonString(),
        "total_seats": f.total_seats,
        "available_seats": f.available_seats,
        "price": f.price,
        "status": f.status,
    }


@router.get("/flights")
def search_flights(
    origin: str = Query(..., description="IATA origin code"),
    destination: str = Query(..., description="IATA destination code"),
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD"),
):
    try:
        resp = flight_client.search_flights(origin=origin, destination=destination, date=date or "")
        return [_flight_to_dict(f) for f in resp.flights]
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
            raise HTTPException(status_code=400, detail=e.details())
        raise HTTPException(status_code=503, detail="Flight service unavailable")


@router.get("/flights/{flight_id}")
def get_flight(flight_id: str):
    try:
        f = flight_client.get_flight(flight_id)
        return _flight_to_dict(f)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail=e.details())
        raise HTTPException(status_code=503, detail="Flight service unavailable")
