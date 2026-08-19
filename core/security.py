import os
import time
import subprocess
from core.logger import logger


def clean_browser_history(config):
    if not config.get("security", {}).get("clean_browser_history", False):
        return 0
    home = os.path.expanduser("~")
    cleaned = 0
    browser_histories = {
        "Chrome": [
            os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "History"),
            os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cookies"),
            os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"),
        ],
        "Firefox": [
            os.path.join(home, "AppData", "Roaming", "Mozilla", "Firefox", "Profiles"),
        ],
        "Edge": [
            os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "History"),
            os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cookies"),
        ],
    }
    for browser, paths in browser_histories.items():
        for path in paths:
            if os.path.isfile(path):
                try:
                    os.remove(path)
                    cleaned += 1
                    logger.info(f"История {browser} удалена: {os.path.basename(path)}")
                except (PermissionError, OSError):
                    pass
            elif os.path.isdir(path):
                try:
                    for f in os.listdir(path):
                        fp = os.path.join(path, f)
                        if os.path.isfile(fp):
                            try:
                                os.remove(fp)
                                cleaned += 1
                            except (PermissionError, OSError):
                                pass
                except (PermissionError, OSError):
                    pass
    return cleaned


def clean_recent_files(config):
    if not config.get("security", {}).get("clean_recent_files", True):
        return 0
    cleaned = 0
    recent_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Recent")
    if os.path.exists(recent_dir):
        for f in os.listdir(recent_dir):
            fp = os.path.join(recent_dir, f)
            try:
                os.remove(fp)
                cleaned += 1
            except (PermissionError, OSError):
                pass
    jump_list = os.path.join(
        os.environ.get("APPDATA", ""),
        "Microsoft", "Windows", "Recent", "AutomaticDestinations"
    )
    if os.path.exists(jump_list):
        for f in os.listdir(jump_list):
            fp = os.path.join(jump_list, f)
            try:
                os.remove(fp)
                cleaned += 1
            except (PermissionError, OSError):
                pass
    if cleaned > 0:
        logger.info(f"Удалено {cleaned} недавних файлов")
    return cleaned


def clean_windows_logs(config):
    if not config.get("security", {}).get("clean_windows_logs", False):
        return 0
    cleaned = 0
    log_dirs = [
        os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "Logs"),
        os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "Temp"),
    ]
    for log_dir in log_dirs:
        if not os.path.exists(log_dir):
            continue
        for f in os.listdir(log_dir):
            fp = os.path.join(log_dir, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                    cleaned += 1
            except (PermissionError, OSError):
                pass
    if cleaned > 0:
        logger.info(f"Очищено {cleaned} лог-файлов Windows")
    return cleaned


def run_defender_scan():
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             r"Start-MpScan -ScanType QuickScan | Out-String"],
            capture_output=True, text=True, timeout=300, creationflags=0x08000000
        )
        output = result.stdout
        threats = 0
        if "Threat" in output or "Угроз" in output.lower():
            lines = output.splitlines()
            for line in lines:
                if "Threat" in line or "угроз" in line.lower():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        try:
                            threats = int(parts[-1].strip())
                        except ValueError:
                            pass
        logger.info(f"Defender сканирование завершено. Угроз: {threats}")
        return {
            "success": result.returncode == 0,
            "threats": threats,
            "output": output[-1500:] if output else "",
        }
    except Exception as e:
        logger.error(f"Ошибка сканирования Defender: {e}")
        return {"success": False, "threats": 0, "output": str(e)}


def get_defender_status():
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled, AntivirusEnabled, QuickScanEndTime, FullScanEndTime | ConvertTo-Json"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            return json.loads(result.stdout.strip())
    except Exception:
        pass
    return {}


def clean_all_security(config):
    results = {}
    results["browser_history"] = clean_browser_history(config)
    results["recent_files"] = clean_recent_files(config)
    results["windows_logs"] = clean_windows_logs(config)
    return results
