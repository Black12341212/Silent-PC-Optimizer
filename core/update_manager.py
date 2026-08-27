import subprocess
from core.logger import logger


def get_windows_updates():
    updates = []
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-HotFix | Select-Object HotFixID, Description, InstalledOn, InstalledBy | Sort-Object InstalledOn -Descending | Select-Object -First 50 | ConvertTo-Json"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            data = json.loads(result.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for item in data:
                updates.append({
                    "id": item.get("HotFixID", ""),
                    "description": item.get("Description", ""),
                    "date": item.get("InstalledOn", ""),
                    "installed_by": item.get("InstalledBy", ""),
                })
    except Exception as e:
        logger.error(f"Ошибка получения обновлений: {e}")
    return updates


def get_update_settings():
    settings = {}
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             """Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update' -ErrorAction SilentlyContinue | Select-Object AUOptions, NoAutoUpdate | ConvertTo-Json"""],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            data = json.loads(result.stdout.strip())
            au_options = data.get("AUOptions", 0)
            settings_map = {
                2: "notify_for_download",
                3: "auto_download_notify_install",
                4: "auto_download_auto_install",
                5: "allow_local_admin_choice",
            }
            settings["mode"] = settings_map.get(au_options, "unknown")
            settings["au_options"] = au_options
            settings["no_auto_update"] = data.get("NoAutoUpdate", 0)
    except Exception as e:
        logger.error(f"Ошибка чтения настроек обновлений: {e}")
    return settings


def set_update_defer(days=7):
    try:
        registry_cmd = f"""
        if (-not (Test-Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate')) {{
            New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate' -Force | Out-Null
        }}
        Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate' -Name 'DeferFeatureUpdates' -Value 1 -Force
        Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate' -Name 'DeferFeatureUpdatesPeriodInDays' -Value {days} -Force
        Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate' -Name 'DeferQualityUpdates' -Value 1 -Force
        Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate' -Name 'DeferQualityUpdatesPeriodInDays' -Value {days} -Force
        """
        subprocess.run(
            ["powershell", "-Command", registry_cmd],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        logger.info(f"Обновления отложены на {days} дней")
        return True
    except Exception as e:
        logger.error(f"Ошибка откладывания обновлений: {e}")
        return False


def block_auto_updates():
    try:
        cmd = """
        Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU' -Name 'NoAutoUpdate' -Value 1 -Force
        Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU' -Name 'AUOptions' -Value 2 -Force
        """
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        logger.info("Автоматические обновления заблокированы")
        return True
    except Exception as e:
        logger.error(f"Ошибка блокировки обновлений: {e}")
        return False


def unblock_auto_updates():
    try:
        cmd = """
        Remove-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU' -Name 'NoAutoUpdate' -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU' -Name 'AUOptions' -Value 4 -Force -ErrorAction SilentlyContinue
        """
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        logger.info("Автоматические обновления разблокированы")
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False
