import time
import threading
import psutil
from core.logger import logger


class GameMode:
    def __init__(self, config):
        self.config = config
        self._active = False
        self._watching = False
        self._thread = None
        self._original_priorities = {}
        self._priority_boosted = []

    def start_watching(self):
        gm_cfg = self.config.get("game_mode", {})
        if not gm_cfg.get("enabled", False):
            return
        self._watching = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info("Игровой режим: мониторинг запущен")

    def stop_watching(self):
        self._watching = False
        self.deactivate()

    def _watch_loop(self):
        gm_cfg = self.config.get("game_mode", {})
        watch_apps = [a.lower() for a in gm_cfg.get("watch_apps", [])]
        while self._watching:
            try:
                running = self._get_running_apps()
                found_game = False
                for proc_name in running:
                    if any(wa in proc_name.lower() for wa in watch_apps):
                        found_game = True
                        break
                if found_game and not self._active:
                    self.activate()
                elif not found_game and self._active:
                    self.deactivate()
            except Exception as e:
                logger.debug(f"Ошибка мониторинга игр: {e}")
            time.sleep(5)

    def _get_running_apps(self):
        apps = set()
        for proc in psutil.process_iter(["name"]):
            try:
                apps.add(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return apps

    def activate(self):
        if self._active:
            return
        self._active = True
        logger.info("Игровой режим: АКТИВИРОВАН")
        self._boost_system()

    def deactivate(self):
        if not self._active:
            return
        self._active = False
        logger.info("Игровой режим: деактивирован")
        self._restore_system()

    def _boost_system(self):
        try:
            import ctypes
            try:
                ctypes.windll.psapi.SetProcessWorkingSetSize(
                    ctypes.windll.kernel32.GetCurrentProcess(), -1, -1
                )
            except Exception:
                pass
            self._set_process_priorities("high")
        except Exception as e:
            logger.debug(f"Ошибка буста: {e}")

    def _restore_system(self):
        try:
            self._set_process_priorities("normal")
        except Exception as e:
            logger.debug(f"Ошибка восстановления: {e}")

    def _set_process_priorities(self, level):
        priority_map = {
            "high": psutil.HIGH_PRIORITY_CLASS if hasattr(psutil, 'HIGH_PRIORITY_CLASS') else 256,
            "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS if hasattr(psutil, 'ABOVE_NORMAL_PRIORITY_CLASS') else 32768,
            "normal": psutil.NORMAL_PRIORITY_CLASS if hasattr(psutil, 'NORMAL_PRIORITY_CLASS') else 32,
        }
        nice_val = priority_map.get(level, priority_map["normal"])
        gm_cfg = self.config.get("game_mode", {})
        watch_apps = [a.lower() for a in gm_cfg.get("watch_apps", [])]
        if not watch_apps:
            return
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info.get("name")
                if not name:
                    continue
                if any(wa in name.lower() for wa in watch_apps):
                    p = psutil.Process(proc.info["pid"])
                    try:
                        p.nice(nice_val)
                    except Exception:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    @property
    def is_active(self):
        return self._active


class StreamingMode:
    def __init__(self, config):
        self.config = config
        self._active = False

    def activate(self):
        self._active = True
        sm_cfg = self.config.get("streaming_mode", {})
        if sm_cfg.get("prioritize_obs", True):
            self._set_priority_by_name("obs64.exe", "high")
            self._set_priority_by_name("obs32.exe", "high")
        if sm_cfg.get("prioritize_browsers", True):
            for name in ["chrome.exe", "firefox.exe", "msedge.exe"]:
                self._set_priority_by_name(name, "above_normal")
        logger.info("Режим стриминга: активирован")

    def deactivate(self):
        self._active = False
        for name in ["obs64.exe", "obs32.exe", "chrome.exe", "firefox.exe", "msedge.exe"]:
            self._set_priority_by_name(name, "normal")
        logger.info("Режим стриминга: деактивирован")

    def _set_priority_by_name(self, process_name, level):
        priority_map = {
            "high": psutil.HIGH_PRIORITY_CLASS if hasattr(psutil, 'HIGH_PRIORITY_CLASS') else -10,
            "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS if hasattr(psutil, 'ABOVE_NORMAL_PRIORITY_CLASS') else -5,
            "normal": psutil.NORMAL_PRIORITY_CLASS if hasattr(psutil, 'NORMAL_PRIORITY_CLASS') else 10,
        }
        nice_val = priority_map.get(level, 10)
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"].lower() == process_name.lower():
                    p = psutil.Process(proc.info["pid"])
                    try:
                        p.nice(nice_val)
                    except Exception:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    @property
    def is_active(self):
        return self._active


class PresentationMode:
    def __init__(self, config):
        self.config = config
        self._active = False
        self._dnd_was_enabled = False

    def activate(self):
        self._active = True
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-Command",
                 "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' -Name 'NOCGlobalSettingToastsEnabled' -Value 0 -Force"],
                capture_output=True, timeout=10, creationflags=0x08000000
            )
            subprocess.run(
                ["powershell", "-Command",
                 "New-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' -Name 'NOCGlobalSettingToastsEnabled' -Value 0 -PropertyType DWord -Force"],
                capture_output=True, timeout=10, creationflags=0x08000000
            )
        except Exception:
            pass
        logger.info("Режим презентации: активирован")

    def deactivate(self):
        self._active = False
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-Command",
                 "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' -Name 'NOCGlobalSettingToastsEnabled' -Value 1 -Force"],
                capture_output=True, timeout=10, creationflags=0x08000000
            )
        except Exception:
            pass
        logger.info("Режим презентации: деактивирован")

    @property
    def is_active(self):
        return self._active
