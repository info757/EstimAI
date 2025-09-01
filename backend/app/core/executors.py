# backend/app/core/executors.py
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import atexit

# Tune this based on your machine / expected concurrency.
# 4–8 is a good starting point for local/dev.
EXECUTOR = ThreadPoolExecutor(max_workers=4)

def _shutdown_executor():
    # Wait for running tasks to finish on interpreter shutdown.
    EXECUTOR.shutdown(wait=True, cancel_futures=False)

atexit.register(_shutdown_executor)
