# Add to utils/profiler.py
import time
import json
from pathlib import Path
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Store timings in memory
TIMINGS = []

def profile(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        
        timing_data = {
            "function": func.__name__,
            "duration_seconds": round(duration, 2),
            "timestamp": time.time()
        }
        TIMINGS.append(timing_data)
        logger.info(f"⏱️ {func.__name__}: {duration:.2f}s")
        return result
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        timing_data = {
            "function": func.__name__,
            "duration_seconds": round(duration, 2),
            "timestamp": time.time()
        }
        TIMINGS.append(timing_data)
        logger.info(f"⏱️ {func.__name__}: {duration:.2f}s")
        return result
    
    # Return appropriate wrapper
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def save_timings(preview_token: str):
    """Save timings to JSON file"""
    output_file = Path("performance_logs") / f"{preview_token}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(TIMINGS, f, indent=2)
    
    TIMINGS.clear()  # Reset for next run
    logger.info(f"Performance data saved: {output_file}")
