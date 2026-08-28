"""
NetPulse Structured Logging Engine.

Supports both human-readable console logging with colorization and
machine-readable structured JSON logging with test contextual metadata.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional


class JSONLogFormatter(logging.Formatter):
    """
    Formats log records as newline-delimited JSON objects with full structured context.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include structured context if present
        context_fields = [
            "test_name",
            "protocol",
            "source",
            "destination",
            "duration_ms",
            "status",
            "error",
            "retry_count",
            "bytes_transferred",
            "packet_count"
        ]

        for field in context_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Formats log records for terminal output with ANSI color codes.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        time_str = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Format contextual suffix if test/protocol fields are available
        ctx_parts = []
        if hasattr(record, "protocol"):
            ctx_parts.append(f"proto={getattr(record, 'protocol')}")
        if hasattr(record, "test_name"):
            ctx_parts.append(f"test={getattr(record, 'test_name')}")
        if hasattr(record, "status"):
            ctx_parts.append(f"status={getattr(record, 'status')}")
        if hasattr(record, "duration_ms"):
            ctx_parts.append(f"{getattr(record, 'duration_ms'):.2f}ms")

        context_str = f" [{', '.join(ctx_parts)}]" if ctx_parts else ""

        message = record.getMessage()
        formatted = f"{time_str} {color}{self.BOLD}[{record.levelname:<5}]{self.RESET} {record.name}: {message}{context_str}"

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        return formatted


class TestContextAdapter(logging.LoggerAdapter):
    """
    LoggerAdapter that injects test and network context into every log record.
    """

    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        merged_extra = dict(self.extra)
        if "extra" in kwargs:
            merged_extra.update(kwargs["extra"])
        kwargs["extra"] = merged_extra
        return msg, kwargs

    def update_context(self, **kwargs: Any) -> None:
        """Update context values for subsequent log calls."""
        self.extra.update(kwargs)


_configured = False


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = "logs/netpulse.log",
    json_file: Optional[str] = "logs/netpulse.json.log",
    console: bool = True
) -> logging.Logger:
    """
    Initialize global root logger with both console and structured JSON handlers.
    """
    global _configured

    root_logger = logging.getLogger("netpulse")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers if already configured
    if _configured:
        return root_logger

    root_logger.handlers.clear()

    # 1. Console Handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(ColoredConsoleFormatter())
        root_logger.addHandler(console_handler)

    # 2. File Handler (Human-readable)
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(file_path), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # 3. JSON File Handler (Machine-readable)
    if json_file:
        json_path = Path(json_file)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_handler = logging.FileHandler(str(json_path), encoding="utf-8")
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONLogFormatter())
        root_logger.addHandler(json_handler)

    _configured = True
    return root_logger


def get_logger(name: str, **context: Any) -> TestContextAdapter:
    """
    Get a structured contextual logger for a component or test.
    """
    base_logger = logging.getLogger(f"netpulse.{name}" if not name.startswith("netpulse") else name)
    return TestContextAdapter(base_logger, extra=context)
