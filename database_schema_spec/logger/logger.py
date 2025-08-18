import atexit
import json
import logging
import logging.config
from pathlib import Path

# Configure logging
logger = logging.getLogger("SchemaGenerator")


def setup_logger():
    config_file = Path(__file__).parent / "logging_config.json"
    with open(config_file) as f:
        config = json.load(f)
    logging.config.dictConfig(config)
    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None and hasattr(queue_handler, "listener"):
        # Type checker doesn't understand hasattr, so we access listener safely
        listener = getattr(queue_handler, "listener", None)
        if listener is not None:
            listener.start()
            atexit.register(listener.stop)


if __name__ == "__main__":
    setup_logger()
    # If this module is run directly, set up the logger
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
