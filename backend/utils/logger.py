"""
Logger-Modul für strukturiertes Logging.
- DEV: Detaillierte Debug-Logs (DEBUG Level)
- PROD: Nur wichtige Info/Warnings (INFO Level)

Nutzung:
    from utils.logger import logger

    logger.debug("🔍 Debugging info")
    logger.info("✅ Success info")
    logger.warning("⚠️ Warning")
    logger.error("❌ Error")
"""

import logging
import os
from enum import Enum


class Environment(str, Enum):
    """Application environment enum."""

    DEV = "development"
    PROD = "production"


def get_environment() -> Environment:
    """Get the current environment from NODE_ENV or default to development."""
    env_str = os.getenv("NODE_ENV", "development").lower()
    return Environment.DEV if env_str in ["dev", "development"] else Environment.PROD


def setup_logger(name: str = "billino") -> logging.Logger:
    """
    Configure and return logger with environment-aware settings.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    env = get_environment()

    # Determine log level based on environment
    if env == Environment.DEV:
        log_level = os.getenv("LOG_LEVEL", "DEBUG")
    else:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    # Create logger
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(log_level)

        # Create formatter with helpful prefixes
        formatter = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s")

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Log startup info
        logger.info(
            f"🚀 Logger initialized - Environment: {env.value} - Level: {log_level}"
        )

    return logger


# Create global logger instance
logger = setup_logger()
