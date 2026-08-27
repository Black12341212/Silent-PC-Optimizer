import time
import threading
from core.logger import logger

try:
    import ctypes
    import ctypes.wintypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class Benchmark:
    def __init__(self, config=None):
        self.config = config or {}
        self._running = False
        self.results = {}

    def run_full_benchmark(self, callback=None):
        self._running = True
        logger.info("Бенчмарк запущен")
        self.results = {}
        self.results["cpu"] = self._bench_cpu()
        if callback:
            callback("cpu", self.results["cpu"])
        self.results["ram"] = self._bench_ram()
        if callback:
            callback("ram", self.results["ram"])
        self.results["disk"] = self._bench_disk()
        if callback:
            callback("disk", self.results["disk"])
        self.results["score"] = self._calculate_score()
        self.results["timestamp"] = time.time()
        self._running = False
        logger.info(f"Бенчмарк завершён. Оценка: {self.results['score']}")
        return self.results

    def _bench_cpu(self):
        import psutil
        iterations = 5000000
        cpu_count = psutil.cpu_count()
        start = time.time()
        result = 0
        for i in range(iterations):
            result += i * i
        elapsed = time.time() - start
        ops_per_sec = iterations / elapsed if elapsed > 0 else 0
        start2 = time.time()
        data = list(range(100000))
        data.sort(reverse=True)
        sort_time = time.time() - start2
        import math
        start3 = time.time()
        for i in range(100000):
            math.sqrt(i) * math.log(i + 1)
        math_time = time.time() - start3
        return {
            "single_core_time": round(elapsed, 3),
            "ops_per_sec": round(ops_per_sec),
            "sort_time": round(sort_time, 3),
            "math_time": round(math_time, 3),
            "cpu_count": cpu_count,
        }

    def _bench_ram(self):
        import psutil
        mem = psutil.virtual_memory()
        size = self._ram_test_size()
        start = time.time()
        try:
            test_data = bytearray(size)
            test_data[:] = b"\xff"
            write_time = time.time() - start
            del test_data
        except MemoryError:
            write_time = 0
        import ctypes
        try:
            kernel32 = ctypes.windll.kernel32
            start2 = time.time()
            alloc_size = 50 * 1024 * 1024
            ptr = kernel32.VirtualAlloc(None, alloc_size, 0x3000, 0x40)
            if ptr:
                ctypes.memset(ptr, 0, alloc_size)
                alloc_time = time.time() - start2
                kernel32.VirtualFree(ptr, 0, 0x8000)
            else:
                alloc_time = 0
        except Exception:
            alloc_time = 0
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "write_time": round(write_time, 3),
            "alloc_time": round(alloc_time, 3),
        }

    def _ram_test_size(self):
        try:
            return int(self.config.get("benchmark_ram_size_mb", 100)) * 1024 * 1024
        except Exception:
            return 100 * 1024 * 1024

    def _bench_disk(self):
        import os
        import tempfile
        import psutil
        test_size = self._disk_test_size()
        data = os.urandom(test_size)
        test_file = os.path.join(tempfile.gettempdir(), "spo_bench_test.tmp")
        try:
            start = time.time()
            with open(test_file, "wb") as f:
                f.write(data)
            write_time = time.time() - start
            start = time.time()
            with open(test_file, "rb") as f:
                _ = f.read()
            read_time = time.time() - start
            write_speed = (test_size / write_time / (1024 * 1024)) if write_time > 0 else 0
            read_speed = (test_size / read_time / (1024 * 1024)) if read_time > 0 else 0
        except Exception:
            write_time = read_time = 0
            write_speed = read_speed = 0
        finally:
            try:
                os.remove(test_file)
            except Exception:
                pass
        drive = os.path.splitdrive(tempfile.gettempdir())[0] or "C:"
        disk = psutil.disk_usage(drive + "\\")
        return {
            "drive": drive,
            "write_mb_s": round(write_speed, 1),
            "read_mb_s": round(read_speed, 1),
            "write_time": round(write_time, 3),
            "read_time": round(read_time, 3),
            "total_gb": round(disk.total / (1024**3), 1),
            "used_percent": disk.percent,
        }

    def _disk_test_size(self):
        try:
            return int(self.config.get("benchmark_file_size_mb", 50)) * 1024 * 1024
        except Exception:
            return 50 * 1024 * 1024

    def _calculate_score(self):
        import psutil
        cpu = self.results.get("cpu", {})
        ram = self.results.get("ram", {})
        disk = self.results.get("disk", {})
        cpu_score = max(0, 100 - (cpu.get("single_core_time", 5) * 15))
        ram_score = min(100, (ram.get("total_gb", 8) / 32) * 100)
        disk_score = min(100, (disk.get("write_mb_s", 100) / 3000) * 100)
        score = int(cpu_score * 0.4 + ram_score * 0.3 + disk_score * 0.3)
        return max(0, min(100, score))

    @property
    def is_running(self):
        return self._running


def format_benchmark_result(results, lang="ru"):
    if not results:
        return "No results" if lang == "en" else "Нет результатов"
    score = results.get("score", 0)
    if score >= 80:
        grade = "Excellent" if lang == "en" else "Отлично"
    elif score >= 60:
        grade = "Good" if lang == "en" else "Хорошо"
    elif score >= 40:
        grade = "Average" if lang == "en" else "Средне"
    else:
        grade = "Low" if lang == "en" else "Низко"
    cpu = results.get("cpu", {})
    ram = results.get("ram", {})
    disk = results.get("disk", {})
    if lang == "ru":
        return (
            f"Оценка: {score}/100 ({grade})\n\n"
            f"CPU ({cpu.get('cpu_count', '?')} ядер):\n"
            f"  Время: {cpu.get('single_core_time', '?')} сек\n"
            f"  Ops/sec: {cpu.get('ops_per_sec', '?')}\n"
            f"  Сортировка: {cpu.get('sort_time', '?')} сек\n\n"
            f"RAM: {ram.get('total_gb', '?')} ГБ\n"
            f"  Запись: {ram.get('write_time', '?')} сек\n"
            f"  Аллокация: {ram.get('alloc_time', '?')} сек\n\n"
            f"Disk ({disk.get('drive', '?')}):\n"
            f"  Запись: {disk.get('write_mb_s', '?')} МБ/с\n"
            f"  Чтение: {disk.get('read_mb_s', '?')} МБ/с\n"
            f"  Занято: {disk.get('used_percent', '?')}%"
        )
    else:
        return (
            f"Score: {score}/100 ({grade})\n\n"
            f"CPU ({cpu.get('cpu_count', '?')} cores):\n"
            f"  Time: {cpu.get('single_core_time', '?')} sec\n"
            f"  Ops/sec: {cpu.get('ops_per_sec', '?')}\n"
            f"  Sort: {cpu.get('sort_time', '?')} sec\n\n"
            f"RAM: {ram.get('total_gb', '?')} GB\n"
            f"  Write: {ram.get('write_time', '?')} sec\n"
            f"  Alloc: {ram.get('alloc_time', '?')} sec\n\n"
            f"Disk ({disk.get('drive', '?')}):\n"
            f"  Write: {disk.get('write_mb_s', '?')} MB/s\n"
            f"  Read: {disk.get('read_mb_s', '?')} MB/s\n"
            f"  Used: {disk.get('used_percent', '?')}%"
        )
