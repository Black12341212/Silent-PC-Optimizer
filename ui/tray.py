import threading
import psutil
import pystray
from PIL import Image, ImageDraw
from core.config import load_config, save_config, toggle_autostart, is_autostart_active
from core.logger import logger
from core.optimizer import clean_temp_files, clean_tmp_folder, clean_recycle_bin, clean_browser_cache
from core.processes import get_heavy_processes, kill_processes
from core.scheduler import hibernation_monitor
from core.system_cleaner import clean_all_system
from core.system_monitor import SystemMonitor, check_alerts
from core.history import record_optimization
from core.game_mode import GameMode, StreamingMode, PresentationMode
from core.benchmark import Benchmark
from core.task_scheduler import TaskScheduler
from core.hotkeys import HotkeyManager
from ui.i18n import t
from ui.graph import open_ram_graph
from ui.theme import ThemeManager


def create_image(ram_percent=0):
    width = 64
    height = 64
    image = Image.new("RGB", (width, height), (255, 255, 255))
    dc = ImageDraw.Draw(image)

    if ram_percent > 85:
        color = (200, 40, 40)
    elif ram_percent > 70:
        color = (200, 160, 0)
    else:
        color = (0, 128, 0)

    dc.ellipse((4, 4, width - 4, height - 4), fill=color)
    return image


class App:
    def __init__(self):
        self.config = load_config()
        self.running = True
        self.auto_mode = self.config.get("auto_mode", True)
        self.icon = None
        self.main_window = None
        self._main_window_open = False
        self.tk_root = None

        self.theme_manager = ThemeManager(self.config)

        from core.memory_tracker import MemoryTracker
        self.memory_tracker = MemoryTracker(
            max_minutes=30,
            interval=self.config.get("check_interval", 30)
        )

        self.system_monitor = SystemMonitor()
        self.game_mode = GameMode(self.config)
        self.streaming_mode = StreamingMode(self.config)
        self.presentation_mode = PresentationMode(self.config)
        self.benchmark = Benchmark()
        self.scheduler = TaskScheduler(self.config, self.perform_optimization)
        self.hotkey_manager = HotkeyManager(self.config, {
            "optimize": self._hotkey_optimize,
        })

        self.app_state = {
            "config": self.config,
            "running": lambda: self.running,
            "memory_tracker": self.memory_tracker,
            "system_monitor": self.system_monitor,
            "game_mode": self.game_mode,
            "streaming_mode": self.streaming_mode,
            "presentation_mode": self.presentation_mode,
            "benchmark": self.benchmark,
            "scheduler": self.scheduler,
            "theme_manager": self.theme_manager,
            "tk_root": lambda: self.tk_root,
        }

    def _get_lang(self):
        return self.config.get("language", "ru")

    def _hotkey_optimize(self):
        logger.info("Горячая клавиша: оптимизация")
        threading.Thread(target=self.perform_optimization, args=(True,), daemon=True).start()

    def perform_optimization(self, manual=False):
        initial_free = round(psutil.virtual_memory().available / (1024 ** 3), 2)

        files, mb = clean_temp_files(self.config)
        tmp_files, tmp_mb = clean_tmp_folder(self.config)
        files += tmp_files
        mb += tmp_mb

        clean_recycle_bin(self.config)
        clean_browser_cache(self.config)

        sys_results = clean_all_system(self.config)
        for key, val in sys_results.items():
            if isinstance(val, (int, float)):
                mb += val
            elif isinstance(val, dict) and "mb" in val:
                mb += val["mb"]

        minimized = self._minimize_browsers()

        import time
        time.sleep(1)

        final_free = round(psutil.virtual_memory().available / (1024 ** 3), 2)
        freed = round(final_free - initial_free, 2)
        if freed < 0:
            freed = 0

        mb = round(mb, 2)
        record_optimization(freed, files, mb, details=sys_results)

        lang = self._get_lang()
        logger.info(
            f"Оптимизация: RAM {freed} ГБ, файлов {files}, "
            f"кэш {mb} МБ, окон {minimized}"
        )

        if manual or freed > 0.1 or files > 0:
            msg = t(lang, "optimization_notification",
                     freed=freed, cache=mb, wins=minimized)
            if self.icon:
                self.icon.notify(msg, t(lang, "app_name"))

    def _minimize_browsers(self):
        import pygetwindow as gw
        browser_names = self.config.get("browser_names", [])
        minimized_count = 0
        try:
            active_window = gw.getActiveWindow()
            active_title = active_window.title if active_window else ""
            for window in gw.getAllWindows():
                if any(b in window.title for b in browser_names) and window.title != active_title:
                    if not window.isMinimized:
                        window.minimize()
                        minimized_count += 1
        except Exception as e:
            logger.debug(f"Ошибка сворачивания окон: {e}")
        return minimized_count

    def background_loop(self):
        logger.info(t(self._get_lang(), "monitoring_started"))

        while self.running:
            if self.auto_mode:
                ram = psutil.virtual_memory().percent
                self.memory_tracker.record()

                if ram > self.config.get("ram_threshold", 85.0):
                    self.perform_optimization(manual=False)
                    for _ in range(300):
                        if not self.running:
                            return
                        import time
                        time.sleep(1)
                    continue

            interval = self.config.get("check_interval", 30)
            for _ in range(interval):
                if not self.running:
                    return
                import time
                time.sleep(1)

    def _alert_checker_loop(self):
        while self.running:
            try:
                check_alerts(self.system_monitor, self.config)
            except Exception:
                pass
            for _ in range(60):
                if not self.running:
                    return
                import time
                time.sleep(1)

    def update_icon(self):
        if self.icon:
            ram = psutil.virtual_memory().percent
            self.icon.icon = create_image(ram)

    def on_optimize(self, icon, item):
        threading.Thread(target=self.perform_optimization, args=(True,), daemon=True).start()

    def on_auto_mode(self, icon, item):
        self.auto_mode = not self.auto_mode
        self.config["auto_mode"] = self.auto_mode
        save_config(self.config)
        lang = self._get_lang()
        msg = t(lang, "auto_on") if self.auto_mode else t(lang, "auto_off")
        icon.notify(msg, t(lang, "app_name"))
        logger.info(f"Авто-режим: {'вкл' if self.auto_mode else 'выкл'}")

    def on_autostart(self, icon, item):
        current = is_autostart_active()
        new_state = not current
        success = toggle_autostart(new_state)
        self.config["autostart"] = new_state
        save_config(self.config)

        lang = self._get_lang()
        if success:
            msg = t(lang, "autostart_on") if new_state else t(lang, "autostart_off")
            icon.notify(msg, t(lang, "app_name"))
            logger.info(f"Автозапуск: {'вкл' if new_state else 'выкл'}")
        else:
            logger.error("Не удалось изменить автозапуск")

    def on_stats(self, icon, item):
        if not self.tk_root:
            return
        self.tk_root.after(0, self._do_open_stats)

    def _do_open_stats(self):
        try:
            open_ram_graph(self.app_state)
        except Exception as e:
            logger.error(f"Ошибка графика: {e}")

    def on_kill_processes(self, icon, item):
        heavy = get_heavy_processes(self.config)
        lang = self._get_lang()
        if not heavy:
            icon.notify(t(lang, "no_heavy"), t(lang, "processes_title"))
            return
        killed = kill_processes(heavy)
        icon.notify(t(lang, "killed", n=killed), t(lang, "processes_title"))

    def on_open_window(self, icon, item):
        if not self.tk_root:
            return
        self.tk_root.after(0, self._do_open_window)

    def _do_open_window(self):
        if self._main_window_open:
            if self.main_window and self.main_window.root:
                try:
                    self.main_window.root.deiconify()
                    self.main_window.root.lift()
                    self.main_window.root.focus_force()
                except Exception:
                    self._main_window_open = False
            return
        try:
            import tkinter as tk
            self._main_window_open = True
            self.app_state["tk_root"] = self.tk_root
            from ui.main_window import MainWindow
            toplevel = tk.Toplevel(self.tk_root)
            self.main_window = MainWindow(toplevel, self.app_state, self.theme_manager)
            toplevel.protocol("WM_DELETE_WINDOW", self._close_main_window)
            self.main_window._toplevel = toplevel
        except Exception as e:
            logger.error(f"Ошибка главного окна: {e}")
            self._main_window_open = False

    def _close_main_window(self):
        if self.main_window:
            try:
                self.main_window.destroy()
            except Exception:
                pass
        if self.main_window and hasattr(self.main_window, '_toplevel'):
            try:
                self.main_window._toplevel.destroy()
            except Exception:
                pass
        self._main_window_open = False
        self.main_window = None

    def on_game_mode(self, icon, item):
        if self.game_mode.is_active:
            self.game_mode.deactivate()
            lang = self._get_lang()
            icon.notify(t(lang, "game_mode_off"), t(lang, "game_mode"))
        else:
            self.game_mode.activate()
            lang = self._get_lang()
            icon.notify(t(lang, "game_mode_on"), t(lang, "game_mode"))

    def on_streaming_mode(self, icon, item):
        if self.streaming_mode.is_active:
            self.streaming_mode.deactivate()
            lang = self._get_lang()
            icon.notify(t(lang, "streaming_off"), t(lang, "streaming_mode"))
        else:
            self.streaming_mode.activate()
            lang = self._get_lang()
            icon.notify(t(lang, "streaming_on"), t(lang, "streaming_mode"))

    def on_presentation_mode(self, icon, item):
        if self.presentation_mode.is_active:
            self.presentation_mode.deactivate()
            lang = self._get_lang()
            icon.notify(t(lang, "presentation_off"), t(lang, "presentation_mode"))
        else:
            self.presentation_mode.activate()
            lang = self._get_lang()
            icon.notify(t(lang, "presentation_on"), t(lang, "presentation_mode"))

    def on_theme_toggle(self, icon, item):
        self.theme_manager.toggle_theme()
        save_config(self.config)
        lang = self._get_lang()
        theme_name = t(lang, "theme_dark") if self.theme_manager.current_theme_name == "dark" else t(lang, "theme_light")
        icon.notify(f"{t(lang, 'theme')}: {theme_name}", t(lang, "settings"))

    def on_support(self, icon, item):
        import webbrowser
        webbrowser.open("https://www.donationalerts.com/r/zenixx5678")
        logger.info("Открыта ссылка поддержки")

    def on_about(self, icon, item):
        lang = self._get_lang()
        text = t(lang, "about_text", version=t(lang, "version"))
        icon.notify(text, t(lang, "about_title"))

    def on_language_ru(self, icon, item):
        self.config["language"] = "ru"
        save_config(self.config)
        self._rebuild_menu()
        icon.notify(t("ru", "language_changed", lang="Русский"), t("ru", "app_name"))

    def on_language_en(self, icon, item):
        self.config["language"] = "en"
        save_config(self.config)
        self._rebuild_menu()
        icon.notify(t("en", "language_changed", lang="English"), t("en", "app_name"))

    def on_exit(self, icon, item):
        self.running = False
        self.system_monitor.stop()
        self.game_mode.stop_watching()
        self.scheduler.stop()
        self.hotkey_manager.unregister_all()
        if self.tk_root:
            try:
                self.tk_root.after(0, self.tk_root.destroy)
            except Exception:
                pass
        logger.info("Выход из приложения")
        icon.stop()

    def _build_menu(self):
        lang = self._get_lang()

        submenu_help = pystray.Menu(
            pystray.MenuItem(t(lang, "about"), self.on_about),
            pystray.MenuItem(t(lang, "support"), self.on_support),
        )

        submenu_lang = pystray.Menu(
            pystray.MenuItem("Русский", self.on_language_ru),
            pystray.MenuItem("English", self.on_language_en),
        )

        submenu_theme = pystray.Menu(
            pystray.MenuItem(t(lang, "theme_dark"), self.on_theme_toggle,
                           checked=lambda item: self.theme_manager.current_theme_name == "dark"),
            pystray.MenuItem(t(lang, "theme_light"), self.on_theme_toggle,
                           checked=lambda item: self.theme_manager.current_theme_name == "light"),
        )

        submenu_modes = pystray.Menu(
            pystray.MenuItem(
                t(lang, "game_mode"),
                self.on_game_mode,
                checked=lambda item: self.game_mode.is_active
            ),
            pystray.MenuItem(
                t(lang, "streaming_mode"),
                self.on_streaming_mode,
                checked=lambda item: self.streaming_mode.is_active
            ),
            pystray.MenuItem(
                t(lang, "presentation_mode"),
                self.on_presentation_mode,
                checked=lambda item: self.presentation_mode.is_active
            ),
        )

        menu_items = [
            pystray.MenuItem(t(lang, "open_window"), self.on_open_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t(lang, "optimize_now"), self.on_optimize),
            pystray.MenuItem(
                t(lang, "auto_mode"),
                self.on_auto_mode,
                checked=lambda item: self.auto_mode
            ),
            pystray.MenuItem(
                t(lang, "autostart"),
                self.on_autostart,
                checked=lambda item: is_autostart_active()
            ),
            pystray.MenuItem(t(lang, "stats"), self.on_stats),
            pystray.MenuItem(t(lang, "kill_processes"), self.on_kill_processes),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t(lang, "game_mode_tab"), submenu_modes),
            pystray.MenuItem(t(lang, "theme"), submenu_theme),
            pystray.MenuItem(t(lang, "language"), submenu_lang),
            pystray.MenuItem(t(lang, "help_menu"), submenu_help),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t(lang, "exit"), self.on_exit),
        ]

        return pystray.Menu(*menu_items)

    def _rebuild_menu(self):
        if self.icon:
            self.icon.menu = self._build_menu()
            lang = self._get_lang()
            ram = psutil.virtual_memory().percent
            self.icon.title = t(lang, "tray_tooltip", ram=ram)

    def run(self):
        lang = self._get_lang()
        image = create_image(psutil.virtual_memory().percent)
        menu = self._build_menu()

        ram = psutil.virtual_memory().percent
        tooltip = t(lang, "tray_tooltip", ram=ram)

        self.icon = pystray.Icon("SilentOptimizer", image, tooltip, menu)

        threading.Thread(target=self.background_loop, daemon=True).start()
        threading.Thread(target=self._alert_checker_loop, daemon=True).start()

        hib_state = {
            "config": self.config,
            "running": lambda: self.running,
        }
        threading.Thread(
            target=hibernation_monitor,
            args=(hib_state,),
            kwargs={"notify_callback": lambda msg: self.icon.notify(msg, "Hibernate")},
            daemon=True
        ).start()

        self.system_monitor.start()
        self.game_mode.start_watching()
        self.scheduler.start()

        try:
            self.hotkey_manager.register_all()
        except Exception as e:
            logger.debug(f"Ошибка горячих клавиш: {e}")

        def icon_updater():
            import time as _time
            while self.running:
                _time.sleep(10)
                self.update_icon()
                ram = psutil.virtual_memory().percent
                self.icon.title = t(self._get_lang(), "tray_tooltip", ram=ram)

        threading.Thread(target=icon_updater, daemon=True).start()

        self.icon.notify(t(lang, "tray_notification"), t(lang, "app_name"))
        self.icon.run()
        self.running = False

    def run_with_tk(self):
        import tkinter as tk
        import time as _time

        self.tk_root = tk.Tk()
        self.tk_root.withdraw()
        self.tk_root.title("Silent PC Optimizer")
        self.tk_root.geometry("1x1+9999+9999")

        def _start_tray():
            _time.sleep(1)
            self.run()

        threading.Thread(target=_start_tray, daemon=True).start()

        self._tick_count = 0
        def _tick():
            if self.running:
                self._tick_count += 1
                if self._tick_count % 300 == 0:
                    try:
                        import psutil as _ps
                        ram = _ps.virtual_memory().percent
                        self.icon.title = t(self._get_lang(), "tray_tooltip", ram=ram)
                    except Exception:
                        pass
                self.tk_root.after(1000, _tick)
            else:
                try:
                    self.tk_root.destroy()
                except Exception:
                    pass

        self.tk_root.after(1000, _tick)
        self.tk_root.mainloop()
        self.running = False
