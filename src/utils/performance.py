import time
import logging
from contextlib import contextmanager


@contextmanager
def performance_monitor(operation_name: str):
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        logging.info(f"{operation_name} took {duration:.2f} seconds")
