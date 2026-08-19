import ctypes
import threading
from core.logger import logger

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


class HotkeyManager:
    def __init__(self, config, callbacks):
        self.config = config
        self.callbacks = callbacks
        self._registered = []

    def register_all(self):
        if not HAS_KEYBOARD:
            logger.warning("Библиотека keyboard не установлена: pip install keyboard")
            return
        hk_cfg = self.config.get("hotkeys", {})
        if not hk_cfg.get("enabled", False):
            return
        optimize_key = hk_cfg.get("optimize", "ctrl+alt+o")
        if optimize_key and "optimize" in self.callbacks:
            try:
                keyboard.add_hotkey(optimize_key, self.callbacks["optimize"])
                self._registered.append(optimize_key)
                logger.info(f"Горячая клавиша зарегистрирована: {optimize_key}")
            except Exception as e:
                logger.error(f"Ошибка регистрации горячей клавиши: {e}")

    def unregister_all(self):
        if not HAS_KEYBOARD:
            return
        for key in self._registered:
            try:
                keyboard.remove_hotkey(key)
            except Exception:
                pass
        self._registered.clear()

    def update_hotkey(self, action, key_combination):
        if not HAS_KEYBOARD:
            return False
        if action in self.callbacks:
            try:
                keyboard.remove_hotkey(key_combination)
            except Exception:
                pass
            try:
                keyboard.add_hotkey(key_combination, self.callbacks[action])
                logger.info(f"Горячая клавиша обновлена: {action} -> {key_combination}")
                return True
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                return False
        return False
