import logging
import signal
import sys
from concurrent import futures

import grpc

import flight_pb2_grpc
from app.config import settings
from app.interceptors import AuthInterceptor
from app.servicer import FlightServicer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[AuthInterceptor()],
    )
    flight_pb2_grpc.add_FlightServiceServicer_to_server(FlightServicer(), server)
    address = f"[::]:{settings.grpc_port}"
    server.add_insecure_port(address)
    server.start()
    logger.info("Flight Service gRPC server listening on %s", address)

    def _shutdown(sig, frame):
        logger.info("Shutting down...")
        server.stop(5)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
