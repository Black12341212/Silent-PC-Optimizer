import sys
import os
import tkinter as tk

if getattr(sys, 'frozen', False):
    _base = os.path.dirname(sys.executable)
else:
    _base = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _base)

from core.config import load_config, CONFIG_PATH
from core.logger import logger
from ui.tray import App


def main():
    logger.info("=" * 40)
    logger.info("Silent PC Optimizer v4.0 запускается...")

    config = load_config()

    try:
        app = App()
        app.run_with_tk()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
