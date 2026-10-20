import logging
import sys
import re

SENSITIVE_PATTERNS = [
    re.compile(r"(password\s*[:=]\s*)([^\s,;&]+)", re.IGNORECASE),
    re.compile(r"(secret\s*[:=]\s*)([^\s,;&]+)", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[:=]\s*)([^\s,;&]+)", re.IGNORECASE),
    re.compile(r"(bearer\s+)([a-zA-Z0-9_\-\.]{15,})", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*)([^\s,;&]+)", re.IGNORECASE),
]

def sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(r"\1[REDACTED]", sanitized)
    return sanitized

class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        return sanitize_text(orig)

def setup_logger(name: str = "workbench", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

logger = setup_logger()
