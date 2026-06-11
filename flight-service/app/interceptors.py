import logging
import grpc
from app.config import settings

logger = logging.getLogger(__name__)


class AuthInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        api_key = metadata.get("x-api-key")

        if not api_key or api_key != settings.api_key:
            logger.warning("UNAUTHENTICATED request to %s", handler_call_details.method)

            def reject(request, context):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing API key")

            return grpc.unary_unary_rpc_method_handler(reject)

        return continuation(handler_call_details)
