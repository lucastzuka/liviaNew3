"""
security_utils.py

Security utilities for environment variable management and logging redaction.
"""

import os
import logging
import re

def get_required_env(var_name: str) -> str:
    """
    Fetch a required environment variable or raise ValueError if missing.
    """
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Required environment variable '{var_name}' is missing")
    return value

class SecretRedactorFilter(logging.Filter):
    """
    Logging filter that redacts secrets such as API keys in log messages.

    - Redacts OpenAI keys: sk-[A-Za-z0-9]{16,}
    - Redacts base64 strings with ':' delimiter (Zapier keys): [A-Za-z0-9+/=]{16,}:[A-Za-z0-9+/=]{16,}
    - Redacts generic patterns that look like secrets.
    """
    SK_PATTERN = re.compile(r"sk-[A-Za-z0-9]{16,}")
    BASE64_COLON_PATTERN = re.compile(r"\b([A-Za-z0-9+/=]{16,}:[A-Za-z0-9+/=]{16,})\b")
    # Add more patterns as needed

    def filter(self, record):
        original = record.getMessage()
        redacted = original
        redacted = self.SK_PATTERN.sub("***REDACTED***", redacted)
        redacted = self.BASE64_COLON_PATTERN.sub("***REDACTED***", redacted)
        # Add more substitutions as needed
        # Replace the message in the record (for most logging handlers)
        record.msg = redacted
        if hasattr(record, "message"):
            record.message = redacted
        return True

def setup_global_logging_redaction():
    """
    Attach the SecretRedactorFilter to all handlers of the root logger.
    """
    redactor = SecretRedactorFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(redactor)
    # Also add to any loggers that are created with logging.getLogger(__name__)
    # (Optional: recursively add to all known loggers)
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        for handler in getattr(logger, 'handlers', []):
            handler.addFilter(redactor)