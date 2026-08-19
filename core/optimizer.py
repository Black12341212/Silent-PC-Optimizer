import os
import time
import ctypes
from core.logger import logger


def clean_temp_files(config):
    temp_cfg = config.get("temp_cleaning", {})
    if not temp_cfg.get("enabled", True):
        return 0, 0.0

    temp_folder = os.getenv("TEMP")
    if not temp_folder:
        return 0, 0.0

    min_age_hours = temp_cfg.get("min_age_hours", 24)
    extensions = temp_cfg.get("extensions", [".tmp", ".log", ".cab"])
    min_age_seconds = min_age_hours * 3600
    now = time.time()

    deleted_count = 0
    bytes_cleared = 0

    for root, dirs, files in os.walk(temp_folder):
        for fname in files:
            file_path = os.path.join(root, fname)
            try:
                ext = os.path.splitext(fname)[1].lower()
                if extensions and ext not in extensions:
                    continue

                mtime = os.path.getmtime(file_path)
                if (now - mtime) < min_age_seconds:
                    continue

                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                bytes_cleared += file_size
                deleted_count += 1
            except PermissionError:
                logger.debug(f"Файл заблокирован: {file_path}")
            except OSError as e:
                logger.debug(f"Ошибка удаления {file_path}: {e}")

    mb_cleared = round(bytes_cleared / (1024 * 1024), 2)
    logger.info(f"Очистка TEMP: удалено {deleted_count} файлов, освобождено {mb_cleared} МБ")
    return deleted_count, mb_cleared


def clean_tmp_folder(config):
    if not config.get("clean_tmp_folder", True):
        return 0, 0.0

    tmp_folder = os.getenv("TMP")
    if not tmp_folder or tmp_folder == os.getenv("TEMP"):
        return 0, 0.0

    deleted_count = 0
    bytes_cleared = 0

    for root, dirs, files in os.walk(tmp_folder):
        for fname in files:
            file_path = os.path.join(root, fname)
            try:
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                bytes_cleared += file_size
                deleted_count += 1
            except (PermissionError, OSError):
                pass

    mb_cleared = round(bytes_cleared / (1024 * 1024), 2)
    if deleted_count > 0:
        logger.info(f"Очистка TMP: удалено {deleted_count} файлов, освобождено {mb_cleared} МБ")
    return deleted_count, mb_cleared


def clean_recycle_bin(config):
    if not config.get("clean_recycle_bin", False):
        return False

    try:
        from win32com.shell import shell, shellcon
        result = shell.SHEmptyRecycleBin(None, None, shellcon.SHERB_NOCONFIRMATION | shellcon.SHERB_NOPROGRESSUI)
        if result == 0:
            logger.info("Корзина очищена")
            return True
        else:
            logger.warning(f"Ошибка очистки корзины: код {result}")
            return False
    except ImportError:
        logger.warning("pywin32 не установлен, очистка корзины недоступна")
        return False
    except Exception as e:
        logger.error(f"Ошибка очистки корзины: {e}")
        return False


def clean_browser_cache(config):
    if not config.get("clean_browser_cache", False):
        return 0, 0.0

    cache_paths = config.get("browser_cache_paths", {})
    home = os.path.expanduser("~")
    total_deleted = 0
    total_bytes = 0

    for browser_name, rel_path in cache_paths.items():
        cache_dir = os.path.join(home, rel_path)
        if not os.path.exists(cache_dir):
            continue

        for root, dirs, files in os.walk(cache_dir):
            for fname in files:
                file_path = os.path.join(root, fname)
                try:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    total_bytes += file_size
                    total_deleted += 1
                except (PermissionError, OSError):
                    pass

        logger.info(f"Кэш {browser_name}: удалено {total_deleted} файлов")

    mb_cleared = round(total_bytes / (1024 * 1024), 2)
    return total_deleted, mb_cleared
