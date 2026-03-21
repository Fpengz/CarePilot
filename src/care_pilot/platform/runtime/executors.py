"""
Provide dedicated execution pools for heavy or specialized workloads.

This module centralizes executors to prevent starvation of the main ASGI
event loop and default thread pool by heavy ML or I/O tasks.
"""

import atexit
from concurrent.futures import ThreadPoolExecutor

from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)

# Dedicated pool for ML inference (PyTorch/Transformers)
# High CPU/Memory usage, isolated from general I/O tasks.
# Using a small number of workers to prevent system overload on single-node deployments.
_ML_EXECUTOR = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="ml_worker"
)

# Dedicated pool for general blocking I/O (Database, Cloud APIs)
_IO_EXECUTOR = ThreadPoolExecutor(
    max_workers=32,
    thread_name_prefix="io_worker"
)

def get_ml_executor() -> ThreadPoolExecutor:
    """Return the shared ML thread pool executor."""
    return _ML_EXECUTOR

def get_io_executor() -> ThreadPoolExecutor:
    """Return the shared I/O thread pool executor."""
    return _IO_EXECUTOR

def shutdown_executors() -> None:
    """Gracefully shutdown all shared executors."""
    logger.info("shutting_down_executors")
    _ML_EXECUTOR.shutdown(wait=True)
    _IO_EXECUTOR.shutdown(wait=True)

atexit.register(shutdown_executors)
