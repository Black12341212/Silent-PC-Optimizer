import os
import subprocess
import shutil
from core.logger import logger


def flush_dns_cache():
    try:
        result = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.returncode == 0:
            logger.info("DNS-кэш очищен")
            return True
        else:
            logger.warning(f"Ошибка очистки DNS: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Ошибка очистки DNS-кэша: {e}")
        return False


def clean_windows_update_cache():
    cleaned_mb = 0.0
    try:
        service_stop = subprocess.run(
            ["net", "stop", "wuauserv"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        download_dir = os.path.join(
            os.environ.get("SYSTEMROOT", r"C:\Windows"),
            "SoftwareDistribution", "Download"
        )
        if os.path.exists(download_dir):
            for root, dirs, files in os.walk(download_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fp)
                        os.remove(fp)
                        cleaned_mb += size / (1024 * 1024)
                    except (PermissionError, OSError):
                        pass
        subprocess.run(
            ["net", "start", "wuauserv"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        cleaned_mb = round(cleaned_mb, 2)
        if cleaned_mb > 0:
            logger.info(f"Кэш Windows Update: освобождено {cleaned_mb} МБ")
        return cleaned_mb
    except Exception as e:
        logger.error(f"Ошибка очистки кэша Windows Update: {e}")
        return 0.0


def clean_thumbnail_cache():
    cleaned_mb = 0.0
    thumb_dir = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "Windows", "Explorer"
    )
    if not os.path.exists(thumb_dir):
        return 0.0
    try:
        for f in os.listdir(thumb_dir):
            if f.startswith("thumbcache_") and f.endswith(".db"):
                fp = os.path.join(thumb_dir, f)
                try:
                    size = os.path.getsize(fp)
                    os.remove(fp)
                    cleaned_mb += size / (1024 * 1024)
                except (PermissionError, OSError):
                    pass
        cleaned_mb = round(cleaned_mb, 2)
        if cleaned_mb > 0:
            logger.info(f"Кэш миниатюр: освобождено {cleaned_mb} МБ")
        return cleaned_mb
    except Exception as e:
        logger.error(f"Ошибка очистки кэша миниатюр: {e}")
        return 0.0


def clean_font_cache():
    cleaned_mb = 0.0
    try:
        font_cache_dir = os.path.join(
            os.environ.get("SYSTEMROOT", r"C:\Windows"),
            "ServiceProfiles", "LocalService", "AppData", "Local", "FontCache"
        )
        if not os.path.exists(font_cache_dir):
            return 0.0
        for f in os.listdir(font_cache_dir):
            if f.endswith(".dat") or f.startswith("FontCache"):
                fp = os.path.join(font_cache_dir, f)
                try:
                    size = os.path.getsize(fp)
                    os.remove(fp)
                    cleaned_mb += size / (1024 * 1024)
                except (PermissionError, OSError):
                    pass
        subprocess.run(
            ["net", "stop", "FontCache"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        subprocess.run(
            ["net", "start", "FontCache"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        cleaned_mb = round(cleaned_mb, 2)
        if cleaned_mb > 0:
            logger.info(f"Кэш шрифтов: освобождено {cleaned_mb} МБ")
        return cleaned_mb
    except Exception as e:
        logger.error(f"Ошибка очистки кэша шрифтов: {e}")
        return 0.0


def clean_prefetch():
    cleaned_mb = 0.0
    prefetch_dir = os.path.join(
        os.environ.get("SYSTEMROOT", r"C:\Windows"), "Prefetch"
    )
    if not os.path.exists(prefetch_dir):
        return 0.0
    try:
        for f in os.listdir(prefetch_dir):
            fp = os.path.join(prefetch_dir, f)
            if os.path.isfile(fp):
                try:
                    size = os.path.getsize(fp)
                    os.remove(fp)
                    cleaned_mb += size / (1024 * 1024)
                except (PermissionError, OSError):
                    pass
        cleaned_mb = round(cleaned_mb, 2)
        if cleaned_mb > 0:
            logger.info(f"Prefetch: освобождено {cleaned_mb} МБ")
        return cleaned_mb
    except Exception as e:
        logger.error(f"Ошибка очистки prefetch: {e}")
        return 0.0


def clean_all_system(config):
    results = {}
    if config.get("dns_cache_clean", True):
        results["dns"] = flush_dns_cache()
    if config.get("windows_update_cache_clean", False):
        results["windows_update_mb"] = clean_windows_update_cache()
    if config.get("thumbnail_cache_clean", True):
        results["thumbnail_mb"] = clean_thumbnail_cache()
    if config.get("font_cache_clean", False):
        results["font_mb"] = clean_font_cache()
    if config.get("prefetch_clean", True):
        results["prefetch_mb"] = clean_prefetch()
    return results
