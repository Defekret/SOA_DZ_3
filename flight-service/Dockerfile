FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/flight.proto /proto/flight.proto
RUN python -m grpc_tools.protoc \
    -I /proto \
    --python_out=/app \
    --grpc_python_out=/app \
    /proto/flight.proto

COPY . .

EXPOSE 50051

CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
