import os
import sys
import logging
import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Глобальная конфигурация логгера
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 МБ
BACKUP_COUNT = 5  # Количество файлов для ротации

# Директория для сохранения логов
LOG_DIR = Path("logs")


def setup_logger():
    """
    Настройка глобального логгера.
    Создает директорию для логов, если её нет.
    """
    if not LOG_DIR.exists():
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Формат имени файла логов с датой
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"sea_conquest_bot_{today}.log"

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Обработчик для вывода в файл с ротацией
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    return root_logger


# Глобальный логгер
_root_logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """
    Получение настроенного логгера для модуля.

    Args:
        name: Имя модуля или логгера

    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)


def set_log_level(level: int or str):
    """
    Установка уровня логирования.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    _root_logger.setLevel(level)
    for handler in _root_logger.handlers:
        handler.setLevel(level)

    _root_logger.info(f"Установлен уровень логирования: {logging.getLevelName(level)}")


class LoggerHandler:
    """
    Обработчик для захвата и перенаправления логов в UI.
    """

    def __init__(self, callback=None):
        """
        Инициализация обработчика логов.

        Args:
            callback: Функция обратного вызова для обработки логов в UI
        """
        self.callback = callback
        self.level = logging.INFO
        self.formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)

    def emit(self, record):
        """
        Обработка записи лога.

        Args:
            record: Запись лога
        """
        try:
            msg = self.formatter.format(record)
            if self.callback:
                self.callback(msg, record.levelno)
        except Exception:
            pass

    def handle(self, record):
        """
        Обработка записи лога.

        Args:
            record: Запись лога

        Returns:
            True если запись обработана, иначе False
        """
        if record.levelno >= self.level:
            self.emit(record)
            return True
        return False

    def setLevel(self, level):
        """
        Установка уровня логирования.

        Args:
            level: Уровень логирования
        """
        self.level = level

    def setFormatter(self, formatter):
        """
        Установка форматера логов.

        Args:
            formatter: Форматер логов
        """
        self.formatter = formatter


def add_ui_logger(callback):
    """
    Добавление обработчика логов для UI.

    Args:
        callback: Функция обратного вызова для обработки логов в UI

    Returns:
        Созданный обработчик логов
    """
    handler = LoggerHandler(callback)
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    _root_logger.addHandler(handler)
    return handler


def remove_ui_logger(handler):
    """
    Удаление обработчика логов для UI.

    Args:
        handler: Обработчик логов для удаления
    """
    if handler in _root_logger.handlers:
        _root_logger.removeHandler(handler)