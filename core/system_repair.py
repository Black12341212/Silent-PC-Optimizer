import subprocess
import os
from core.logger import logger


def run_sfc_scan():
    try:
        result = subprocess.run(
            ["sfc", "/scannow"],
            capture_output=True, text=True, timeout=600, creationflags=0x08000000
        )
        output = result.stdout
        repaired = 0
        for line in output.splitlines():
            if "repaired" in line.lower() or "восстановлен" in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            repaired = int(part)
                            break
                except Exception:
                    pass
        logger.info(f"SFC scan завершён. Восстановлено: {repaired}")
        return {
            "success": result.returncode == 0,
            "repaired": repaired,
            "output": output[-2000:] if output else "",
        }
    except Exception as e:
        logger.error(f"Ошибка SFC: {e}")
        return {"success": False, "repaired": 0, "output": str(e)}


def run_dism_repair():
    try:
        result = subprocess.run(
            ["dism", "/online", "/cleanup-image", "/restorehealth"],
            capture_output=True, text=True, timeout=900, creationflags=0x08000000
        )
        logger.info("DISM восстановление завершено")
        return {
            "success": result.returncode == 0,
            "output": result.stdout[-2000:] if result.stdout else "",
        }
    except Exception as e:
        logger.error(f"Ошибка DISM: {e}")
        return {"success": False, "output": str(e)}


def check_system_files():
    results = {"sfc": None, "dism": None}
    try:
        results["sfc"] = run_sfc_scan()
    except Exception as e:
        results["sfc"] = {"success": False, "output": str(e)}
    return results


def get_system_info():
    import platform
    import psutil
    info = {
        "os": platform.platform(),
        "processor": platform.processor(),
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "python": platform.python_version(),
    }
    return info
