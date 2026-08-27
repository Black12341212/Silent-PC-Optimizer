import json
import os
import time
import threading
from core.config import HISTORY_PATH
from core.logger import logger

_history_lock = threading.Lock()


def _load_history():
    if not os.path.exists(HISTORY_PATH):
        return {"optimizations": [], "daily_stats": {}}
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"optimizations": [], "daily_stats": {}}


def _save_history(data):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_optimization(freed_gb, files_deleted, cache_mb, details=None):
    with _history_lock:
        data = _load_history()
        entry = {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "freed_gb": freed_gb,
            "files_deleted": files_deleted,
            "cache_mb": cache_mb,
            "details": details or {},
        }
        data["optimizations"].append(entry)
        today = time.strftime("%Y-%m-%d")
        if today not in data["daily_stats"]:
            data["daily_stats"][today] = {
                "count": 0,
                "total_freed_gb": 0.0,
                "total_files": 0,
                "total_cache_mb": 0.0,
            }
        ds = data["daily_stats"][today]
        ds["count"] += 1
        ds["total_freed_gb"] = round(ds["total_freed_gb"] + freed_gb, 3)
        ds["total_files"] += files_deleted
        ds["total_cache_mb"] = round(ds["total_cache_mb"] + cache_mb, 2)
        if len(data["optimizations"]) > 1000:
            data["optimizations"] = data["optimizations"][-500:]
        _save_history(data)
        logger.info(
            f"История: записана оптимизация — {freed_gb} ГБ, "
            f"{files_deleted} файлов, {cache_mb} МБ кэша"
        )


def get_history(limit=50):
    data = _load_history()
    return data["optimizations"][-limit:]


def get_daily_stats():
    data = _load_history()
    return data.get("daily_stats", {})


def get_summary(period="week"):
    data = _load_history()
    now = time.time()
    if period == "day":
        cutoff = now - 86400
    elif period == "week":
        cutoff = now - 604800
    elif period == "month":
        cutoff = now - 2592000
    else:
        cutoff = 0
    total_freed = 0.0
    total_files = 0
    total_cache = 0.0
    count = 0
    for entry in data["optimizations"]:
        if entry.get("timestamp", 0) >= cutoff:
            total_freed += entry.get("freed_gb", 0)
            total_files += entry.get("files_deleted", 0)
            total_cache += entry.get("cache_mb", 0)
            count += 1
    return {
        "period": period,
        "optimizations": count,
        "total_freed_gb": round(total_freed, 3),
        "total_files": total_files,
        "total_cache_mb": round(total_cache, 2),
    }


def clear_history():
    with _history_lock:
        _save_history({"optimizations": [], "daily_stats": {}})
    logger.info("История оптимизаций очищена")
