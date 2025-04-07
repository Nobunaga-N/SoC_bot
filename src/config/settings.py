"""
Модуль настроек приложения.
Содержит конфигурацию и константы для работы приложения.
"""

import os
import json
from pathlib import Path
from ..utils.logger import get_logger, set_log_level
import logging

logger = get_logger(__name__)

# Базовые пути
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"

# Настройки игры
GAME_PACKAGE = "com.seaofconquest.global"
GAME_ACTIVITY = "com.kingsgroup.mo.KGUnityPlayerActivity"

# Мапинг сезонов на диапазоны серверов
SEASON_TO_SERVER_RANGES = {
    "S1": (577, 600),
    "S2": (541, 576),
    "S3": (505, 540),
    "S4": (481, 504),
    "S5": (433, 480),
    "X1": (409, 432),
    "X2": (266, 407),
    "X3": (1, 264),
}


# Обратное отображение: сервер -> сезон
def get_season_for_server(server_number):
    """
    Определение сезона по номеру сервера.

    Args:
        server_number: Номер сервера

    Returns:
        Название сезона или None, если сезон не найден
    """
    for season, (start, end) in SEASON_TO_SERVER_RANGES.items():
        if start <= server_number <= end:
            return season
    return None


# Настройки логирования
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# Создание необходимых директорий
def ensure_dirs_exist():
    """
    Убедиться, что все необходимые директории существуют.
    Создает их, если они отсутствуют.
    """
    dirs = [ASSETS_DIR, IMAGES_DIR, CONFIG_DIR, LOGS_DIR]
    for directory in dirs:
        if not directory.exists():
            logger.info(f"Создание директории: {directory}")
            directory.mkdir(parents=True, exist_ok=True)


# Настройки для координат
class Coordinates:
    """Класс с константами координат для действий в игре."""

    # Координаты различных элементов UI
    PROFILE_ICON = (54, 55)
    SETTINGS_ICON = (1073, 35)
    CHARACTERS_ICON = (638, 319)
    ADD_CHARACTER_ICON = (270, 184)

    # Координаты для скролла
    SEASON_SCROLL_START = (257, 353)
    SEASON_SCROLL_END = (254, 187)

    SERVER_SCROLL_START = (778, 567)
    SERVER_SCROLL_END = (778, 130)

    # Координаты для свайпа
    COMPLEX_SWIPE_POINTS = [
        (154, 351),
        (288, 355),
        (507, 353),
        (627, 351)
    ]


# Пользовательские настройки, которые можно сохранять
class UserSettings:
    """Класс для управления пользовательскими настройками."""

    def __init__(self):
        self.settings_file = CONFIG_DIR / "user_settings.json"
        self.settings = {
            "ldplayer_path": "",
            "server_range": (1, 10),
            "selected_emulators": [],
            "theme": "light",
            "log_level": "INFO"
        }
        self.load_settings()

    def load_settings(self):
        """
        Загрузка настроек из файла.
        """
        if not self.settings_file.exists():
            logger.info("Файл настроек не найден, используются настройки по умолчанию")
            return

        try:
            with open(self.settings_file, "r", encoding="utf-8") as file:
                saved_settings = json.load(file)
                self.settings.update(saved_settings)

                # Установка уровня логирования
                if "log_level" in saved_settings:
                    set_log_level(saved_settings["log_level"])

                logger.info("Настройки успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроек: {e}")

    def save_settings(self):
        """
        Сохранение настроек в файл.
        """
        ensure_dirs_exist()

        try:
            with open(self.settings_file, "w", encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4)
            logger.info("Настройки успешно сохранены")
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {e}")

    def get(self, key, default=None):
        """
        Получение значения настройки.

        Args:
            key: Ключ настройки
            default: Значение по умолчанию

        Returns:
            Значение настройки или значение по умолчанию
        """
        return self.settings.get(key, default)

    def set(self, key, value):
        """
        Установка значения настройки.

        Args:
            key: Ключ настройки
            value: Новое значение
        """
        self.settings[key] = value
        self.save_settings()


# Инициализация
ensure_dirs_exist()
user_settings = UserSettings()

# Установка уровня логирования из настроек
set_log_level(user_settings.get("log_level", "INFO"))