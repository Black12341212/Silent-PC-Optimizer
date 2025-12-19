import psutil
import pygetwindow as gw
import os
import time
import threading
import pystray
from PIL import Image, ImageDraw
import ctypes

# --- НАСТРОЙКИ ---
RAM_THRESHOLD = 85.0
CHECK_INTERVAL = 30
BROWSER_NAMES = ["Chrome", "Firefox", "Edge", "Opera", "Yandex"]

# Глобальные флаги управления
running = True
auto_mode = True
icon = None

def create_image():
    """Генерирует простую иконку (зеленый круг) для трея."""
    width = 64
    height = 64
    color1 = (0, 128, 0)
    color2 = (255, 255, 255)
    
    image = Image.new('RGB', (width, height), color2)
    dc = ImageDraw.Draw(image)
    dc.ellipse((0, 0, width, height), fill=color1)
    return image

def get_ram_usage():
    return psutil.virtual_memory().percent

def get_free_ram_gb():
    return round(psutil.virtual_memory().available / (1024 ** 3), 2)

def clean_temp_files():
    temp_folder = os.getenv('TEMP')
    deleted_count = 0
    bytes_cleared = 0
    if not temp_folder: return 0, 0
    
    for root, dirs, files in os.walk(temp_folder):
        for file in files:
            try:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                bytes_cleared += file_size
                deleted_count += 1
            except Exception: pass
    return deleted_count, round(bytes_cleared / (1024 * 1024), 2)

def optimize_windows():
    minimized_count = 0
    try:
        active_window = gw.getActiveWindow()
        active_title = active_window.title if active_window else ""
        for window in gw.getAllWindows():
            if any(browser in window.title for browser in BROWSER_NAMES) and window.title != active_title:
                if not window.isMinimized:
                    window.minimize()
                    minimized_count += 1
    except Exception: pass
    return minimized_count

def perform_optimization(manual=False):
    """Функция очистки. manual=True показывает уведомление даже если мало очистили."""
    initial_ram = get_free_ram_gb()
    files, cache_mb = clean_temp_files()
    wins = optimize_windows()
    time.sleep(1)
    final_ram = get_free_ram_gb()
    freed = round(final_ram - initial_ram, 2)
    if freed < 0: freed = 0

    if manual or freed > 0.1 or files > 0:
        msg = f"Освобождено RAM: {freed} ГБ\nКэш: {cache_mb} МБ\nСвернуто окон: {wins}"
        if icon:
            icon.notify(msg, title="Silent Optimizer")

def background_loop():
    """Фоновый поток мониторинга."""
    global running, auto_mode
    print("Мониторинг запущен")
    
    while running:
        if auto_mode:
            ram = get_ram_usage()
            if ram > RAM_THRESHOLD:
                perform_optimization(manual=False)
                time.sleep(300) # Пауза после очистки 5 минут
        
        # Проверяем каждые CHECK_INTERVAL секунд
        for _ in range(CHECK_INTERVAL):
            if not running: break
            time.sleep(1)

# --- Управление треем ---

def on_clicked(icon, item):
    """Обработчик нажатий меню."""
    global running, auto_mode
    
    if str(item) == "Выход":
        running = False
        icon.stop()
    elif str(item) == "Оптимизировать сейчас":
        threading.Thread(target=perform_optimization, args=(True,)).start()
    elif str(item) == "Авто-режим":
        auto_mode = not auto_mode
        # Обновляем состояние галочки (визуально pystray сам не обновляет, нужен пересоздание, но оставим простым переключением)
        state_text = "ВКЛ" if auto_mode else "ВЫКЛ"
        icon.notify(f"Автоматическая очистка: {state_text}", title="Настройки")

def setup_tray():
    global icon
    image = create_image()
    menu = pystray.Menu(
        pystray.MenuItem("Оптимизировать сейчас", on_clicked),
        pystray.MenuItem("Авто-режим", on_clicked, checked=lambda item: auto_mode),
        pystray.MenuItem("Выход", on_clicked)
    )
    
    icon = pystray.Icon("SilentOptimizer", image, "PC Optimizer", menu)
    
    # Запускаем фоновый мониторинг в отдельном потоке
    threading.Thread(target=background_loop, daemon=True).start()
    
    icon.notify("Работает в фоне. Правый клик для меню.", title="Silent Optimizer v2.0")
    icon.run()

if __name__ == "__main__":
    setup_tray()
