#!/usr/bin/env python3
"""
Sea of Conquest Bot - Автоматизация прохождения обучения в игре Sea of Conquest.
Основной файл запуска приложения.
"""

import sys
import os
import traceback
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer

# Добавляем директорию проекта в sys.path
project_dir = Path(os.path.dirname(os.path.abspath(__file__)))
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from src.ui.main_window import MainWindow
from src.utils.logger import get_logger
from src.config.settings import ensure_dirs_exist

logger = get_logger("main")


def show_error_dialog(message):
    """
    Показать диалог с сообщением об ошибке.

    Args:
        message: Сообщение об ошибке
    """
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Ошибка")
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setText("Произошла непредвиденная ошибка:")
    msg_box.setInformativeText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Глобальный обработчик исключений для отображения ошибок в UI.

    Args:
        exc_type: Тип исключения
        exc_value: Значение исключения
        exc_traceback: Трассировка исключения
    """
    # Логирование ошибки
    logger.error("Непредвиденная ошибка:", exc_info=(exc_type, exc_value, exc_traceback))

    # Форматирование сообщения об ошибке
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    # Отображение диалога с ошибкой
    show_error_dialog(str(exc_value))

    # Вызов оригинального обработчика исключений
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def main():
    """
    Основная функция запуска приложения.
    """
    # Устанавливаем глобальный обработчик исключений
    sys.excepthook = exception_hook

    # Убеждаемся, что все необходимые директории существуют
    ensure_dirs_exist()

    # Создаем приложение
    app = QApplication(sys.argv)
    app.setApplicationName("Sea of Conquest Bot")

    # Попытка загрузки иконки
    try:
        icon_path = project_dir / "assets" / "icon.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
    except Exception as e:
        logger.warning(f"Не удалось загрузить иконку приложения: {e}")

    # Попытка отображения сплеш-скрина
    splash = None
    try:
        splash_path = project_dir / "assets" / "splash.png"
        if splash_path.exists():
            splash_pixmap = QPixmap(str(splash_path))
            splash = QSplashScreen(splash_pixmap, Qt.WindowType.WindowStaysOnTopHint)
            splash.show()
            splash.showMessage("Запуск приложения...",
                               alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                               color=Qt.GlobalColor.white)
            app.processEvents()
    except Exception as e:
        logger.warning(f"Не удалось показать сплеш-скрин: {e}")

    # Создаем главное окно с задержкой
    def show_main_window():
        try:
            window = MainWindow()
            window.show()

            if splash:
                splash.finish(window)
        except Exception as e:
            logger.error(f"Ошибка при создании главного окна: {e}", exc_info=True)
            if splash:
                splash.close()
            show_error_dialog(str(e))
            app.quit()

    # Запускаем с небольшой задержкой для отображения сплеш-скрина
    if splash:
        QTimer.singleShot(1500, show_main_window)
    else:
        show_main_window()

    # Запускаем главный цикл приложения
    sys.exit(app.exec())


if __name__ == "__main__":
    main()