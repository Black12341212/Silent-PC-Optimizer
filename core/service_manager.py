import subprocess
from core.logger import logger


def _run_sc(args, timeout=30):
    cmd = ["sc"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=0x08000000
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1


def get_service_status(service_name):
    stdout, stderr, code = _run_sc(["query", service_name])
    if code != 0:
        return None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("STATE"):
            parts = line.split()
            if len(parts) >= 4:
                return parts[3]
    return None


def get_all_services():
    services = []
    try:
        import psutil
        for svc in psutil.win_service_iter():
            try:
                info = svc.as_dict()
                services.append({
                    "name": info.get("name", ""),
                    "display_name": info.get("display_name", ""),
                    "status": info.get("status", "unknown"),
                    "start_type": info.get("start_type", "unknown"),
                    "pid": info.get("pid", 0),
                })
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Ошибка получения списка служб: {e}")
    return services


def disable_service(service_name):
    status = get_service_status(service_name)
    if status is None:
        logger.warning(f"Служба {service_name} не найдена")
        return False, f"Service '{service_name}' not found"
    if status == "RUNNING":
        _run_sc(["stop", service_name])
    stdout, stderr, code = _run_sc(["config", service_name, "start=", "disabled"])
    if code == 0:
        logger.info(f"Служба {service_name} отключена")
        return True, f"Service '{service_name}' disabled"
    else:
        logger.warning(f"Ошибка отключения {service_name}: {stderr}")
        return False, stderr


def enable_service(service_name):
    stdout, stderr, code = _run_sc(["config", service_name, "start=", "demand"])
    if code == 0:
        logger.info(f"Служба {service_name} переведена в ручной запуск")
        return True, f"Service '{service_name}' set to manual"
    else:
        logger.warning(f"Ошибка включения {service_name}: {stderr}")
        return False, stderr


def start_service(service_name):
    stdout, stderr, code = _run_sc(["start", service_name])
    if code == 0:
        logger.info(f"Служба {service_name} запущена")
        return True, f"Service '{service_name}' started"
    else:
        return False, stderr


def stop_service(service_name):
    stdout, stderr, code = _run_sc(["stop", service_name])
    if code == 0:
        logger.info(f"Служба {service_name} остановлена")
        return True, f"Service '{service_name}' stopped"
    else:
        return False, stderr


def apply_service_config(config):
    svc_cfg = config.get("service_management", {})
    if not svc_cfg.get("enabled", False):
        return {}
    disable_list = svc_cfg.get("disable_list", [])
    results = {}
    for svc_name in disable_list:
        success, msg = disable_service(svc_name)
        results[svc_name] = {"success": success, "message": msg}
    return results


def get_service_info(service_name):
    status = get_service_status(service_name)
    stdout, _, _ = _run_sc(["qc", service_name])
    start_type = "unknown"
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("START_TYPE"):
            parts = line.split(":")
            if len(parts) >= 2:
                start_type = parts[1].strip()
    return {
        "name": service_name,
        "status": status or "not_found",
        "start_type": start_type,
    }
