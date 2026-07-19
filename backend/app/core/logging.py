import logging
import sys

_PII_NOTE = (
    "Never pass child first_name, notes, input_snapshot, or result_json content to this logger — "
    "log only IDs, status codes, and durations."
)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Logger for app modules. See module docstring: never log child PII."""
    return logging.getLogger(name)
