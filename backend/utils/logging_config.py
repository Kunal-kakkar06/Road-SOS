import logging
import json
import re
import os
import contextvars
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variables for correlation across threads/coroutines
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
job_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("job_id", default=None)
worker_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("worker_id", default=None)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)

# Sensitive data redaction patterns
REDACT_KEYS = {"password", "secret", "token", "authorization", "auth", "jwt", "bearer", "symptoms", "symptom_text", "patient_text", "transcript"}
SENSITIVE_HEADER_PATTERN = re.compile(r'(Bearer\s+|Token\s+|password=)[^\s,]+', re.IGNORECASE)
DB_CREDENTIAL_PATTERN = re.compile(r'postgresql(\+[a-z0-9]+)?://([^:]+):([^@]+)@', re.IGNORECASE)

class StructuredJsonFormatter(logging.Formatter):
    """
    Production-grade structured JSON log formatter.
    Ensures consistent log fields and automatic sensitive data redaction.
    """
    def __init__(self, service_name: str = "roadsos-api"):
        super().__init__()
        self.service_name = service_name
        self.environment = os.getenv("ENVIRONMENT", "production")

    def sanitize_val(self, key: str, val: Any) -> Any:
        if isinstance(val, str):
            # Check string for JWT or authorization tokens
            if "Bearer " in val or "token" in key.lower():
                return "[REDACTED_TOKEN]"
            if "password" in key.lower() or "secret" in key.lower():
                return "[REDACTED_SECRET]"
            if key.lower() in REDACT_KEYS:
                return "[REDACTED_SENSITIVE]"
            val = DB_CREDENTIAL_PATTERN.sub(r'postgresql\1://\2:[REDACTED_DB_PASS]@', val)
            val = SENSITIVE_HEADER_PATTERN.sub(r'\1[REDACTED]', val)
            return val
        elif isinstance(val, dict):
            return {k: self.sanitize_val(k, v) for k, v in val.items()}
        elif isinstance(val, list):
            return [self.sanitize_val(key, item) for item in val]
        return val

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", self.service_name),
            "environment": self.environment,
            "event_name": getattr(record, "event_name", record.getMessage()),
            "logger": record.name,
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
            "job_id": getattr(record, "job_id", None) or job_id_var.get(),
            "worker_id": getattr(record, "worker_id", None) or worker_id_var.get(),
            "user_id": getattr(record, "user_id", None) or user_id_var.get(),
            "processing_mode": getattr(record, "processing_mode", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "status": getattr(record, "status", None),
            "attempt_count": getattr(record, "attempt_count", None),
        }

        # Include exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Include extra dictionary fields if added to record
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            for k, v in record.extra_fields.items():
                if k not in log_obj:
                    log_obj[k] = self.sanitize_val(k, v)

        # Remove null values for concise log output
        clean_log = {k: self.sanitize_val(k, v) for k, v in log_obj.items() if v is not None}
        return json.dumps(clean_log)


def setup_structured_logging(service_name: str = "roadsos-api", log_level: str = "INFO"):
    """
    Configures the root logger with StructuredJsonFormatter.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter(service_name=service_name))
    root_logger.addHandler(handler)

    # Disable overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger

# Module logger
logger = logging.getLogger("roadsos")
