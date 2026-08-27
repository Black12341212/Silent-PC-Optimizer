import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import psutil
import time
import threading
from ui.theme import ThemeManager
from ui.dashboard import DashboardWidget, MiniGraph
from ui.i18n import t
from core.system_cleaner import clean_all_system
from core.service_manager import get_all_services, disable_service, enable_service, get_service_info
from core.disk_optimizer import optimize_drive, get_disk_health, get_disk_drives, is_ssd, run_trim, run_defrag
from core.startup_manager import get_startup_programs, disable_startup_program, get_installed_programs, uninstall_program
from core.system_repair import run_sfc_scan, get_system_info
from core.update_manager import get_windows_updates, get_update_settings, block_auto_updates, unblock_auto_updates, set_update_defer
from core.benchmark import Benchmark, format_benchmark_result
from core.security import clean_all_security, run_defender_scan
from core.file_encryptor import encrypt_file, decrypt_file
from core.history import get_history, get_summary
from core.optimizer import clean_recycle_bin
from core.restore_point import create_restore_point
from core.config import save_config, CONFIG_PATH
from core.version import VERSION


class MainWindow:
    def __init__(self, root, app_state, theme_manager):
        self.root = root
        self.app_state = app_state
        self.tm = theme_manager
        self.config = app_state.get("config", {})
        self.memory_tracker = app_state.get("memory_tracker")
        self.system_monitor = app_state.get("system_monitor")
        self.game_mode = app_state.get("game_mode")
        self.streaming_mode = app_state.get("streaming_mode")
        self.presentation_mode = app_state.get("presentation_mode")
        self.benchmark = app_state.get("benchmark")
        self.history = app_state.get("history")
        self.scheduler = app_state.get("scheduler")
        self.on_optimize = app_state.get("on_optimize", lambda: None)
        self.on_refresh = app_state.get("on_refresh", lambda: None)
        self._running = True
        self._monitor_data = {
            "cpu": [],
            "ram": [],
            "disk_read": [],
            "disk_write": [],
            "net_sent": [],
            "net_recv": [],
        }
        self._monitor_max = 60
        self._last_disk = psutil.disk_io_counters()
        self._last_net = psutil.net_io_counters()
        self._last_time = time.time()

        self.root.title(f"Silent PC Optimizer v{VERSION}")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.root.configure(bg=self.tm.get("bg"))

        self._build_ui()
        self._start_refresh()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")
        surface = self.tm.get("surface")
        border = self.tm.get("border")

        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=surface, foreground=fg,
                         padding=[12, 6], font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", accent)],
                  foreground=[("selected", "#ffffff")])
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("TButton", background=accent, foreground="#ffffff",
                         font=("Segoe UI", 10, "bold"), padding=[10, 5])
        style.map("TButton",
                  background=[("active", self.tm.get("accent_hover", accent))],
                  foreground=[("active", "#ffffff")])
        style.configure("Treeview", background=surface, foreground=fg,
                         fieldbackground=surface, font=("Consolas", 9), rowheight=22)
        style.configure("Treeview.Heading", background=accent, foreground="#ffffff",
                         font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", accent)])
        style.configure("TScrollbar", background=surface, troughcolor=bg)
        style.configure("Horizontal.TScale", background=bg, troughcolor=surface)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))

        self.tabs = {}
        tab_names = [
            ("dashboard", "Dashboard"), ("monitoring", "Monitoring"),
            ("optimization", "Optimization"), ("services", "Services"),
            ("startup", "Startup"), ("uninstaller", "Uninstaller"),
            ("system_tools", "System Tools"), ("benchmark", "Benchmark"),
            ("security", "Security"), ("encryption", "Encryption"),
            ("game_mode", "Game Mode"), ("updates", "Updates"),
            ("disks", "Disks"), ("processes", "Processes"),
            ("history", "History"),
            ("settings", "Settings"), ("about", "About"),
        ]
        for key, label in tab_names:
            frame = tk.Frame(self.notebook, bg=bg)
            self.notebook.add(frame, text=f"  {label}  ")
            self.tabs[key] = frame

        self._build_dashboard(self.tabs["dashboard"])
        self._build_monitoring(self.tabs["monitoring"])
        self._build_optimization(self.tabs["optimization"])
        self._build_services(self.tabs["services"])
        self._build_startup(self.tabs["startup"])
        self._build_uninstaller(self.tabs["uninstaller"])
        self._build_system_tools(self.tabs["system_tools"])
        self._build_benchmark(self.tabs["benchmark"])
        self._build_security(self.tabs["security"])
        self._build_encryption(self.tabs["encryption"])
        self._build_game_mode(self.tabs["game_mode"])
        self._build_updates(self.tabs["updates"])
        self._build_disks(self.tabs["disks"])
        self._build_processes(self.tabs["processes"])
        self._build_history(self.tabs["history"])
        self._build_settings(self.tabs["settings"])
        self._build_about(self.tabs["about"])

        self.status_bar = tk.Frame(self.root, bg=surface, height=28)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)
        self.status_label = tk.Label(self.status_bar, text="Initializing...",
                                      bg=surface, fg=fg, font=("Consolas", 9))
        self.status_label.pack(side=tk.LEFT, padx=10)
        self.status_right = tk.Label(self.status_bar, text="",
                                      bg=surface, fg=fg, font=("Consolas", 9))
        self.status_right.pack(side=tk.RIGHT, padx=10)

    # ───────────────────────────────────────────────────────────────────
    # Dashboard
    # ───────────────────────────────────────────────────────────────────
    def _build_dashboard(self, parent):
        container = tk.Frame(parent, bg=self.tm.get("bg"))
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        try:
            cpu_val = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")
            net = psutil.net_io_counters()

            self.cpu_widget = DashboardWidget(container, self.tm)
            self.cpu_widget.set_title("CPU")
            self.cpu_widget.add_bar("usage", "Usage")
            self.cpu_widget.add_metric("cores", "Cores")
            self.cpu_widget.add_metric("temp", "Temperature")
            self.cpu_widget.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

            self.ram_widget = DashboardWidget(container, self.tm)
            self.ram_widget.set_title("RAM")
            self.ram_widget.add_bar("usage", "Usage")
            self.ram_widget.add_metric("used", "Used / Total")
            self.ram_widget.add_metric("free", "Free")
            self.ram_widget.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

            self.disk_widget = DashboardWidget(container, self.tm)
            self.disk_widget.set_title("Disk C:")
            self.disk_widget.add_bar("usage", "Usage")
            self.disk_widget.add_metric("space", "Used / Total")
            self.disk_widget.add_metric("free", "Free")
            self.disk_widget.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

            self.net_widget = DashboardWidget(container, self.tm)
            self.net_widget.set_title("Network")
            self.net_widget.add_metric("sent", "Total Sent")
            self.net_widget.add_metric("recv", "Total Recv")
            self.net_widget.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        except Exception as e:
            from core.logger import logger
            logger.debug(f"Dashboard build error: {e}")
            self.cpu_widget = tk.Label(container, text="CPU", bg=self.tm.get("bg_secondary"),
                                       fg=self.tm.get("fg"), font=("Segoe UI", 14))
            self.cpu_widget.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
            self.ram_widget = tk.Label(container, text="RAM", bg=self.tm.get("bg_secondary"),
                                       fg=self.tm.get("fg"), font=("Segoe UI", 14))
            self.ram_widget.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
            self.disk_widget = tk.Label(container, text="Disk", bg=self.tm.get("bg_secondary"),
                                        fg=self.tm.get("fg"), font=("Segoe UI", 14))
            self.disk_widget.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
            self.net_widget = tk.Label(container, text="Network", bg=self.tm.get("bg_secondary"),
                                       fg=self.tm.get("fg"), font=("Segoe UI", 14))
            self.net_widget.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        self.cpu_mini = MiniGraph(container, self.tm, width=200, height=60)
        self.cpu_mini.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        self.ram_mini = MiniGraph(container, self.tm, width=200, height=60)
        self.ram_mini.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        container.rowconfigure(2, weight=0)

    # ───────────────────────────────────────────────────────────────────
    # Monitoring
    # ───────────────────────────────────────────────────────────────────
    def _build_monitoring(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.mon_cpu_canvas = tk.Canvas(container, bg=self.tm.get("surface"),
                                         highlightthickness=1,
                                         highlightbackground=self.tm.get("border"))
        self.mon_cpu_canvas.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.mon_ram_canvas = tk.Canvas(container, bg=self.tm.get("surface"),
                                         highlightthickness=1,
                                         highlightbackground=self.tm.get("border"))
        self.mon_ram_canvas.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.mon_disk_canvas = tk.Canvas(container, bg=self.tm.get("surface"),
                                          highlightthickness=1,
                                          highlightbackground=self.tm.get("border"))
        self.mon_disk_canvas.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.mon_net_canvas = tk.Canvas(container, bg=self.tm.get("surface"),
                                         highlightthickness=1,
                                         highlightbackground=self.tm.get("border"))
        self.mon_net_canvas.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        for c in self.mon_cpu_canvas, self.mon_ram_canvas, self.mon_disk_canvas, self.mon_net_canvas:
            c.create_text(0, 0, text="", tags="label", fill=fg, font=("Segoe UI", 9, "bold"),
                          anchor="nw")

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        self._chart_labels = {
            "cpu": self.mon_cpu_canvas,
            "ram": self.mon_ram_canvas,
            "disk": self.mon_disk_canvas,
            "net": self.mon_net_canvas,
        }

    def _draw_chart(self, canvas, data, title, color, max_val=100):
        canvas.update_idletasks()
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            return
        canvas.delete("chart")
        bg = self.tm.get("surface")
        border = self.tm.get("border")
        canvas.configure(bg=bg, highlightbackground=border)

        canvas.create_text(8, 8, text=title, tags="chart", fill=self.tm.get("fg"),
                           font=("Segoe UI", 10, "bold"), anchor="nw")

        chart_top = 28
        chart_bottom = h - 10
        chart_left = 40
        chart_right = w - 10
        chart_w = chart_right - chart_left
        chart_h = chart_bottom - chart_top

        for i in range(5):
            y = chart_top + chart_h * i / 4
            canvas.create_line(chart_left, y, chart_right, y,
                               fill=border, dash=(2, 4), tags="chart")
            val = int(max_val * (4 - i) / 4)
            canvas.create_text(chart_left - 5, y, text=f"{val}", tags="chart",
                               fill=self.tm.get("fg"), font=("Consolas", 8), anchor="e")

        if len(data) < 2:
            return
        step = chart_w / (self._monitor_max - 1) if self._monitor_max > 1 else chart_w
        points = []
        for i, val in enumerate(data[-self._monitor_max:]):
            x = chart_left + i * step
            clamped = max(0, min(val, max_val))
            y = chart_bottom - (clamped / max_val) * chart_h if max_val > 0 else chart_bottom
            points.append((x, y))

        flat = []
        for p in points:
            flat.extend(p)
        if len(flat) >= 4:
            canvas.create_line(*flat, fill=color, width=2, smooth=True, tags="chart")
            fill_pts = list(flat)
            fill_pts.append(points[-1][0])
            fill_pts.append(chart_bottom)
            fill_pts.append(points[0][0])
            fill_pts.append(chart_bottom)
            canvas.create_polygon(*fill_pts, fill=color, stipple="gray25",
                                  outline="", tags="chart")

    # ───────────────────────────────────────────────────────────────────
    # Optimization
    # ───────────────────────────────────────────────────────────────────
    def _build_optimization(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(container, bg=bg)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        result_frame = tk.Frame(container, bg=bg)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.opt_result = tk.Text(result_frame, bg=self.tm.get("surface"), fg=fg,
                                   font=("Consolas", 9), wrap=tk.WORD,
                                   insertbackground=fg, relief=tk.FLAT,
                                   highlightthickness=1,
                                   highlightbackground=self.tm.get("border"))
        self.opt_result.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.opt_result, command=self.opt_result.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.opt_result.configure(yscrollcommand=scrollbar.set)

        buttons = [
            ("Clean Temp Files", lambda: self._run_opt("clean_temp", self._clean_temp)),
            ("Clean DNS Cache", lambda: self._run_opt("clean_dns", self._clean_dns)),
            ("Clean Prefetch", lambda: self._run_opt("clean_prefetch", self._clean_prefetch)),
            ("Clean Thumbnail Cache", lambda: self._run_opt("clean_thumb", self._clean_thumb)),
            ("Clean Font Cache", lambda: self._run_opt("clean_font", self._clean_font)),
            ("Clean WinUpdate Cache", lambda: self._run_opt("clean_winupdate", self._clean_winupdate)),
            ("Clean Recycle Bin", lambda: self._run_opt("clean_recycle", self._clean_recycle)),
            ("Clean Browser Cache", lambda: self._run_opt("clean_browser", self._clean_browser)),
            ("Clean All System", lambda: self._run_opt("clean_all", self._clean_all)),
            ("Disable Services", lambda: self._run_opt("disable_svc", self._disable_services)),
            ("Optimize Disk", lambda: self._run_opt("optimize_disk", self._optimize_disk)),
            ("Create Restore Point", lambda: self._run_opt("restore_point", self._create_restore_point)),
        ]

        for i, (label, cmd) in enumerate(buttons):
            btn = tk.Button(btn_frame, text=label, command=cmd,
                            bg=accent, fg="#ffffff", activebackground=self.tm.get("accent_hover", accent),
                            activeforeground="#ffffff", font=("Segoe UI", 9, "bold"),
                            relief=tk.FLAT, padx=10, pady=4, cursor="hand2")
            btn.grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="ew")

        for c in range(4):
            btn_frame.columnconfigure(c, weight=1)

    def _append_opt(self, text):
        self.opt_result.after(0, lambda: (
            self.opt_result.insert(tk.END, text + "\n"),
            self.opt_result.see(tk.END),
        ))

    def _run_opt(self, name, func):
        self._append_opt(f"--- Starting: {name} ---")
        threading.Thread(target=func, daemon=True).start()

    def _clean_temp(self):
        try:
            res = clean_all_system(self.config)
            self._append_opt(f"Temp clean: {res}")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _clean_dns(self):
        try:
            import subprocess
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
            self._append_opt("DNS cache flushed.")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _clean_prefetch(self):
        try:
            import os, glob
            count = 0
            for f in glob.glob(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Prefetch", "*.*")):
                try:
                    os.remove(f)
                    count += 1
                except Exception:
                    pass
            self._append_opt(f"Prefetch cleaned: {count} files removed.")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _clean_thumb(self):
        try:
            import os, glob
            thumb_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Explorer")
            count = 0
            for f in glob.glob(os.path.join(thumb_dir, "thumbcache_*.db")):
                try:
                    os.remove(f)
                    count += 1
                except Exception:
                    pass
            self._append_opt(f"Thumbnail cache cleaned: {count} files removed.")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _clean_font(self):
        try:
            import os, glob, subprocess
            count = 0
            cache_dir = os.path.join(
                os.environ.get("SYSTEMROOT", "C:\\Windows"),
                "ServiceProfiles", "LocalService", "AppData", "Local", "FontCache"
            )
            if os.path.exists(cache_dir):
                for f in glob.glob(os.path.join(cache_dir, "*.dat")):
                    try:
                        os.remove(f)
                        count += 1
                    except Exception:
                        pass
            subprocess.run(["net", "stop", "FontCache"], capture_output=True, timeout=15)
            subprocess.run(["net", "start", "FontCache"], capture_output=True, timeout=15)
            self._append_opt(f"Font cache cleaned: {count} cache files removed.")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _clean_winupdate(self):
        try:
            import os, shutil
            wu_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "SoftwareDistribution", "Download")
            count = 0
            for item in os.listdir(wu_dir):
                p = os.path.join(wu_dir, item)
                try:
                    if os.path.isfile(p):
                        os.remove(p)
                        count += 1
                    elif os.path.isdir(p):
                        shutil.rmtree(p)
                        count += 1
                except Exception:
                    pass
            self._append_opt(f"Windows Update cache cleaned: {count} items removed.")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _clean_recycle(self):
        try:
            ok = clean_recycle_bin(self.config)
            if ok:
                self._append_opt("Recycle bin cleaned.")
            else:
                self._append_opt("Recycle bin not cleaned (disabled in settings or no permission).")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _clean_browser(self):
        try:
            import os, glob, shutil
            count = 0
            local = os.environ.get("LOCALAPPDATA", "")
            patterns = [
                os.path.join(local, "Google", "Chrome", "User Data", "Default", "Cache", "*"),
                os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Cache", "*"),
                os.path.join(local, "Mozilla", "Firefox", "Profiles", "*", "cache2", "*"),
            ]
            for pat in patterns:
                for f in glob.glob(pat):
                    try:
                        if os.path.isfile(f):
                            os.remove(f)
                            count += 1
                        elif os.path.isdir(f):
                            shutil.rmtree(f, ignore_errors=True)
                            count += 1
                    except Exception:
                        pass
            self._append_opt(f"Browser cache cleaned: {count} items removed.")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _clean_all(self):
        try:
            res = clean_all_system(self.config)
            self._append_opt(f"Full system clean result: {res}")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _disable_services(self):
        try:
            svcs = self.config.get("service_management", {}).get("disable_list", [])
            disabled = 0
            for svc in svcs:
                try:
                    disable_service(svc)
                    disabled += 1
                    self._append_opt(f"Disabled service: {svc}")
                except Exception as e:
                    self._append_opt(f"Failed to disable {svc}: {e}")
            self._append_opt(f"Services disabled: {disabled}/{len(svcs)}")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _optimize_disk(self):
        try:
            result = optimize_drive(self.config)
            self._append_opt(f"Disk optimization result: SSD={result.get('is_ssd', '?')}")
            if result.get("health"):
                for h in result["health"]:
                    self._append_opt(f"  Disk {h.get('name','?')}: health={h.get('health','?')}, type={h.get('type','?')}")
            if result.get("trim"):
                self._append_opt(f"  TRIM: {'OK' if result['trim'].get('success') else 'Failed'}")
            if result.get("defrag"):
                self._append_opt(f"  Defrag: {'OK' if result['defrag'].get('success') else 'Failed'}")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    def _create_restore_point(self):
        try:
            ok = create_restore_point()
            self._append_opt("Restore point created." if ok else "Restore point failed.")
        except Exception as e:
            self._append_opt(f"Error: {e}")

    # ───────────────────────────────────────────────────────────────────
    # Services
    # ───────────────────────────────────────────────────────────────────
    def _build_services(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        tk.Label(toolbar, text="Filter:", bg=bg, fg=fg,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.svc_filter_var = tk.StringVar(value="all")
        for val, label in [("all", "All"), ("running", "Running"), ("stopped", "Stopped")]:
            rb = tk.Radiobutton(toolbar, text=label, variable=self.svc_filter_var,
                                value=val, bg=bg, fg=fg, selectcolor=self.tm.get("surface"),
                                activebackground=bg, activeforeground=fg,
                                command=self._refresh_services)
            rb.pack(side=tk.LEFT, padx=5)

        btn_refresh = tk.Button(toolbar, text="Refresh", command=self._refresh_services,
                                bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=8, cursor="hand2")
        btn_refresh.pack(side=tk.RIGHT, padx=2)

        btn_disable = tk.Button(toolbar, text="Disable", command=self._svc_disable,
                                bg="#e74c3c", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=8, cursor="hand2")
        btn_disable.pack(side=tk.RIGHT, padx=2)

        btn_enable = tk.Button(toolbar, text="Enable", command=self._svc_enable,
                               bg="#27ae60", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                               relief=tk.FLAT, padx=8, cursor="hand2")
        btn_enable.pack(side=tk.RIGHT, padx=2)

        tree_frame = tk.Frame(container, bg=bg)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "display_name", "status", "start_type")
        self.svc_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                      selectmode="browse")
        self.svc_tree.heading("name", text="Service Name")
        self.svc_tree.heading("display_name", text="Display Name")
        self.svc_tree.heading("status", text="Status")
        self.svc_tree.heading("start_type", text="Start Type")
        self.svc_tree.column("name", width=200)
        self.svc_tree.column("display_name", width=250)
        self.svc_tree.column("status", width=80)
        self.svc_tree.column("start_type", width=100)

        svc_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.svc_tree.yview)
        self.svc_tree.configure(yscrollcommand=svc_scroll.set)
        self.svc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        svc_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.svc_tree.tag_configure("running", foreground="#27ae60")
        self.svc_tree.tag_configure("stopped", foreground="#e74c3c")

        self._refresh_services()

    def _refresh_services(self):
        try:
            f = self.svc_filter_var.get()
            services = get_all_services()
            if f != "all":
                services = [s for s in services if s.get("status", "").lower() == f]
            self.svc_tree.delete(*self.svc_tree.get_children())
            for svc in services:
                name = svc.get("name", "")
                display = svc.get("display_name", "")
                status = svc.get("status", "")
                start = svc.get("start_type", "")
                tag = "running" if status.lower() == "running" else "stopped"
                self.svc_tree.insert("", tk.END, values=(name, display, status, start),
                                     tags=(tag,))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load services: {e}")

    def _svc_disable(self):
        sel = self.svc_tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a service first.")
            return
        name = self.svc_tree.item(sel[0])["values"][0]
        try:
            disable_service(name)
            messagebox.showinfo("Success", f"Service '{name}' disabled.")
            self._refresh_services()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disable: {e}")

    def _svc_enable(self):
        sel = self.svc_tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a service first.")
            return
        name = self.svc_tree.item(sel[0])["values"][0]
        try:
            enable_service(name)
            messagebox.showinfo("Success", f"Service '{name}' enabled.")
            self._refresh_services()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable: {e}")

    # ───────────────────────────────────────────────────────────────────
    # Startup
    # ───────────────────────────────────────────────────────────────────
    def _build_startup(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        btn_refresh = tk.Button(toolbar, text="Refresh", command=self._refresh_startup,
                                bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=8, cursor="hand2")
        btn_refresh.pack(side=tk.RIGHT, padx=2)

        btn_disable = tk.Button(toolbar, text="Disable Selected", command=self._startup_disable,
                                bg="#e74c3c", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=8, cursor="hand2")
        btn_disable.pack(side=tk.RIGHT, padx=2)

        tree_frame = tk.Frame(container, bg=bg)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "command", "location")
        self.startup_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                          selectmode="browse")
        self.startup_tree.heading("name", text="Program Name")
        self.startup_tree.heading("command", text="Path")
        self.startup_tree.heading("location", text="Source")
        self.startup_tree.column("name", width=200)
        self.startup_tree.column("command", width=400)
        self.startup_tree.column("location", width=200)

        startup_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                        command=self.startup_tree.yview)
        self.startup_tree.configure(yscrollcommand=startup_scroll.set)
        self.startup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        startup_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_startup()

    def _refresh_startup(self):
        try:
            programs = get_startup_programs()
            self.startup_tree.delete(*self.startup_tree.get_children())
            for prog in programs:
                name = prog.get("name", "")
                path = prog.get("path", "")
                source = prog.get("source", "")
                self.startup_tree.insert("", tk.END, values=(name, path, source))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load startup programs: {e}")

    def _startup_disable(self):
        sel = self.startup_tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a startup program first.")
            return
        values = self.startup_tree.item(sel[0])["values"]
        name = values[0]
        path = values[1] if len(values) > 1 else ""
        try:
            program = {"name": name, "path": path, "type": "file"}
            disable_startup_program(program)
            messagebox.showinfo("Success", f"Startup program '{name}' disabled.")
            self._refresh_startup()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disable: {e}")

    # ───────────────────────────────────────────────────────────────────
    # Uninstaller
    # ───────────────────────────────────────────────────────────────────
    def _build_uninstaller(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        tk.Label(toolbar, text="Search:", bg=bg, fg=fg,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.uninst_search_var = tk.StringVar()
        self.uninst_search_var.trace_add("write", lambda *_: self._filter_uninstaller())
        search_entry = tk.Entry(toolbar, textvariable=self.uninst_search_var, width=30,
                                bg=self.tm.get("surface"), fg=fg, insertbackground=fg,
                                font=("Segoe UI", 10), relief=tk.FLAT,
                                highlightthickness=1,
                                highlightbackground=self.tm.get("border"))
        search_entry.pack(side=tk.LEFT, padx=5)

        btn_refresh = tk.Button(toolbar, text="Refresh", command=self._refresh_uninstaller,
                                bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=8, cursor="hand2")
        btn_refresh.pack(side=tk.RIGHT, padx=2)

        btn_uninstall = tk.Button(toolbar, text="Uninstall", command=self._uninstall_selected,
                                  bg="#e74c3c", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                  relief=tk.FLAT, padx=8, cursor="hand2")
        btn_uninstall.pack(side=tk.RIGHT, padx=2)

        tree_frame = tk.Frame(container, bg=bg)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "version", "publisher", "size")
        self.uninst_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                         selectmode="browse")
        self.uninst_tree.heading("name", text="Program Name")
        self.uninst_tree.heading("version", text="Version")
        self.uninst_tree.heading("publisher", text="Publisher")
        self.uninst_tree.heading("size", text="Size")
        self.uninst_tree.column("name", width=250)
        self.uninst_tree.column("version", width=100)
        self.uninst_tree.column("publisher", width=200)
        self.uninst_tree.column("size", width=100)

        uninst_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                       command=self.uninst_tree.yview)
        self.uninst_tree.configure(yscrollcommand=uninst_scroll.set)
        self.uninst_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        uninst_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._all_installed = []
        self._refresh_uninstaller()

    def _refresh_uninstaller(self):
        try:
            self._all_installed = get_installed_programs()
            self._filter_uninstaller()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load programs: {e}")

    def _filter_uninstaller(self):
        query = self.uninst_search_var.get().lower() if hasattr(self, "uninst_search_var") else ""
        self.uninst_tree.delete(*self.uninst_tree.get_children())
        for prog in self._all_installed:
            name = prog.get("name", "")
            if query and query not in name.lower():
                continue
            version = prog.get("version", "")
            publisher = prog.get("publisher", "")
            size = f"{prog.get('size_mb', 'N/A')} MB"
            self.uninst_tree.insert("", tk.END, values=(name, version, publisher, size))

    def _uninstall_selected(self):
        sel = self.uninst_tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a program first.")
            return
        name = self.uninst_tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Confirm", f"Uninstall '{name}'?"):
            return
        try:
            success, output = uninstall_program(name)
            if success:
                messagebox.showinfo("Success", f"Uninstall initiated for '{name}'.")
            else:
                messagebox.showinfo("Info", f"Uninstall command sent for '{name}'.")
            self._refresh_uninstaller()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to uninstall: {e}")

    # ───────────────────────────────────────────────────────────────────
    # System Tools
    # ───────────────────────────────────────────────────────────────────
    def _build_system_tools(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        btn_sfc = tk.Button(toolbar, text="Run SFC Scan", command=self._run_sfc,
                            bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                            relief=tk.FLAT, padx=10, cursor="hand2")
        btn_sfc.pack(side=tk.LEFT, padx=2)

        btn_sysinfo = tk.Button(toolbar, text="System Info", command=self._show_sysinfo,
                                bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=10, cursor="hand2")
        btn_sysinfo.pack(side=tk.LEFT, padx=2)

        btn_updates = tk.Button(toolbar, text="Check Updates", command=self._check_updates,
                                bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=10, cursor="hand2")
        btn_updates.pack(side=tk.LEFT, padx=2)

        result_frame = tk.Frame(container, bg=bg)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.sys_result = tk.Text(result_frame, bg=self.tm.get("surface"), fg=fg,
                                   font=("Consolas", 9), wrap=tk.WORD,
                                   insertbackground=fg, relief=tk.FLAT,
                                   highlightthickness=1,
                                   highlightbackground=self.tm.get("border"))
        self.sys_result.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(self.sys_result, command=self.sys_result.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.sys_result.configure(yscrollcommand=scroll.set)

    def _append_sys(self, text):
        self.sys_result.after(0, lambda: (
            self.sys_result.insert(tk.END, text + "\n"),
            self.sys_result.see(tk.END),
        ))

    def _run_sfc(self):
        self.sys_result.delete("1.0", tk.END)
        self._append_sys("--- Running SFC Scan ---")
        threading.Thread(target=self._sfc_thread, daemon=True).start()

    def _sfc_thread(self):
        try:
            result = run_sfc_scan()
            self._append_sys(str(result))
        except Exception as e:
            self._append_sys(f"Error: {e}")

    def _show_sysinfo(self):
        self.sys_result.delete("1.0", tk.END)
        try:
            info = get_system_info()
            if isinstance(info, dict):
                for k, v in info.items():
                    self._append_sys(f"{k}: {v}")
            else:
                self._append_sys(str(info))
        except Exception as e:
            self._append_sys(f"Error: {e}")

    def _check_updates(self):
        self.sys_result.delete("1.0", tk.END)
        self._append_sys("--- Checking Windows Updates ---")
        threading.Thread(target=self._updates_thread, daemon=True).start()

    def _updates_thread(self):
        try:
            updates = get_windows_updates()
            if isinstance(updates, list):
                for u in updates:
                    if isinstance(u, dict):
                        self._append_sys(
                            f"- {u.get('description', 'N/A')} ({u.get('id', 'N/A')}) - {u.get('date', 'N/A')}"
                        )
                    else:
                        self._append_sys(f"- {u}")
            else:
                self._append_sys(str(updates))
            settings = get_update_settings()
            self._append_sys(f"\nUpdate settings: {settings}")
        except Exception as e:
            self._append_sys(f"Error: {e}")

    # ───────────────────────────────────────────────────────────────────
    # Benchmark
    # ───────────────────────────────────────────────────────────────────
    def _build_benchmark(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        info_label = tk.Label(container,
                              text="Run a system benchmark to test CPU, RAM, and Disk performance.",
                              bg=bg, fg=fg, font=("Segoe UI", 11))
        info_label.pack(pady=(0, 10))

        btn_frame = tk.Frame(container, bg=bg)
        btn_frame.pack(pady=(0, 10))

        self.bench_btn = tk.Button(btn_frame, text="Start Benchmark", command=self._run_benchmark,
                                   bg=accent, fg="#ffffff", font=("Segoe UI", 11, "bold"),
                                   relief=tk.FLAT, padx=20, pady=8, cursor="hand2")
        self.bench_btn.pack()

        self.bench_status = tk.Label(btn_frame, text="", bg=bg, fg=fg,
                                      font=("Segoe UI", 10))
        self.bench_status.pack(pady=5)

        self.bench_progress = ttk.Progressbar(container, mode="indeterminate", length=300)

        result_frame = tk.Frame(container, bg=bg)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.bench_result = tk.Text(result_frame, bg=self.tm.get("surface"), fg=fg,
                                     font=("Consolas", 10), wrap=tk.WORD,
                                     insertbackground=fg, relief=tk.FLAT,
                                     highlightthickness=1,
                                     highlightbackground=self.tm.get("border"))
        self.bench_result.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(self.bench_result, command=self.bench_result.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.bench_result.configure(yscrollcommand=scroll.set)

    def _run_benchmark(self):
        self.bench_btn.configure(state=tk.DISABLED)
        self.bench_status.configure(text="Benchmarking... please wait.")
        self.bench_progress.pack(pady=5)
        self.bench_progress.start(10)
        threading.Thread(target=self._benchmark_thread, daemon=True).start()

    def _benchmark_thread(self):
        try:
            bench = Benchmark() if self.benchmark is None else self.benchmark
            result = bench.run_full_benchmark()
            formatted = format_benchmark_result(result)
            self.bench_result.after(0, lambda: (
                self.bench_result.delete("1.0", tk.END),
                self.bench_result.insert(tk.END, formatted),
            ))
            self.bench_status.after(0, lambda: self.bench_status.configure(text="Benchmark complete!"))
        except Exception as e:
            self.bench_status.after(0, lambda: self.bench_status.configure(text=f"Error: {e}"))
        finally:
            self.bench_progress.after(0, self.bench_progress.stop)
            self.bench_progress.after(0, self.bench_progress.pack_forget)
            self.bench_btn.after(0, lambda: self.bench_btn.configure(state=tk.NORMAL))

    # ───────────────────────────────────────────────────────────────────
    # Security
    # ───────────────────────────────────────────────────────────────────
    def _build_security(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        btn_clean = tk.Button(toolbar, text="Clean All Security Traces",
                              command=self._security_clean,
                              bg="#e67e22", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                              relief=tk.FLAT, padx=10, cursor="hand2")
        btn_clean.pack(side=tk.LEFT, padx=2)

        btn_defender = tk.Button(toolbar, text="Run Defender Scan",
                                 command=self._security_defender,
                                 bg="#e74c3c", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                 relief=tk.FLAT, padx=10, cursor="hand2")
        btn_defender.pack(side=tk.LEFT, padx=2)

        result_frame = tk.Frame(container, bg=bg)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.sec_result = tk.Text(result_frame, bg=self.tm.get("surface"), fg=fg,
                                   font=("Consolas", 9), wrap=tk.WORD,
                                   insertbackground=fg, relief=tk.FLAT,
                                   highlightthickness=1,
                                   highlightbackground=self.tm.get("border"))
        self.sec_result.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(self.sec_result, command=self.sec_result.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.sec_result.configure(yscrollcommand=scroll.set)

    def _append_sec(self, text):
        self.sec_result.after(0, lambda: (
            self.sec_result.insert(tk.END, text + "\n"),
            self.sec_result.see(tk.END),
        ))

    def _security_clean(self):
        self.sec_result.delete("1.0", tk.END)
        self._append_sec("--- Cleaning security traces ---")
        threading.Thread(target=self._sec_clean_thread, daemon=True).start()

    def _sec_clean_thread(self):
        try:
            result = clean_all_security(self.config)
            self._append_sec(str(result))
            sec_cfg = self.config.get("security", {})
            if sec_cfg.get("auto_defender_scan", False):
                self._append_sec("--- Running Windows Defender Scan ---")
                scan = run_defender_scan()
                self._append_sec(str(scan))
        except Exception as e:
            self._append_sec(f"Error: {e}")

    def _security_defender(self):
        self.sec_result.delete("1.0", tk.END)
        self._append_sec("--- Running Windows Defender Scan ---")
        threading.Thread(target=self._sec_defender_thread, daemon=True).start()

    def _sec_defender_thread(self):
        try:
            result = run_defender_scan()
            self._append_sec(str(result))
        except Exception as e:
            self._append_sec(f"Error: {e}")

    # ───────────────────────────────────────────────────────────────────
    # Encryption
    # ───────────────────────────────────────────────────────────────────
    def _build_encryption(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_frame = tk.Frame(container, bg=bg)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(top_frame, text="File:", bg=bg, fg=fg,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.enc_file_var = tk.StringVar()
        file_entry = tk.Entry(top_frame, textvariable=self.enc_file_var, width=50,
                              bg=self.tm.get("surface"), fg=fg, insertbackground=fg,
                              font=("Segoe UI", 10), relief=tk.FLAT,
                              highlightthickness=1,
                              highlightbackground=self.tm.get("border"))
        file_entry.pack(side=tk.LEFT, padx=5)

        btn_browse = tk.Button(top_frame, text="Browse", command=self._enc_browse,
                                bg=self.tm.get("surface"), fg=fg, font=("Segoe UI", 9),
                                relief=tk.FLAT, padx=8, cursor="hand2")
        btn_browse.pack(side=tk.LEFT, padx=2)

        tk.Label(top_frame, text="Password:", bg=bg, fg=fg,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(15, 5))
        self.enc_pass_var = tk.StringVar()
        pass_entry = tk.Entry(top_frame, textvariable=self.enc_pass_var, width=25,
                              show="*", bg=self.tm.get("surface"), fg=fg, insertbackground=fg,
                              font=("Segoe UI", 10), relief=tk.FLAT,
                              highlightthickness=1,
                              highlightbackground=self.tm.get("border"))
        pass_entry.pack(side=tk.LEFT, padx=5)

        btn_frame = tk.Frame(container, bg=bg)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        btn_encrypt = tk.Button(btn_frame, text="Encrypt File", command=self._enc_encrypt,
                                bg="#27ae60", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=15, cursor="hand2")
        btn_encrypt.pack(side=tk.LEFT, padx=5)

        btn_decrypt = tk.Button(btn_frame, text="Decrypt File", command=self._enc_decrypt,
                                bg="#2980b9", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=15, cursor="hand2")
        btn_decrypt.pack(side=tk.LEFT, padx=5)

        result_frame = tk.Frame(container, bg=bg)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.enc_result = tk.Text(result_frame, bg=self.tm.get("surface"), fg=fg,
                                   font=("Consolas", 9), wrap=tk.WORD,
                                   insertbackground=fg, relief=tk.FLAT,
                                   highlightthickness=1,
                                   highlightbackground=self.tm.get("border"))
        self.enc_result.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(self.enc_result, command=self.enc_result.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.enc_result.configure(yscrollcommand=scroll.set)

    def _enc_browse(self):
        path = filedialog.askopenfilename(title="Select file")
        if path:
            self.enc_file_var.set(path)

    def _enc_encrypt(self):
        path = self.enc_file_var.get()
        password = self.enc_pass_var.get()
        if not path or not password:
            messagebox.showwarning("Warning", "Select a file and enter a password.")
            return
        threading.Thread(target=self._enc_thread, args=("encrypt", path, password),
                         daemon=True).start()

    def _enc_decrypt(self):
        path = self.enc_file_var.get()
        password = self.enc_pass_var.get()
        if not path or not password:
            messagebox.showwarning("Warning", "Select a file and enter a password.")
            return
        threading.Thread(target=self._enc_thread, args=("decrypt", path, password),
                         daemon=True).start()

    def _enc_thread(self, action, path, password):
        try:
            if action == "encrypt":
                result = encrypt_file(path, password)
            else:
                result = decrypt_file(path, password)
            self.enc_result.after(0, lambda: (
                self.enc_result.insert(tk.END, f"{action.capitalize()} result: {result}\n"),
                self.enc_result.see(tk.END),
            ))
        except Exception as e:
            self.enc_result.after(0, lambda: (
                self.enc_result.insert(tk.END, f"Error: {e}\n"),
                self.enc_result.see(tk.END),
            ))

    # ───────────────────────────────────────────────────────────────────
    # Game Mode
    # ───────────────────────────────────────────────────────────────────
    def _build_game_mode(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title = tk.Label(container, text="Game & Presentation Mode",
                         bg=bg, fg=fg, font=("Segoe UI", 16, "bold"))
        title.pack(pady=(10, 20))

        modes = [
            ("Game Mode", "game_mode", "Optimizes system for gaming performance.", "#e74c3c"),
            ("Streaming Mode", "streaming_mode", "Optimizes for streaming with low overhead.", "#9b59b6"),
            ("Presentation Mode", "presentation_mode", "Optimizes for presentations, disables sleep.", "#3498db"),
        ]

        self.mode_vars = {}
        for label, key, desc, color in modes:
            frame = tk.Frame(container, bg=self.tm.get("surface"), padx=15, pady=12,
                             highlightthickness=1, highlightbackground=self.tm.get("border"))
            frame.pack(fill=tk.X, padx=20, pady=6)

            left = tk.Frame(frame, bg=self.tm.get("surface"))
            left.pack(side=tk.LEFT, fill=tk.X, expand=True)

            tk.Label(left, text=label, bg=self.tm.get("surface"), fg=fg,
                     font=("Segoe UI", 13, "bold")).pack(anchor="w")
            tk.Label(left, text=desc, bg=self.tm.get("surface"),
                     fg=self.tm.get("fg_dim", fg),
                     font=("Segoe UI", 9)).pack(anchor="w")

            var = tk.BooleanVar(value=False)
            self.mode_vars[key] = var
            toggle = tk.Checkbutton(frame, variable=var,
                                     command=lambda k=key: self._toggle_mode(k),
                                     bg=self.tm.get("surface"), fg=fg,
                                     selectcolor=color,
                                     activebackground=self.tm.get("surface"),
                                     activeforeground=fg,
                                     font=("Segoe UI", 11))
            toggle.pack(side=tk.RIGHT)

    def _toggle_mode(self, key):
        val = self.mode_vars[key].get()
        mode_obj = None
        if key == "game_mode":
            mode_obj = self.game_mode
        elif key == "streaming_mode":
            mode_obj = self.streaming_mode
        elif key == "presentation_mode":
            mode_obj = self.presentation_mode

        if mode_obj is None:
            return

        try:
            if val:
                mode_obj.activate()
            else:
                mode_obj.deactivate()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle {key}: {e}")

    # ───────────────────────────────────────────────────────────────────
    # Updates
    # ───────────────────────────────────────────────────────────────────
    def _build_updates(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        tk.Button(toolbar, text="Check Updates", command=self._updates_refresh,
                  bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Block Auto Updates", command=lambda: self._updates_action(block_auto_updates),
                  bg="#e74c3c", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Unblock Auto Updates", command=lambda: self._updates_action(unblock_auto_updates),
                  bg="#27ae60", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Defer 7 Days", command=lambda: self._updates_action(lambda: set_update_defer(7)),
                  bg="#f39c12", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=2)

        result_frame = tk.Frame(container, bg=bg)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.updates_result = tk.Text(result_frame, bg=self.tm.get("surface"), fg=fg,
                                      font=("Consolas", 9), wrap=tk.WORD,
                                      insertbackground=fg, relief=tk.FLAT,
                                      highlightthickness=1,
                                      highlightbackground=self.tm.get("border"))
        self.updates_result.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(self.updates_result, command=self.updates_result.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.updates_result.configure(yscrollcommand=scroll.set)

    def _updates_refresh(self):
        self.updates_result.delete("1.0", tk.END)
        self._append_updates("--- Checking Windows Updates ---")
        threading.Thread(target=self._updates_thread, daemon=True).start()

    def _updates_thread(self):
        try:
            updates = get_windows_updates()
            for u in updates:
                if isinstance(u, dict):
                    self._append_updates(
                        f"- {u.get('description', 'N/A')} ({u.get('id', 'N/A')}) - {u.get('date', 'N/A')}"
                    )
                else:
                    self._append_updates(f"- {u}")
            settings = get_update_settings()
            self._append_updates(f"\nUpdate settings: {settings}")
        except Exception as e:
            self._append_updates(f"Error: {e}")

    def _updates_action(self, action):
        self.updates_result.delete("1.0", tk.END)
        self._append_updates("--- Applying ---")
        threading.Thread(target=lambda: self._updates_action_thread(action), daemon=True).start()

    def _updates_action_thread(self, action):
        try:
            ok = action()
            self._append_updates("Done." if ok else "Failed (admin rights may be required).")
        except Exception as e:
            self._append_updates(f"Error: {e}")

    def _append_updates(self, text):
        self.updates_result.after(0, lambda: (
            self.updates_result.insert(tk.END, text + "\n"),
            self.updates_result.see(tk.END),
        ))

    # ───────────────────────────────────────────────────────────────────
    # Disks
    # ───────────────────────────────────────────────────────────────────
    def _build_disks(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        tk.Button(toolbar, text="Refresh", command=self._disks_refresh,
                  bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="TRIM Selected", command=self._disks_trim,
                  bg="#27ae60", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Defrag Selected", command=self._disks_defrag,
                  bg="#2980b9", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=2)

        tree_frame = tk.Frame(container, bg=bg)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("letter", "type", "total", "free", "percent", "health")
        self.disks_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                       selectmode="browse")
        self.disks_tree.heading("letter", text="Drive")
        self.disks_tree.heading("type", text="Type")
        self.disks_tree.heading("total", text="Total GB")
        self.disks_tree.heading("free", text="Free GB")
        self.disks_tree.heading("percent", text="Used %")
        self.disks_tree.heading("health", text="Health")
        self.disks_tree.column("letter", width=80)
        self.disks_tree.column("type", width=80)
        self.disks_tree.column("total", width=100)
        self.disks_tree.column("free", width=100)
        self.disks_tree.column("percent", width=80)
        self.disks_tree.column("health", width=140)
        self.disks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.disks_tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.disks_tree.configure(yscrollcommand=scroll.set)

        self._disks_refresh()

    def _disks_refresh(self):
        try:
            drives = get_disk_drives()
            health = {h.get("device_id"): h for h in get_disk_health()}
            self.disks_tree.delete(*self.disks_tree.get_children())
            for d in drives:
                h = health.get(str(d["letter"])) or {}
                disk_type = "SSD" if is_ssd(d["letter"]) else "HDD"
                self.disks_tree.insert("", tk.END, values=(
                    d["letter"], disk_type, d["total_gb"], d["free_gb"],
                    d["percent"], h.get("health", "N/A")
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load disks: {e}")

    def _disks_selected_letter(self):
        sel = self.disks_tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a drive first.")
            return None
        return self.disks_tree.item(sel[0])["values"][0]

    def _disks_trim(self):
        letter = self._disks_selected_letter()
        if not letter:
            return
        threading.Thread(target=lambda: self._append_opt_disk(letter, run_trim(letter + ":")), daemon=True).start()

    def _disks_defrag(self):
        letter = self._disks_selected_letter()
        if not letter:
            return
        threading.Thread(target=lambda: self._append_opt_disk(letter, run_defrag(letter + ":")), daemon=True).start()

    def _append_opt_disk(self, letter, result):
        ok, out = result
        self.disks_tree.after(0, lambda: messagebox.showinfo(
            "Disk", f"{letter}: {'OK' if ok else 'Failed'}\n{out[:300]}"))

    # ───────────────────────────────────────────────────────────────────
    # Processes
    # ───────────────────────────────────────────────────────────────────
    def _build_processes(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        tk.Button(toolbar, text="Refresh", command=self._processes_refresh,
                  bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=2)

        tk.Label(toolbar, text="Priority:", bg=bg, fg=fg, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(15, 5))
        self.proc_priority_var = tk.StringVar(value="normal")
        for val, lbl in [("high", "High"), ("above_normal", "Above Normal"),
                         ("normal", "Normal"), ("below_normal", "Below Normal"),
                         ("idle", "Idle")]:
            tk.Radiobutton(toolbar, text=lbl, variable=self.proc_priority_var, value=val,
                           bg=bg, fg=fg, selectcolor=self.tm.get("surface"),
                           activebackground=bg, activeforeground=fg,
                           command=lambda: None).pack(side=tk.LEFT, padx=3)
        tk.Button(toolbar, text="Set Priority", command=self._processes_set_priority,
                  bg="#27ae60", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT, padx=5)

        tree_frame = tk.Frame(container, bg=bg)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("pid", "name", "cpu", "mem")
        self.proc_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                      selectmode="browse")
        self.proc_tree.heading("pid", text="PID")
        self.proc_tree.heading("name", text="Name")
        self.proc_tree.heading("cpu", text="CPU %")
        self.proc_tree.heading("mem", text="Memory MB")
        self.proc_tree.column("pid", width=80)
        self.proc_tree.column("name", width=200)
        self.proc_tree.column("cpu", width=80)
        self.proc_tree.column("mem", width=100)
        self.proc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.proc_tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.proc_tree.configure(yscrollcommand=scroll.set)

        self._processes_refresh()

    def _processes_refresh(self):
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
                try:
                    mem_mb = round(p.info["memory_info"].rss / (1024 * 1024), 1) if p.info["memory_info"] else 0
                    procs.append((p.info["pid"], p.info["name"], p.info["cpu_percent"], mem_mb))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x[3], reverse=True)
            self.proc_tree.delete(*self.proc_tree.get_children())
            for proc in procs[:200]:
                self.proc_tree.insert("", tk.END, values=proc)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load processes: {e}")

    def _processes_set_priority(self):
        sel = self.proc_tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a process first.")
            return
        pid = self.proc_tree.item(sel[0])["values"][0]
        level = self.proc_priority_var.get()
        priority_map = {
            "high": psutil.HIGH_PRIORITY_CLASS if hasattr(psutil, "HIGH_PRIORITY_CLASS") else 256,
            "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS if hasattr(psutil, "ABOVE_NORMAL_PRIORITY_CLASS") else 32768,
            "normal": psutil.NORMAL_PRIORITY_CLASS if hasattr(psutil, "NORMAL_PRIORITY_CLASS") else 32,
            "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS if hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS") else 16384,
            "idle": psutil.IDLE_PRIORITY_CLASS if hasattr(psutil, "IDLE_PRIORITY_CLASS") else 64,
        }
        nice_val = priority_map.get(level, priority_map["normal"])
        try:
            p = psutil.Process(pid)
            p.nice(nice_val)
            messagebox.showinfo("Success", f"Priority set to {level} for PID {pid}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    # ───────────────────────────────────────────────────────────────────
    # History
    # ───────────────────────────────────────────────────────────────────
    def _build_history(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = tk.Frame(container, bg=bg)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        btn_refresh = tk.Button(toolbar, text="Refresh", command=self._refresh_history,
                                bg=accent, fg="#ffffff", font=("Segoe UI", 9, "bold"),
                                relief=tk.FLAT, padx=8, cursor="hand2")
        btn_refresh.pack(side=tk.RIGHT, padx=2)

        self.hist_summary = tk.Label(toolbar, text="", bg=bg, fg=fg,
                                      font=("Segoe UI", 10, "bold"))
        self.hist_summary.pack(side=tk.LEFT, padx=5)

        tree_frame = tk.Frame(container, bg=bg)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("date", "freed", "files", "cache")
        self.hist_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                        selectmode="browse")
        self.hist_tree.heading("date", text="Date")
        self.hist_tree.heading("freed", text="RAM Freed (GB)")
        self.hist_tree.heading("files", text="Files")
        self.hist_tree.heading("cache", text="Cache (MB)")
        self.hist_tree.column("date", width=200)
        self.hist_tree.column("freed", width=120)
        self.hist_tree.column("files", width=100)
        self.hist_tree.column("cache", width=120)

        hist_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                     command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=hist_scroll.set)
        self.hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.hist_tree.tag_configure("success", foreground="#27ae60")
        self.hist_tree.tag_configure("error", foreground="#e74c3c")

        self._refresh_history()

    def _refresh_history(self):
        try:
            history = self.history if self.history is not None else None
            records = history.get_history() if history else get_history()
            self.hist_tree.delete(*self.hist_tree.get_children())
            for rec in records:
                date = rec.get("date", "")
                freed = rec.get("freed_gb", 0)
                files = rec.get("files_deleted", 0)
                cache = rec.get("cache_mb", 0)
                self.hist_tree.insert("", tk.END, values=(date, freed, files, cache))
            summary = history.get_summary() if history else get_summary()
            self.hist_summary.configure(
                text=f"Total operations: {summary.get('optimizations', 0)}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load history: {e}")

    # ───────────────────────────────────────────────────────────────────
    # Settings
    # ───────────────────────────────────────────────────────────────────
    def _build_settings(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")
        surface = self.tm.get("surface")

        outer = tk.Frame(parent, bg=bg)
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        self.settings_canvas = canvas
        self.settings_frame = tk.Frame(canvas, bg=bg)

        self.settings_frame.bind("<Configure>",
                                lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.settings_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.settings_entries = {}
        self._settings_rows = []
        self._settings_search_var = tk.StringVar()

        def _bind_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _bind_mousewheel)
        self.settings_frame.bind("<MouseWheel>", _bind_mousewheel)

        search_frame = tk.Frame(self.settings_frame, bg=bg)
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 0))
        tk.Label(search_frame, text="Search:", bg=bg, fg=fg,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        search_entry = tk.Entry(search_frame, textvariable=self._settings_search_var, width=30,
                                bg=surface, fg=fg, insertbackground=fg, font=("Segoe UI", 10),
                                relief=tk.FLAT, highlightthickness=1,
                                highlightbackground=self.tm.get("border"))
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self._settings_search_var.trace_add("write", lambda *_: self._filter_settings())

        sections = [
            ("General", [
                (("temp_cleaning", "enabled"), "Clean Temp Files", "bool"),
                (("dns_cache_clean",), "Clean DNS Cache", "bool"),
                (("prefetch_clean",), "Clean Prefetch", "bool"),
                (("thumbnail_cache_clean",), "Clean Thumbnail Cache", "bool"),
                (("font_cache_clean",), "Clean Font Cache", "bool"),
                (("clean_browser_cache",), "Clean Browser Cache", "bool"),
                (("clean_recycle_bin",), "Clean Recycle Bin", "bool"),
                (("windows_update_cache_clean",), "Clean WinUpdate Cache", "bool"),
                (("auto_restore_point",), "Create Restore Point on Optimize", "bool"),
                (("auto_theme",), "Auto Theme (follow Windows)", "bool"),
            ]),
            ("Services", [
                (("service_management", "disable_list"), "Services to Disable (comma separated)", "list"),
            ]),
            ("Optimization", [
                (("disk_optimization", "auto_trim_ssd"), "TRIM SSD", "bool"),
                (("disk_optimization", "auto_defrag_hdd"), "Defrag HDD", "bool"),
                (("disk_optimization", "check_health"), "Check Disk Health", "bool"),
            ]),
            ("Security", [
                (("security", "clean_browser_history"), "Clean Browser History", "bool"),
                (("security", "clean_recent_files"), "Clean Recent Files", "bool"),
                (("security", "clean_windows_logs"), "Clean Windows Logs", "bool"),
                (("security", "auto_defender_scan"), "Run Defender Scan on Security Clean", "bool"),
            ]),
            ("Startup", [
                (("startup_cleaning",), "Clean Startup on Optimize", "bool"),
            ]),
            ("Scheduling", [
                (("scheduled_optimization", "enabled"), "Enable Auto Schedule", "bool"),
                (("scheduled_optimization", "interval_hours"), "Interval (hours)", "int"),
            ]),
        ]

        row = 1
        for section_name, fields in sections:
            header = tk.Label(self.settings_frame, text=section_name, bg=bg, fg=accent,
                              font=("Segoe UI", 13, "bold"))
            header.grid(row=row, column=0, columnspan=2, sticky="w", pady=(15, 5), padx=5)
            self._settings_rows.append({"widget": header, "text": section_name.lower(),
                                        "section": True})
            row += 1

            for path, label, dtype in fields:
                lbl = tk.Label(self.settings_frame, text=label, bg=bg, fg=fg,
                               font=("Segoe UI", 10))
                lbl.grid(row=row, column=0, sticky="w", padx=10, pady=3)

                current = self._cfg_get(path)
                if dtype == "bool":
                    var = tk.BooleanVar(value=bool(current))
                    entry = tk.Checkbutton(self.settings_frame, variable=var,
                                            bg=bg, fg=fg, selectcolor=surface,
                                            activebackground=bg, activeforeground=fg)
                elif dtype == "list":
                    var = tk.StringVar(value=", ".join(current or []))
                    entry = tk.Entry(self.settings_frame, textvariable=var, width=40,
                                     bg=surface, fg=fg, insertbackground=fg,
                                     font=("Consolas", 9), relief=tk.FLAT,
                                     highlightthickness=1,
                                     highlightbackground=self.tm.get("border"))
                elif dtype == "int":
                    var = tk.StringVar(value=str(current if current is not None else 0))
                    entry = tk.Entry(self.settings_frame, textvariable=var, width=20,
                                     bg=surface, fg=fg, insertbackground=fg,
                                     font=("Consolas", 9), relief=tk.FLAT,
                                     highlightthickness=1,
                                     highlightbackground=self.tm.get("border"))
                else:
                    var = tk.StringVar(value=str(current if current is not None else ""))
                    entry = tk.Entry(self.settings_frame, textvariable=var, width=40,
                                     bg=surface, fg=fg, insertbackground=fg,
                                     font=("Consolas", 9), relief=tk.FLAT,
                                     highlightthickness=1,
                                     highlightbackground=self.tm.get("border"))

                entry.grid(row=row, column=1, sticky="w", padx=10, pady=3)
                self.settings_entries[".".join(path)] = (var, dtype, path)
                self._settings_rows.append({"widget": lbl, "entry": entry,
                                            "text": label.lower(), "section": False})
                row += 1

        self.settings_frame.columnconfigure(0, weight=0)
        self.settings_frame.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(self.settings_frame, bg=bg)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        row += 1

        save_btn = tk.Button(btn_frame, text="Save Settings", command=self._save_settings,
                             bg="#27ae60", fg="#ffffff", font=("Segoe UI", 11, "bold"),
                             relief=tk.FLAT, padx=20, pady=6, cursor="hand2")
        save_btn.pack(side=tk.LEFT, padx=5)

        export_btn = tk.Button(btn_frame, text="Export", command=self._export_settings,
                                bg=accent, fg="#ffffff", font=("Segoe UI", 10, "bold"),
                                relief=tk.FLAT, padx=14, pady=6, cursor="hand2")
        export_btn.pack(side=tk.LEFT, padx=5)

        import_btn = tk.Button(btn_frame, text="Import", command=self._import_settings,
                                bg=accent, fg="#ffffff", font=("Segoe UI", 10, "bold"),
                                relief=tk.FLAT, padx=14, pady=6, cursor="hand2")
        import_btn.pack(side=tk.LEFT, padx=5)

    def _cfg_get(self, path):
        cur = self.config
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return None
        return cur

    def _cfg_set(self, path, value):
        cur = self.config
        for k in path[:-1]:
            if not isinstance(cur.get(k), dict):
                cur[k] = {}
            cur = cur[k]
        cur[path[-1]] = value

    def _save_settings(self):
        try:
            for sid, (var, dtype, path) in self.settings_entries.items():
                raw = var.get()
                if dtype == "bool":
                    value = bool(raw)
                elif dtype == "int":
                    try:
                        value = int(raw)
                    except ValueError:
                        value = 0
                elif dtype == "list":
                    value = [s.strip() for s in raw.split(",") if s.strip()]
                else:
                    value = raw
                self._cfg_set(path, value)

            save_config(self.config)
            messagebox.showinfo("Success", "Settings saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _filter_settings(self):
        query = self._settings_search_var.get().strip().lower()
        for item in self._settings_rows:
            widget = item["widget"]
            match = (not query) or (query in item["text"])
            if match:
                widget.grid()
            else:
                widget.grid_remove()
            if not item.get("section") and "entry" in item:
                if match:
                    item["entry"].grid()
                else:
                    item["entry"].grid_remove()

    def _export_settings(self):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 filetypes=[("JSON", "*.json")],
                                                 title="Export Settings")
            if not path:
                return
            import shutil
            shutil.copy2(CONFIG_PATH, path)
            messagebox.showinfo("Success", f"Settings exported to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def _import_settings(self):
        try:
            path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")],
                                              title="Import Settings")
            if not path:
                return
            import json
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            self.config.clear()
            self.config.update(imported)
            save_config(self.config)
            messagebox.showinfo("Success", "Settings imported. Restart the app to apply fully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import: {e}")

    # ───────────────────────────────────────────────────────────────────
    # About
    # ───────────────────────────────────────────────────────────────────
    def _build_about(self, parent):
        bg = self.tm.get("bg")
        fg = self.tm.get("fg")
        accent = self.tm.get("accent")

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        center = tk.Frame(container, bg=bg)
        center.place(relx=0.5, rely=0.4, anchor="center")

        tk.Label(center, text="Silent PC Optimizer", bg=bg, fg=fg,
                  font=("Segoe UI", 24, "bold")).pack(pady=(0, 5))
        tk.Label(center, text=f"v{VERSION}", bg=bg, fg=accent,
                  font=("Segoe UI", 14)).pack(pady=(0, 15))
        tk.Label(center, text="A lightweight Windows optimization tool\n"
                              "designed to keep your system fast and clean.",
                 bg=bg, fg=self.tm.get("fg_dim", fg),
                 font=("Segoe UI", 11), justify=tk.CENTER).pack(pady=(0, 20))

        features = [
            "System cleaning and optimization",
            "Service and startup management",
            "Benchmark and monitoring",
            "Security and privacy tools",
            "File encryption and decryption",
            "Game mode and presentation mode",
        ]
        tk.Label(center, text="Features:", bg=bg, fg=accent,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))
        for feat in features:
            tk.Label(center, text=f"  {feat}", bg=bg, fg=fg,
                     font=("Segoe UI", 10), anchor="w").pack(anchor="w")

        bottom = tk.Frame(container, bg=bg)
        bottom.pack(side=tk.BOTTOM, pady=10)
        tk.Label(bottom, text="Use at your own risk. Always back up important data.",
                 bg=bg, fg="#e74c3c", font=("Segoe UI", 9, "italic")).pack()

    # ───────────────────────────────────────────────────────────────────
    # Periodic refresh
    # ───────────────────────────────────────────────────────────────────
    def _start_refresh(self):
        if self._running:
            self._refresh_metrics()
            self.root.after(2000, self._start_refresh)

    def _refresh_metrics(self):
        try:
            now = time.time()
            dt = now - self._last_time if self._last_time else 1
            self._last_time = now

            cpu_val = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            net_io = psutil.net_io_counters()

            disk_read_speed = (disk_io.read_bytes - self._last_disk.read_bytes) / dt / 1024 if dt > 0 else 0
            disk_write_speed = (disk_io.write_bytes - self._last_disk.write_bytes) / dt / 1024 if dt > 0 else 0
            net_sent_speed = (net_io.bytes_sent - self._last_net.bytes_sent) / dt / 1024 if dt > 0 else 0
            net_recv_speed = (net_io.bytes_recv - self._last_net.bytes_recv) / dt / 1024 if dt > 0 else 0

            self._last_disk = disk_io
            self._last_net = net_io

            self._monitor_data["cpu"].append(cpu_val)
            self._monitor_data["ram"].append(ram.percent)
            self._monitor_data["disk_read"].append(disk_read_speed)
            self._monitor_data["disk_write"].append(disk_write_speed)
            self._monitor_data["net_sent"].append(net_sent_speed)
            self._monitor_data["net_recv"].append(net_recv_speed)

            for key in self._monitor_data:
                if len(self._monitor_data[key]) > self._monitor_max:
                    self._monitor_data[key] = self._monitor_data[key][-self._monitor_max:]

            status_text = (f"CPU: {cpu_val:.1f}%  |  "
                           f"RAM: {ram.percent:.1f}% ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB)  |  "
                           f"Disk R: {disk_read_speed:.0f} KB/s  W: {disk_write_speed:.0f} KB/s  |  "
                           f"Net Sent: {net_sent_speed:.0f} KB/s  Recv: {net_recv_speed:.0f} KB/s")
            self.status_label.configure(text=status_text)
            self.status_right.configure(text=time.strftime("%H:%M:%S"))

            self._update_dashboard(cpu_val, ram, disk_io, net_io, disk_read_speed, disk_write_speed)
            self._update_monitoring_charts()
            self._update_mini_graphs(cpu_val, ram.percent)

        except Exception:
            pass

    def _update_dashboard(self, cpu_val, ram, disk_io, net_io, disk_read, disk_write):
        try:
            if hasattr(self, "cpu_widget") and isinstance(self.cpu_widget, DashboardWidget):
                self.cpu_widget.update_bar("usage", cpu_val)
                self.cpu_widget.update_metric("cores", f"{psutil.cpu_count()} cores")
                self.cpu_widget.update_metric("temp", "Temperature: N/A")
            elif hasattr(self, "cpu_widget") and hasattr(self.cpu_widget, "configure"):
                self.cpu_widget.configure(text=f"CPU\n{cpu_val:.1f}%")
        except Exception:
            pass

        try:
            if hasattr(self, "ram_widget") and isinstance(self.ram_widget, DashboardWidget):
                self.ram_widget.update_bar("usage", ram.percent)
                self.ram_widget.update_metric("used", f"{ram.used // (1024**3)} / {ram.total // (1024**3)} GB")
                self.ram_widget.update_metric("free", f"{ram.available // (1024**3)} GB")
            elif hasattr(self, "ram_widget") and hasattr(self.ram_widget, "configure"):
                self.ram_widget.configure(
                    text=f"RAM\n{ram.percent:.1f}%\n{ram.used // (1024**3)}/{ram.total // (1024**3)} GB")
        except Exception:
            pass

        try:
            disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
            if hasattr(self, "disk_widget") and isinstance(self.disk_widget, DashboardWidget):
                self.disk_widget.update_bar("usage", disk.percent)
                self.disk_widget.update_metric("space", f"{disk.used // (1024**3)} / {disk.total // (1024**3)} GB")
                self.disk_widget.update_metric("free", f"{disk.free // (1024**3)} GB")
            elif hasattr(self, "disk_widget") and hasattr(self.disk_widget, "configure"):
                self.disk_widget.configure(
                    text=f"Disk\n{disk.percent:.1f}%\nFree: {disk.free // (1024**3)} GB")
        except Exception:
            pass

        try:
            if hasattr(self, "net_widget") and isinstance(self.net_widget, DashboardWidget):
                self.net_widget.update_metric("sent", f"{net_io.bytes_sent // (1024**2)} MB")
                self.net_widget.update_metric("recv", f"{net_io.bytes_recv // (1024**2)} MB")
            elif hasattr(self, "net_widget") and hasattr(self.net_widget, "configure"):
                self.net_widget.configure(
                    text=f"Network\nSent: {net_io.bytes_sent // (1024**2)} MB\n"
                         f"Recv: {net_io.bytes_recv // (1024**2)} MB")
        except Exception:
            pass

    def _update_monitoring_charts(self):
        try:
            cpu_data = self._monitor_data["cpu"]
            ram_data = self._monitor_data["ram"]
            disk_total = [r + w for r, w in zip(self._monitor_data["disk_read"],
                                                 self._monitor_data["disk_write"])]
            net_total = [s + r for s, r in zip(self._monitor_data["net_sent"],
                                                self._monitor_data["net_recv"])]
            max_disk = max(max(disk_total), 100)
            max_net = max(max(net_total), 100)

            self._draw_chart(self.mon_cpu_canvas, cpu_data, "CPU Usage (%)", "#2ecc71", 100)
            self._draw_chart(self.mon_ram_canvas, ram_data, "RAM Usage (%)", "#3498db", 100)
            self._draw_chart(self.mon_disk_canvas, disk_total, "Disk I/O (KB/s)", "#e67e22", max_disk)
            self._draw_chart(self.mon_net_canvas, net_total, "Network (KB/s)", "#9b59b6", max_net)
        except Exception:
            pass

    def _update_mini_graphs(self, cpu_val, ram_val):
        try:
            if hasattr(self, "cpu_mini"):
                self.cpu_mini.add_point(cpu_val)
            if hasattr(self, "ram_mini"):
                self.ram_mini.add_point(ram_val)
        except Exception:
            pass

    def destroy(self):
        self._running = False
        try:
            if hasattr(self, "settings_canvas") and self.settings_canvas:
                self.settings_canvas.unbind("<MouseWheel>")
        except Exception:
            pass
        try:
            if hasattr(self, "settings_frame") and self.settings_frame:
                self.settings_frame.unbind("<MouseWheel>")
        except Exception:
            pass
