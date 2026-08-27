import time
import threading
from collections import deque
import psutil


class MemoryTracker:
    def __init__(self, max_minutes=30, interval=30):
        self.max_minutes = max_minutes
        self.interval = interval
        self.max_points = (max_minutes * 60) // interval
        self.buffer = deque(maxlen=self.max_points)
        self._lock = threading.Lock()

    def record(self):
        ram = psutil.virtual_memory().percent
        free_gb = round(psutil.virtual_memory().available / (1024 ** 3), 2)
        with self._lock:
            self.buffer.append({
                "time": time.time(),
                "ram_percent": ram,
                "free_gb": free_gb
            })

    def get_data(self):
        with self._lock:
            return list(self.buffer)

    def get_latest(self):
        with self._lock:
            if self.buffer:
                return self.buffer[-1]
            return {"time": time.time(), "ram_percent": 0, "free_gb": 0}
