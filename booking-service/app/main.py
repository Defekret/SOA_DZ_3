import logging

from fastapi import FastAPI

from app.routers import flights, bookings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Booking Service", version="1.0.0")

app.include_router(flights.router)
app.include_router(bookings.router)


@app.get("/health")
def health():
    return {"status": "ok"}
