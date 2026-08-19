import psutil
from core.logger import logger


def get_heavy_processes(config):
    killer_cfg = config.get("background_process_killer", {})
    if not killer_cfg.get("enabled", False):
        return []

    threshold_mb = killer_cfg.get("ram_threshold_mb", 500)
    whitelist = [name.lower() for name in killer_cfg.get("whitelist", [])]
    heavy = []

    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            info = proc.info
            name = info["name"]
            if name.lower() in whitelist:
                continue

            mem_mb = info["memory_info"].rss / (1024 * 1024)
            if mem_mb >= threshold_mb:
                heavy.append({
                    "pid": info["pid"],
                    "name": name,
                    "ram_mb": round(mem_mb, 1)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    heavy.sort(key=lambda p: p["ram_mb"], reverse=True)
    return heavy


def kill_processes(process_list):
    killed = 0
    for proc_info in process_list:
        try:
            proc = psutil.Process(proc_info["pid"])
            proc.terminate()
            killed += 1
            logger.info(f"Завершён процесс: {proc_info['name']} (PID {proc_info['pid']}, {proc_info['ram_mb']} МБ)")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Не удалось завершить {proc_info['name']}: {e}")
    return killed
