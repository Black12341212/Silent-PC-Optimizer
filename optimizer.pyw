import psutil
import pygetwindow as gw
import os
import shutil
import time
import ctypes
import threading

# --- НАСТРОЙКИ ---
RAM_THRESHOLD = 85.0  # Процент RAM, при котором срабатывает очистка
CHECK_INTERVAL = 30   # Как часто проверять систему (в секундах)
BROWSER_NAMES = ["Chrome", "Firefox", "Edge", "Opera", "Yandex"]

def get_ram_usage():
    """Возвращает процент использования RAM."""
    return psutil.virtual_memory().percent

def get_free_ram_gb():
    """Возвращает кол-во свободной RAM в ГБ."""
    return round(psutil.virtual_memory().available / (1024 ** 3), 2)

def clean_temp_files():
    """
    Чистит системную папку Temp. 
    Возвращает количество удаленных файлов (эмуляция 'закрытых вкладок/мусора').
    """
    temp_folder = os.getenv('TEMP')
    deleted_count = 0
    bytes_cleared = 0
    
    if not temp_folder:
        return 0, 0

    for root, dirs, files in os.walk(temp_folder):
        for file in files:
            try:
                file_path = os.path.join(root, file)
                # Пытаемся удалить файл (если он не занят системой)
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                bytes_cleared += file_size
                deleted_count += 1
            except Exception:
                pass # Пропускаем занятые файлы
    
    return deleted_count, round(bytes_cleared / (1024 * 1024), 2) # MB

def optimize_windows():
    """
    Сворачивает неактивные окна браузеров для экономии ресурсов рендеринга.
    Возвращает количество свернутых окон.
    """
    minimized_count = 0
    try:
        active_window = gw.getActiveWindow()
        active_title = active_window.title if active_window else ""
        
        all_windows = gw.getAllWindows()
        
        for window in all_windows:
            # Если окно принадлежит браузеру и оно не активно прямо сейчас
            if any(browser in window.title for browser in BROWSER_NAMES) and window.title != active_title:
                if not window.isMinimized:
                    window.minimize()
                    minimized_count += 1
    except Exception as e:
        print(f"Error accessing windows: {e}")
        
    return minimized_count

def show_notification(title, message):
    """Показывает нативное Windows-уведомление (MessageBox)."""
    # 0x40000 = Поверх всех окон (MB_TOPMOST)
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x1000)

def optimization_task():
    """Основная логика очистки."""
    initial_ram_free = get_free_ram_gb()
    
    # 1. Чистим кэш/temp
    files_removed, cache_cleared_mb = clean_temp_files()
    
    # 2. Оптимизируем окна (эмуляция работы с вкладками)
    windows_optimized = optimize_windows()
    
    # Небольшая пауза, чтобы система обновила статистику памяти
    time.sleep(2)
    
    final_ram_free = get_free_ram_gb()
    freed_ram = round(final_ram_free - initial_ram_free, 2)
    
    # Если освободили меньше 0 (погрешность), ставим 0
    if freed_ram < 0: freed_ram = 0

    # Формируем отчет, если было что-то сделано
    if freed_ram > 0.1 or files_removed > 0:
        report = (
            f"Освободил: {freed_ram} ГБ RAM\n"
            f"Очищено кэша: {cache_cleared_mb} МБ\n"
            f"Свернуто фоновых окон: {windows_optimized}"
        )
        # Запускаем уведомление в отдельном потоке, чтобы не тормозить скрипт
        threading.Thread(target=show_notification, args=("Silent Optimizer", report)).start()

def main():
    print(f"Silent Optimizer запущен. Мониторинг RAM > {RAM_THRESHOLD}%")
    while True:
        try:
            current_ram = get_ram_usage()
            
            if current_ram > RAM_THRESHOLD:
                # Если система тормозит (RAM забита)
                optimization_task()
                # После очистки ждем дольше, чтобы не спамить (например, 5 минут)
                time.sleep(300) 
            else:
                time.sleep(CHECK_INTERVAL)
                
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()