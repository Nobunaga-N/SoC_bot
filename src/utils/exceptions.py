"""
Модуль с пользовательскими исключениями для проекта.
"""


class BotError(Exception):
    """Базовый класс для всех исключений бота."""
    pass


class EmulatorError(BotError):
    """Исключение, связанное с проблемами эмулятора."""
    pass


class ADBError(BotError):
    """Исключение, связанное с проблемами ADB."""
    pass


class ImageError(BotError):
    """Исключение, связанное с проблемами обработки изображений."""
    pass


class TutorialError(BotError):
    """Исключение, связанное с проблемами выполнения туториала."""

    def __init__(self, message, step_id=None, step_name=None):
        """
        Инициализация исключения.

        Args:
            message: Сообщение об ошибке
            step_id: ID шага, на котором произошла ошибка
            step_name: Название шага, на котором произошла ошибка
        """
        self.step_id = step_id
        self.step_name = step_name
        super().__init__(message)


class ConfigError(BotError):
    """Исключение, связанное с проблемами конфигурации."""
    pass


class TimeoutError(BotError):
    """Исключение, связанное с превышением времени ожидания."""

    def __init__(self, message, wait_time=None, action=None):
        """
        Инициализация исключения.

        Args:
            message: Сообщение об ошибке
            wait_time: Время ожидания, которое было превышено
            action: Действие, которое вызвало таймаут
        """
        self.wait_time = wait_time
        self.action = action
        super().__init__(message)


class ServerError(BotError):
    """Исключение, связанное с проблемами выбора сервера."""

    def __init__(self, message, server_number=None, season=None):
        """
        Инициализация исключения.

        Args:
            message: Сообщение об ошибке
            server_number: Номер сервера, который вызвал ошибку
            season: Сезон, в котором произошла ошибка
        """
        self.server_number = server_number
        self.season = season
        super().__init__(message)