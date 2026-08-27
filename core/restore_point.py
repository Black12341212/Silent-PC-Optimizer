import subprocess
from core.logger import logger


def create_restore_point(description="Silent PC Optimizer Cleanup"):
    try:
        ps = (
            "Checkpoint-Computer -Description "
            f"'{description}' -RestorePointType 'MODIFY_SETTINGS'"
        )
        result = subprocess.run(
            ["powershell", "-Command", ps],
            capture_output=True, text=True, timeout=120, creationflags=0x08000000
        )
        if result.returncode == 0:
            logger.info(f"Точка восстановления создана: {description}")
            return True
        logger.warning(f"Не удалось создать точку восстановления: {result.stderr}")
        return False
    except Exception as e:
        logger.error(f"Ошибка создания точки восстановления: {e}")
        return False


def restore_points_supported():
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-ComputerRestorePoint -ErrorAction SilentlyContinue | Select-Object -First 1 | ConvertTo-Json"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        return result.returncode == 0
    except Exception:
        return False
