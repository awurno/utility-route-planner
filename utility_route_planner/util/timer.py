import time
import structlog

logger = structlog.get_logger(__name__)


def time_function(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"*** Function {func.__name__} took {end_time - start_time} to execute.")
        return result

    return wrapper
