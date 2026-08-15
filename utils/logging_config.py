from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_logging(user_activity_log: Path, error_log: Path) -> tuple[logging.Logger, logging.Logger]:
    formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    console_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    activity_logger = logging.getLogger("user_activity")
    activity_logger.setLevel(logging.INFO)
    activity_logger.propagate = False
    _replace_handlers(activity_logger, user_activity_log, formatter, logging.INFO, console_formatter, sys.stdout)

    error_logger = logging.getLogger("error")
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False
    _replace_handlers(error_logger, error_log, formatter, logging.ERROR, console_formatter, sys.stderr)

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
    return activity_logger, error_logger


def _replace_handlers(
    logger: logging.Logger,
    path: Path,
    file_formatter: logging.Formatter,
    level: int,
    console_formatter: logging.Formatter | None = None,
    stream=None,
) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(stream or sys.stdout)
    console_handler.setFormatter(console_formatter or file_formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
