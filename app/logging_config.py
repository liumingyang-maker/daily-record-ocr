"""Logging configuration using loguru."""

import sys
from loguru import logger
from app.settings import LOG_LEVEL, DATA_DIR


def setup_logging() -> None:
    """Configure loguru logger for the application."""
    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # File handler - rotation daily
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        level=LOG_LEVEL,
        rotation="00:00",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
