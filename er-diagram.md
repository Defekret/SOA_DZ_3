А # ER-диаграмма (3NF)

## Flight Service

```mermaid
erDiagram
    flights {
        UUID id PK
        VARCHAR(10) flight_number
        VARCHAR(100) airline
        VARCHAR(3) origin
        VARCHAR(3) destination
        TIMESTAMPTZ departure_time
        TIMESTAMPTZ arrival_time
        INTEGER total_seats
        INTEGER available_seats
        NUMERIC(10_2) price
        flightstatus status
    }

    seat_reservations {
        UUID id PK
        UUID flight_id FK
        UUID booking_id UK
        INTEGER seat_count
        reservationstatus status
        TIMESTAMPTZ created_at
    }

    flights ||--o{ seat_reservations : "has"
```

**Энумы:**
- `flightstatus`: SCHEDULED | DEPARTED | CANCELLED | COMPLETED
- `reservationstatus`: ACTIVE | RELEASED | EXPIRED

**Ограничения целостности:**
- `total_seats > 0`
- `available_seats >= 0`
- `price > 0`
- `seat_count > 0`
- `booking_id` уникален (1 бронирование = 1 резервация)

---

## Booking Service

```mermaid
erDiagram
    bookings {
        UUID id PK
        VARCHAR user_id
        VARCHAR flight_id
        VARCHAR passenger_name
        VARCHAR passenger_email
        INTEGER seat_count
        NUMERIC(10_2) total_price
        bookingstatus status
        TIMESTAMPTZ created_at
    }
```

**Энумы:**
- `bookingstatus`: CONFIRMED | CANCELLED

**Ограничения целостности:**
- `seat_count > 0`
- `total_price > 0`

---

## Взаимосвязь между сервисами

`bookings.flight_id` → ссылается на `flights.id` в Flight Service (межсервисная ссылка, без FK на уровне БД).  
`seat_reservations.booking_id` → соответствует `bookings.id` из Booking Service (без FK, разные БД).
