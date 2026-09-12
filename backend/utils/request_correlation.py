import uuid
import re
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logging_config import request_id_var, user_id_var

# Safe request ID pattern: alphanumeric, hyphen, underscore, length 1..64
REQUEST_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')
logger = logging.getLogger("roadsos.api")

class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure request correlation ID (X-Request-ID) is propagated
    across all HTTP requests, background jobs, workers, and response headers.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        raw_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
        
        # Validate request ID to prevent header abuse or log injection
        if raw_id and REQUEST_ID_PATTERN.match(raw_id):
            request_id = raw_id
        else:
            request_id = str(uuid.uuid4())

        # Set contextvar for structured logger
        req_token = request_id_var.set(request_id)
        request.state.request_id = request_id

        start_time = time.time()
        
        # Log request start
        logger.info(
            "API Request Received",
            extra={
                "event_name": "api.request.received",
                "request_id": request_id,
                "extra_fields": {
                    "method": request.method,
                    "url_path": request.url.path,
                    "client_host": request.client.host if request.client else "unknown"
                }
            }
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            # Log request completion
            logger.info(
                "API Request Completed",
                extra={
                    "event_name": "api.request.completed",
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "status": response.status_code,
                    "extra_fields": {
                        "method": request.method,
                        "url_path": request.url.path
                    }
                }
            )
            
            # Inject correlation header into response
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "API Request Failed",
                extra={
                    "event_name": "api.request.failed",
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "status": 500,
                    "extra_fields": {
                        "method": request.method,
                        "url_path": request.url.path,
                        "error": str(exc)
                    }
                },
                exc_info=True
            )
            raise exc
        finally:
            request_id_var.reset(req_token)
