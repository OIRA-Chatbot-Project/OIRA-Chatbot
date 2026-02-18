"""
Centralized logging configuration for the backend.
Replaces scattered print() statements with proper logging.
"""

import logging
import sys
from typing import Optional


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger for the application.
    Call this once at application startup.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Configured logger instance

    Usage:
        from logger import get_logger
        logger = get_logger(__name__)
        logger.info("This is an info message")
        logger.warning("This is a warning")
        logger.error("This is an error")
    """
    return logging.getLogger(name)


# Pre-configured loggers for common modules
chatbot_logger = get_logger("chatbot")
routes_logger = get_logger("routes")
