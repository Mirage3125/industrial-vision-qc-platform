import logging
import logging.handlers
import sys
from pathlib import Path

from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str, log_file: Path) -> None:
    """Configure JSON logs for stdout and a size-rotated local file."""

    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        rename_fields={"levelname": "level"},
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
