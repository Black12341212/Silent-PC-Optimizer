import time
import ctypes
import threading
import psutil
from core.logger import logger

HAS_WIN32API = False
try:
    import win32api
    HAS_WIN32API = True
except ImportError:
    pass


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
                    target_h, target_m = self._parse_daily_time(daily_time)
                    if target_h is None:
                        logger.error(f"Неверный формат daily_time: {daily_time}")
                        continue
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

    @staticmethod
    def _parse_daily_time(daily_time):
        if not daily_time or not isinstance(daily_time, str):
            return None, None
        parts = daily_time.split(":")
        if len(parts) < 2:
            return None, None
        try:
            h = int(parts[0])
            m = int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return h, m
        except ValueError:
            pass
        return None, None


def get_idle_duration():
    if HAS_WIN32API:
        try:
            kernel32 = ctypes.windll.kernel32
            current_tick = kernel32.GetTickCount()
            last_input = win32api.GetLastInputInfo()
            idle_ms = (current_tick - last_input) & 0xFFFFFFFF
            return idle_ms / 1000.0
        except Exception:
            pass
    return 0


def hibernation_monitor(app_state, notify_callback=None):
    config = app_state["config"]
    hib_cfg = config.get("hibernation", {})
    if not hib_cfg.get("enabled", False):
        return

    idle_minutes = hib_cfg.get("idle_minutes", 30)
    ram_threshold = hib_cfg.get("ram_threshold", 90.0)
    notify_seconds = hib_cfg.get("notify_before_seconds", 10)

    while app_state["running"]():
        time.sleep(60)
        try:
            if not hib_cfg.get("enabled", False):
                continue

            idle_secs = get_idle_duration()
            idle_mins = idle_secs / 60.0

            if idle_mins < idle_minutes:
                continue

            ram = psutil.virtual_memory().percent
            if ram < ram_threshold:
                continue

            logger.warning(
                f"Гибернация: RAM {ram}% > {ram_threshold}%, "
                f"неактивность {int(idle_mins)} мин > {idle_minutes} мин"
            )

            if notify_callback:
                notify_callback(
                    f"ПК уйдёт в гибернацию через {notify_seconds} сек\n"
                    f"RAM: {ram}% | Неактивность: {int(idle_mins)} мин"
                )

            time.sleep(notify_seconds)

            idle_secs2 = get_idle_duration()
            if (idle_secs2 / 60.0) >= idle_minutes:
                ram2 = psutil.virtual_memory().percent
                if ram2 >= ram_threshold:
                    logger.info("Отправка ПК в гибернацию")
                    ctypes.windll.power.SetSuspendState(1, 0, 0)
        except Exception as e:
            logger.error(f"Ошибка мониторинга гибернации: {e}")
