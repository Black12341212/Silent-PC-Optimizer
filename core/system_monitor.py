import time
import threading
import html
import psutil
from collections import deque
from core.logger import logger

try:
    import ctypes
    import ctypes.wintypes
    HAS_CTYPES = True
except ImportError:
    HAS_CTYPES = False

try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False

_WMI_INSTANCE = None


class SystemMonitor:
    def __init__(self, max_points=120):
        self.max_points = max_points
        self.cpu_history = deque(maxlen=max_points)
        self.ram_history = deque(maxlen=max_points)
        self.disk_io_history = deque(maxlen=max_points)
        self.net_history = deque(maxlen=max_points)
        self.temp_history = deque(maxlen=max_points)
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._prev_net = None
        self._prev_disk_io = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _monitor_loop(self):
        while self._running:
            try:
                self._record_snapshot()
            except Exception as e:
                logger.debug(f"Ошибка мониторинга: {e}")
            time.sleep(2)

    def _record_snapshot(self):
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_counters = psutil.net_io_counters()
        net_io = net_counters.bytes_sent + net_counters.bytes_recv
        now = time.time()

        net_speed = 0.0
        if self._prev_net is not None:
            elapsed = now - self._prev_net[1]
            if elapsed > 0:
                net_speed = (net_io - self._prev_net[0]) / elapsed / 1024
        self._prev_net = (net_io, now)

        disk_speed = 0.0
        if disk_io and self._prev_disk_io is not None:
            elapsed = now - self._prev_disk_io[1]
            if elapsed > 0:
                read_speed = (disk_io.read_bytes - self._prev_disk_io[0][0]) / elapsed / 1024
                write_speed = (disk_io.write_bytes - self._prev_disk_io[0][1]) / elapsed / 1024
                disk_speed = read_speed + write_speed
        if disk_io:
            self._prev_disk_io = ((disk_io.read_bytes, disk_io.write_bytes), now)

        temp = self._get_cpu_temperature()

        snapshot = {
            "time": now,
            "cpu_percent": cpu,
            "ram_percent": ram.percent,
            "ram_used_gb": round((ram.total - ram.available) / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_free_gb": round(ram.available / (1024**3), 2),
            "net_speed_kbps": round(net_speed, 1),
            "disk_speed_kbps": round(disk_speed, 1),
            "temperature": temp,
        }

        with self._lock:
            self.cpu_history.append(snapshot)
            self.ram_history.append(snapshot)
            self.net_history.append(snapshot)
            self.disk_io_history.append(snapshot)
            if temp is not None:
                self.temp_history.append(snapshot)

    def _get_cpu_temperature(self):
        global _WMI_INSTANCE
        if not HAS_WMI:
            return None
        try:
            if _WMI_INSTANCE is None:
                _WMI_INSTANCE = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            w = _WMI_INSTANCE
            sensors = w.Sensor()
            for sensor in sensors:
                if sensor.SensorType == "Temperature" and "CPU" in sensor.Name:
                    return round(float(sensor.Value), 1)
        except Exception:
            pass
        try:
            if _WMI_INSTANCE is None:
                _WMI_INSTANCE = wmi.WMI(namespace="root\\WMI")
            w = _WMI_INSTANCE
            temps = w.MSAcpi_ThermalZoneTemperature()
            if temps:
                return round((temps[0].CurrentTemperature / 10.0) - 273.15, 1)
        except Exception:
            pass
        return None

    def get_snapshot(self):
        with self._lock:
            if self.cpu_history:
                return self.cpu_history[-1]
            return self._empty_snapshot()

    def get_cpu_history(self):
        with self._lock:
            return list(self.cpu_history)

    def get_ram_history(self):
        with self._lock:
            return list(self.ram_history)

    def get_net_history(self):
        with self._lock:
            return list(self.net_history)

    def get_disk_history(self):
        with self._lock:
            return list(self.disk_io_history)

    def get_temp_history(self):
        with self._lock:
            return list(self.temp_history)

    def _empty_snapshot(self):
        return {
            "time": time.time(),
            "cpu_percent": 0,
            "ram_percent": 0,
            "ram_used_gb": 0,
            "ram_total_gb": 0,
            "ram_free_gb": 0,
            "net_speed_kbps": 0,
            "disk_speed_kbps": 0,
            "temperature": None,
        }


def get_top_io_processes(top_n=10):
    procs = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                p = psutil.Process(proc.info["pid"])
                io = p.io_counters()
                total = io.read_bytes + io.write_bytes
                procs.append({
                    "pid": proc.info["pid"],
                    "name": proc.info["name"],
                    "read_mb": round(io.read_bytes / (1024 * 1024), 2),
                    "write_mb": round(io.write_bytes / (1024 * 1024), 2),
                    "total_mb": round(total / (1024 * 1024), 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    procs.sort(key=lambda p: p["total_mb"], reverse=True)
    return procs[:top_n]


def send_alert(message, config):
    tg_cfg = config.get("telegram_alerts", {})
    if tg_cfg.get("enabled", False):
        _send_telegram(message, tg_cfg)
    email_cfg = config.get("email_alerts", {})
    if email_cfg.get("enabled", False):
        _send_email(message, email_cfg)


def _escape_html(text):
    return html.escape(str(text))


def _send_telegram(message, cfg):
    try:
        import urllib.request
        import urllib.parse
        bot_token = cfg.get("bot_token", "")
        chat_id = cfg.get("chat_id", "")
        if not bot_token or not chat_id:
            return
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        safe_message = _escape_html(f"⚠️ Silent PC Optimizer\n\n{message}")
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": safe_message,
            "parse_mode": "HTML"
        }).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
        logger.info("Telegram-уведомление отправлено")
    except Exception as e:
        logger.error(f"Ошибка Telegram: {e}")


def _send_email(message, cfg):
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(message)
        msg["Subject"] = "Silent PC Optimizer Alert"
        msg["From"] = cfg.get("email", "")
        msg["To"] = cfg.get("recipient", "")
        server = smtplib.SMTP(cfg.get("smtp_server", ""), cfg.get("smtp_port", 587))
        server.starttls()
        server.login(cfg.get("email", ""), cfg.get("password", ""))
        server.send_message(msg)
        server.quit()
        logger.info("Email-уведомление отправлено")
    except Exception as e:
        logger.error(f"Ошибка email: {e}")


def check_alerts(monitor, config):
    snapshot = monitor.get_snapshot()
    thresholds = config.get("alert_thresholds", {})
    alerts = []
    if snapshot["cpu_percent"] > thresholds.get("cpu_percent", 90):
        alerts.append(f"CPU: {snapshot['cpu_percent']}%")
    if snapshot["ram_percent"] > thresholds.get("ram_percent", 90):
        alerts.append(f"RAM: {snapshot['ram_percent']}%")
    if snapshot.get("temperature") and snapshot["temperature"] > thresholds.get("temperature_celsius", 85):
        alerts.append(f"Temp: {snapshot['temperature']}°C")
    if alerts:
        msg = "Критическая нагрузка:\n" + "\n".join(alerts)
        send_alert(msg, config)
    return alerts
