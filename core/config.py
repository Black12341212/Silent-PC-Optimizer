import json
import os
import sys
import shutil

DEFAULT_CONFIG = {
    "ram_threshold": 85.0,
    "check_interval": 30,
    "browser_names": ["Chrome", "Firefox", "Edge", "Opera", "Yandex"],
    "auto_mode": True,
    "language": "ru",
    "theme": "dark",
        "temp_cleaning": {
            "enabled": True,
            "min_age_hours": 24,
            "extensions": [".tmp", ".log", ".cab"]
        },
    "clean_tmp_folder": True,
    "clean_recycle_bin": False,
    "clean_browser_cache": False,
    "browser_cache_paths": {
        "Chrome": "AppData/Local/Google/Chrome/User Data/Default/Cache",
        "Firefox": "AppData/Local/Mozilla/Firefox/Profiles",
        "Edge": "AppData/Local/Microsoft/Edge/User Data/Default/Cache"
    },
    "background_process_killer": {
        "enabled": False,
        "ram_threshold_mb": 500,
        "whitelist": [
            "svchost.exe", "explorer.exe", "csrss.exe", "dwm.exe",
            "system", "smss.exe", "wininit.exe", "services.exe",
            "lsass.exe", "sihost.exe", "taskhostw.exe", "RuntimeBroker.exe",
            "pythonw.exe", "python.exe"
        ]
    },
    "hibernation": {
        "enabled": False,
        "idle_minutes": 30,
        "ram_threshold": 90.0,
        "notify_before_seconds": 10
    },
    "autostart": False,
    "dns_cache_clean": True,
    "prefetch_clean": True,
    "thumbnail_cache_clean": True,
    "font_cache_clean": False,
    "windows_update_cache_clean": False,
    "service_management": {
        "enabled": False,
        "disable_list": [
            "SysMain", "WSearch", "Spooler", "DiagTrack",
            "dmwappushservice", "MapsBroker", "lfsvc", "RetailDemo",
            "WMPNetworkSvc", "XblAuthManager", "XblGameSave",
            "XboxNetApiSvc", "XboxGipSvc"
        ]
    },
    "disk_optimization": {
        "auto_trim_ssd": True,
        "auto_defrag_hdd": False,
        "check_health": True
    },
    "scheduled_optimization": {
        "enabled": False,
        "interval_hours": 2,
        "daily_time": "03:00",
        "mode": "interval"
    },
    "startup_cleaning": False,
    "game_mode": {
        "enabled": False,
        "watch_apps": ["firefox.exe", "chrome.exe"],
        "boost_on_launch": True
    },
    "streaming_mode": {
        "enabled": False,
        "prioritize_obs": True,
        "prioritize_browsers": True
    },
    "presentation_mode": {
        "enabled": False
    },
    "hotkeys": {
        "optimize": "ctrl+alt+o",
        "enabled": True
    },
    "process_protection": False,
    "portable_mode": False,
    "auto_restore_point": False,
    "auto_theme": False,
    "email_alerts": {
        "enabled": False,
        "smtp_server": "",
        "smtp_port": 587,
        "email": "",
        "password": "",
        "recipient": ""
    },
    "telegram_alerts": {
        "enabled": False,
        "bot_token": "",
        "chat_id": ""
    },
    "alert_thresholds": {
        "cpu_percent": 90,
        "ram_percent": 90,
        "disk_percent": 95,
        "temperature_celsius": 85
    },
    "benchmark": {
        "last_result": None,
        "ram_size_mb": 100,
        "file_size_mb": 50
    },
    "security": {
        "clean_browser_history": False,
        "clean_recent_files": True,
        "clean_windows_logs": False,
        "default_algorithm": "AES-256-CBC",
        "auto_defender_scan": False
    }
}


def _base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _base_dir()
CONFIG_PATH = os.path.join(BASE_DIR, "settings.json")
LOG_PATH = os.path.join(BASE_DIR, "logs.log")
HISTORY_PATH = os.path.join(BASE_DIR, "optimization_history.json")
PORTABLE_CONFIG_PATH = os.path.join(BASE_DIR, "settings.json")


def _deep_merge(base, override):
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        merged = _deep_merge(DEFAULT_CONFIG, user_cfg)
        return merged
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_startup_path():
    return os.path.join(
        os.environ.get("APPDATA", ""),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )


def toggle_autostart(enable):
    startup_dir = get_startup_path()
    link_path = os.path.join(startup_dir, "SilentOptimizer.lnk")
    script_path = os.path.abspath(sys.argv[0])

    if enable:
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(link_path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{script_path}"'
            shortcut.WorkingDirectory = os.path.dirname(script_path)
            shortcut.IconLocation = sys.executable
            shortcut.save()
            return True
        except Exception:
            try:
                shutil.copy2(script_path, os.path.join(startup_dir, "SilentOptimizer.pyw"))
                return True
            except Exception:
                return False
    else:
        try:
            if os.path.exists(link_path):
                os.remove(link_path)
            fallback = os.path.join(startup_dir, "SilentOptimizer.pyw")
            if os.path.exists(fallback):
                os.remove(fallback)
            return True
        except Exception:
            return False


def is_autostart_active():
    startup_dir = get_startup_path()
    return (
        os.path.exists(os.path.join(startup_dir, "SilentOptimizer.lnk")) or
        os.path.exists(os.path.join(startup_dir, "SilentOptimizer.pyw"))
    )
