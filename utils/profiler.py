# profiler.py
import time
import json
from pathlib import Path
from functools import wraps
import logging
from threading import Lock

logger = logging.getLogger(__name__)

_sessions = {}
_sessions_lock = Lock()
_active_session_id = None  # Track current active session

class Session:
    def __init__(self, session_id: str, label: str):
        self.session_id = session_id
        self.label = label
        self.timings = []
        self.start_time = time.time()
        self.end_time = None
        self.lock = Lock()
    
    def add_timing(self, data):
        with self.lock:
            self.timings.append(data)
    
    def finalize(self):
        self.end_time = time.time()
        with self.lock:
            return {
                "session_label": self.label,
                "total_duration": round(self.end_time - self.start_time, 2),
                "function_calls": sorted(self.timings, key=lambda x: x['timestamp'])
            }

def start_session(session_id: str, label: str):
    global _active_session_id
    with _sessions_lock:
        session = Session(session_id, label)
        _sessions[session_id] = session
        _active_session_id = session_id
        logger.info(f"📊 Started profiling: {label}")

def end_session(session_id: str):
    global _active_session_id
    with _sessions_lock:
        session = _sessions.pop(session_id, None)
        if _active_session_id == session_id:
            _active_session_id = None
    
    if not session:
        return
    
    data = session.finalize()
    
    output_file = Path("performance_logs") / f"{data['session_label']}_{int(time.time())}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"📁 Saved: {output_file} (Total: {data['total_duration']}s)")

def profile(func):
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        with _sessions_lock:
            session = _sessions.get(_active_session_id) if _active_session_id else None
        
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        
        if session:
            timing_data = {
                "function": func.__name__,
                "duration_seconds": round(duration, 2),
                "timestamp": round(start, 2)
            }
            session.add_timing(timing_data)
        
        logger.info(f"⏱️ {func.__name__}: {duration:.2f}s")
        return result
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        with _sessions_lock:
            session = _sessions.get(_active_session_id) if _active_session_id else None
        
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        if session:
            timing_data = {
                "function": func.__name__,
                "duration_seconds": round(duration, 2),
                "timestamp": round(start, 2)
            }
            session.add_timing(timing_data)
        
        logger.info(f"⏱️ {func.__name__}: {duration:.2f}s")
        return result
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
