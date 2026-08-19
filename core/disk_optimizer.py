import subprocess
import os
import shutil
from core.logger import logger


def get_disk_drives():
    drives = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        path = f"{letter}:\\"
        if os.path.exists(path):
            try:
                usage = shutil.disk_usage(path)
                total = usage.total
                free = usage.free
                used = total - free
                drives.append({
                    "letter": letter,
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                    "percent": round((used / total) * 100, 1) if total > 0 else 0,
                })
            except Exception:
                pass
    return drives


def is_ssd(drive_letter="C"):
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"Get-PhysicalDisk | Where-Object {{($_.FriendlyName -like '*{drive_letter}*') -or ($_.DeviceId -eq '0')}} | Select-Object -ExpandProperty MediaType"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        output = result.stdout.strip().lower()
        if "ssd" in output or "non-rotating" in output:
            return True
        if "hdd" in output or "rotating" in output:
            return False
        try:
            result2 = subprocess.run(
                ["powershell", "-Command",
                 "Get-PhysicalDisk | Select-Object -First 1 -ExpandProperty MediaType"],
                capture_output=True, text=True, timeout=15, creationflags=0x08000000
            )
            out2 = result2.stdout.strip().lower()
            return "ssd" in out2 or "non-rotating" in out2
        except Exception:
            return False
    except Exception:
        return False


def run_trim(drive="C:"):
    try:
        result = subprocess.run(
            ["defrag", drive, "/O", "/U"],
            capture_output=True, text=True, timeout=300, creationflags=0x08000000
        )
        if result.returncode == 0:
            logger.info(f"TRIM выполнен для {drive}")
            return True, result.stdout
        else:
            logger.warning(f"TRIM ошибка {drive}: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        logger.error(f"Ошибка TRIM: {e}")
        return False, str(e)


def run_defrag(drive="C:"):
    try:
        result = subprocess.run(
            ["defrag", drive, "/U", "/V"],
            capture_output=True, text=True, timeout=600, creationflags=0x08000000
        )
        if result.returncode == 0:
            logger.info(f"Дефрагментация завершена для {drive}")
            return True, result.stdout
        else:
            logger.warning(f"Дефрагментация ошибка {drive}: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        logger.error(f"Ошибка дефрагментации: {e}")
        return False, str(e)


def get_disk_health():
    health_info = []
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, HealthStatus, OperationalStatus, Size | ConvertTo-Json"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            disks = json.loads(result.stdout.strip())
            if isinstance(disks, dict):
                disks = [disks]
            for disk in disks:
                health_info.append({
                    "device_id": disk.get("DeviceId", "?"),
                    "name": disk.get("FriendlyName", "Unknown"),
                    "type": disk.get("MediaType", "Unknown"),
                    "health": disk.get("HealthStatus", "Unknown"),
                    "status": disk.get("OperationalStatus", "Unknown"),
                    "size_gb": round(disk.get("Size", 0) / (1024**3), 1),
                })
    except Exception as e:
        logger.error(f"Ошибка получения SMART: {e}")
    return health_info


def optimize_drive(config):
    disk_cfg = config.get("disk_optimization", {})
    results = {"trim": None, "defrag": None, "health": []}
    if disk_cfg.get("check_health", True):
        results["health"] = get_disk_health()
    ssd = is_ssd()
    if ssd and disk_cfg.get("auto_trim_ssd", True):
        success, output = run_trim()
        results["trim"] = {"success": success, "output": output[:500] if output else ""}
    elif not ssd and disk_cfg.get("auto_defrag_hdd", False):
        success, output = run_defrag()
        results["defrag"] = {"success": success, "output": output[:500] if output else ""}
    results["is_ssd"] = ssd
    return results
