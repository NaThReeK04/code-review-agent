import logging
import sys
import structlog

def setup_logging():
    """
    Configure structured logging for the entire application.
    
    This sets up structlog to process all logs from Python's
    standard `logging` library, formatting them as JSON.
    """
    
    # 1. Base logging configuration
    logging.basicConfig(
        format="%(message)s",  # Handled by structlog
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # 2. Structlog processors
    # These processors enrich and format the log entries.
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 3. Get the root logger
    logger = structlog.get_logger("code_review_agent")
    logger.info("Structured logging configured.")