import time
import ctypes
import threading
from core.logger import logger
import psutil

HAS_WIN32API = False
try:
    import win32api
    HAS_WIN32API = True
except ImportError:
    pass


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
                    ctypes.windll.power.SetSuspendState(0, 0, 0)
        except Exception as e:
            logger.error(f"Ошибка мониторинга гибернации: {e}")
