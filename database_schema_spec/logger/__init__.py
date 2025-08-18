"""Centralized logging configuration for the database schema specification tool.

This module provides a configured logger instance that can be imported and used
throughout the application. The logger is configured with both console and file
handlers using settings from logging_config.json.

Usage:
    from database_schema_spec.logger import logger

    logger.info("This is an info message")
    logger.error("This is an error message")
    logger.debug("This is a debug message")
"""

from .logger import logger, setup_logger

__all__ = ["logger", "setup_logger"]
