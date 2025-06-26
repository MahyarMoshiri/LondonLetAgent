import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_DIR = "data/logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

DEFAULT_LOG_FILENAME = os.path.join(LOG_DIR, f"property_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

_logger_initialized = False

def setup_logging(name="PropertyAgent", log_level=logging.INFO, console_log_level=logging.INFO, log_file=DEFAULT_LOG_FILENAME):
    """
    Sets up a logger with both console and file handlers.
    This function should ideally be called once at the application startup.

    Args:
        name (str): The name of the root logger to configure.
        log_level (int): The logging level for the file handler.
        console_log_level (int): The logging level for the console handler.
        log_file (str): The full path to the log file.
    """
    global _logger_initialized
    # Configure the root logger or a specific application-wide logger
    logger = logging.getLogger(name) 
    
    # Check if this specific logger (not necessarily the root) has already been configured by this function
    # This is a simple check; more sophisticated checks might look at handler types or a global flag
    if _logger_initialized and any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        # print(f"Logger 	{name}	 already initialized by this setup function.")
        return

    logger.setLevel(logging.DEBUG)  # Set logger to lowest level to allow handlers to control their own levels

    # Prevent duplicate handlers if logger somehow got configured elsewhere, though our flag should handle it for this func
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s")

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(console_log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File Handler
    fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info(f"Logger 	{name}	 initialized by setup_logging. Logging to console and file: {log_file}")
    _logger_initialized = True # Mark that this setup has run for the given logger name

def get_logger(name="PropertyAgent"):
    """
    Retrieves a logger instance. It assumes setup_logging has been called for the root/main application logger.
    If setup_logging hasn't been called for the specific name, it will return a logger that might not have handlers
    or will inherit from the root logger's configuration if the root was configured.
    """
    return logging.getLogger(name)

# Example usage (primarily for testing this module directly):
if __name__ == "__main__":
    setup_logging(name="AppRootLogger", log_file="data/logs/app_root_test.log")
    main_logger = get_logger("AppRootLogger")
    main_logger.debug("This is a debug message from AppRootLogger.")
    main_logger.info("This is an info message from AppRootLogger.")

    module_specific_logger = get_logger("MyModule") # This will inherit from AppRootLogger if AppRootLogger is an ancestor
                                                  # Or it will be a new logger if AppRootLogger is not an ancestor (e.g. if name was different)
    module_specific_logger.info("Logging from MyModule, should go to AppRootLogger handlers.")

    another_logger = get_logger("AnotherIndependentLogger")
    # If "AnotherIndependentLogger" is not a child of "AppRootLogger" and hasn't been configured,
    # it might not output anything unless a root logger handler is set at a very basic level by Python.
    # To ensure it logs, it would also need setup_logging called for it, or ensure it's a child of a configured logger.
    another_logger.warning("This is a warning from AnotherIndependentLogger. Its output depends on root logger config or its own setup.")

    print(f"Log file created at: {os.path.abspath(DEFAULT_LOG_FILENAME)} or specific test log file.")

