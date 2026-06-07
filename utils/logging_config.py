from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(user_activity_log: Path, error_log: Path) -> tuple[logging.Logger, logging.Logger]:
    formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    activity_logger = logging.getLogger("user_activity")
    activity_logger.setLevel(logging.INFO)
    activity_logger.propagate = False
    _replace_handlers(activity_logger, user_activity_log, formatter, logging.INFO)

    error_logger = logging.getLogger("error")
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False
    _replace_handlers(error_logger, error_log, formatter, logging.ERROR)

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
    return activity_logger, error_logger


def _replace_handlers(logger: logging.Logger, path: Path, formatter: logging.Formatter, level: int) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)
