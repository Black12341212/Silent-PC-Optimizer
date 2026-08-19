import time
import threading
from core.logger import logger


class TaskScheduler:
    def __init__(self, config, callback):
        self.config = config
        self.callback = callback
        self._running = False
        self._thread = None
        self._last_run = 0

    def start(self):
        sched_cfg = self.config.get("scheduled_optimization", {})
        if not sched_cfg.get("enabled", False):
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Планировщик задач запущен")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                sched_cfg = self.config.get("scheduled_optimization", {})
                mode = sched_cfg.get("mode", "interval")
                now = time.time()
                should_run = False
                if mode == "interval":
                    interval_hours = sched_cfg.get("interval_hours", 2)
                    interval_seconds = interval_hours * 3600
                    if (now - self._last_run) >= interval_seconds:
                        should_run = True
                elif mode == "daily":
                    daily_time = sched_cfg.get("daily_time", "03:00")
                    h, m = daily_time.split(":")
                    target_h, target_m = int(h), int(m)
                    import datetime
                    current = datetime.datetime.now()
                    if current.hour == target_h and current.minute == target_m:
                        if (now - self._last_run) > 300:
                            should_run = True
                if should_run:
                    logger.info("Планировщик: запуск оптимизации")
                    self._last_run = now
                    self.callback()
            except Exception as e:
                logger.error(f"Ошибка планировщика: {e}")
            time.sleep(30)

    def get_next_run(self):
        sched_cfg = self.config.get("scheduled_optimization", {})
        mode = sched_cfg.get("mode", "interval")
        now = time.time()
        if mode == "interval":
            interval_hours = sched_cfg.get("interval_hours", 2)
            elapsed = now - self._last_run
            remaining = max(0, interval_hours * 3600 - elapsed)
            h = int(remaining // 3600)
            m = int((remaining % 3600) // 60)
            return f"{h}h {m}m"
        elif mode == "daily":
            return sched_cfg.get("daily_time", "03:00")
        return "N/A"
