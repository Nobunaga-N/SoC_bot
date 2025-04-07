import os
import re
import subprocess
import time
from typing import List, Dict, Optional
from threading import Lock
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EmulatorManager:
    """
    Класс для управления несколькими эмуляторами LDPlayer.
    Обеспечивает функционал для получения списка эмуляторов,
    запуска, остановки и управления ими.
    """

    def __init__(self, ldplayer_path: str = None):
        """
        Инициализация менеджера эмуляторов.

        Args:
            ldplayer_path: Путь к директории с LDPlayer
        """
        self._lock = Lock()

        # Пытаемся определить путь к LDPlayer автоматически
        if ldplayer_path is None:
            default_paths = [
                "C:/Program Files/LDPlayer/LDPlayer9",
                "C:/LDPlayer/LDPlayer9",
                "D:/LDPlayer/LDPlayer9"
            ]

            for path in default_paths:
                if os.path.exists(path):
                    ldplayer_path = path
                    break

        self.ldplayer_path = ldplayer_path
        self.ldconsole_path = os.path.join(ldplayer_path, "ldconsole.exe") if ldplayer_path else None
        self.active_emulators = {}  # {emulator_id: emulator_index}

        if self.ldplayer_path and not os.path.exists(self.ldconsole_path):
            logger.error(f"ldconsole.exe не найден по пути: {self.ldconsole_path}")

        logger.info(f"Инициализация менеджера эмуляторов. Путь к LDPlayer: {ldplayer_path}")

    def set_ldplayer_path(self, path: str) -> bool:
        """
        Установка пути к директории LDPlayer.

        Args:
            path: Путь к директории с LDPlayer

        Returns:
            True если путь валидный, иначе False
        """
        with self._lock:
            if not os.path.exists(path):
                logger.error(f"Путь не существует: {path}")
                return False

            ldconsole = os.path.join(path, "ldconsole.exe")
            if not os.path.exists(ldconsole):
                logger.error(f"ldconsole.exe не найден в указанной директории: {path}")
                return False

            self.ldplayer_path = path
            self.ldconsole_path = ldconsole
            logger.info(f"Установлен путь к LDPlayer: {path}")
            return True

    def execute_ldconsole(self, command: str) -> str:
        """
        Выполнение команды ldconsole.

        Args:
            command: Команда для ldconsole

        Returns:
            Результат выполнения команды
        """
        if not self.ldconsole_path:
            logger.error("Путь к ldconsole.exe не установлен")
            return ""

        try:
            full_command = f'"{self.ldconsole_path}" {command}'
            logger.debug(f"Выполнение команды LDConsole: {full_command}")

            result = subprocess.check_output(full_command, shell=True, stderr=subprocess.STDOUT)
            return result.decode('utf-8', errors='ignore').strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка выполнения команды LDConsole: {e}")
            return e.output.decode('utf-8', errors='ignore').strip()

    def list_emulators(self) -> List[Dict[str, str]]:
        """
        Получение списка всех эмуляторов LDPlayer.

        Returns:
            Список эмуляторов в формате [{index: "0", name: "LDPlayer-0", status: "running"}, ...]
        """
        with self._lock:
            result = self.execute_ldconsole("list2")
            emulators = []

            for line in result.splitlines():
                if not line.strip():
                    continue

                parts = line.split(',')
                if len(parts) >= 3:
                    emulator = {
                        "index": parts[0],
                        "name": parts[1],
                        "status": "running" if parts[2] == "1" else "stopped"
                    }
                    emulators.append(emulator)

            logger.info(f"Найдено {len(emulators)} эмуляторов")
            return emulators

    def get_adb_devices(self) -> Dict[str, str]:
        """
        Получение списка устройств ADB.

        Returns:
            Словарь {emulator_id: emulator_status}
        """
        try:
            result = subprocess.check_output("adb devices", shell=True)
            result = result.decode('utf-8').strip()

            devices = {}
            for line in result.splitlines()[1:]:  # Пропускаем заголовок
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    devices[device_id] = status

            logger.debug(f"ADB устройства: {devices}")
            return devices
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка получения списка ADB устройств: {e}")
            return {}

    def get_emulator_adb_id(self, emulator_index: int) -> Optional[str]:
        """
        Получение ADB ID для эмулятора LDPlayer по его индексу.

        Args:
            emulator_index: Индекс эмулятора

        Returns:
            ADB ID эмулятора или None
        """
        with self._lock:
            if str(emulator_index) in self.active_emulators.values():
                # Если уже знаем ID, вернем его
                for adb_id, idx in self.active_emulators.items():
                    if idx == str(emulator_index):
                        return adb_id

            # Получаем информацию о порте эмулятора
            result = self.execute_ldconsole(f"adb --index {emulator_index} --command \"get-serialno\"")

            if result:
                # Типичный формат: emulator-5554 или 127.0.0.1:5555
                device_id = result.strip()
                self.active_emulators[device_id] = str(emulator_index)
                logger.info(f"Получен ADB ID для эмулятора {emulator_index}: {device_id}")
                return device_id

            logger.error(f"Не удалось получить ADB ID для эмулятора {emulator_index}")
            return None

    def start_emulator(self, emulator_index: int) -> bool:
        """
        Запуск эмулятора LDPlayer по его индексу.

        Args:
            emulator_index: Индекс эмулятора

        Returns:
            True если эмулятор запущен успешно, иначе False
        """
        with self._lock:
            logger.info(f"Запуск эмулятора с индексом {emulator_index}")

            # Проверяем, не запущен ли уже эмулятор
            emulators = self.list_emulators()
            for emu in emulators:
                if emu["index"] == str(emulator_index) and emu["status"] == "running":
                    logger.info(f"Эмулятор {emulator_index} уже запущен")
                    return True

            # Запускаем эмулятор
            result = self.execute_ldconsole(f"launch --index {emulator_index}")

            # Ждем запуска эмулятора
            max_attempts = 30
            for attempt in range(max_attempts):
                time.sleep(2)  # Ждем 2 секунды между проверками

                emulators = self.list_emulators()
                for emu in emulators:
                    if emu["index"] == str(emulator_index) and emu["status"] == "running":
                        logger.info(f"Эмулятор {emulator_index} успешно запущен")
                        return True

                logger.debug(f"Ожидание запуска эмулятора {emulator_index}, попытка {attempt + 1}/{max_attempts}")

            logger.error(f"Не удалось запустить эмулятор {emulator_index} после {max_attempts} попыток")
            return False

    def stop_emulator(self, emulator_index: int) -> bool:
        """
        Остановка эмулятора LDPlayer по его индексу.

        Args:
            emulator_index: Индекс эмулятора

        Returns:
            True если эмулятор остановлен успешно, иначе False
        """
        with self._lock:
            logger.info(f"Остановка эмулятора с индексом {emulator_index}")

            # Проверяем, запущен ли эмулятор
            emulators = self.list_emulators()
            is_running = False

            for emu in emulators:
                if emu["index"] == str(emulator_index):
                    if emu["status"] == "stopped":
                        logger.info(f"Эмулятор {emulator_index} уже остановлен")
                        return True
                    is_running = True
                    break

            if not is_running:
                logger.warning(f"Эмулятор {emulator_index} не найден")
                return False

            # Останавливаем эмулятор
            result = self.execute_ldconsole(f"quit --index {emulator_index}")

            # Ждем остановки эмулятора
            max_attempts = 15
            for attempt in range(max_attempts):
                time.sleep(1)  # Ждем 1 секунду между проверками

                emulators = self.list_emulators()
                for emu in emulators:
                    if emu["index"] == str(emulator_index) and emu["status"] == "stopped":
                        logger.info(f"Эмулятор {emulator_index} успешно остановлен")

                        # Удаляем из словаря активных эмуляторов
                        for adb_id, idx in list(self.active_emulators.items()):
                            if idx == str(emulator_index):
                                del self.active_emulators[adb_id]

                        return True

                logger.debug(f"Ожидание остановки эмулятора {emulator_index}, попытка {attempt + 1}/{max_attempts}")

            logger.error(f"Не удалось остановить эмулятор {emulator_index} после {max_attempts} попыток")
            return False

    def restart_emulator(self, emulator_index: int) -> bool:
        """
        Перезапуск эмулятора LDPlayer.

        Args:
            emulator_index: Индекс эмулятора

        Returns:
            True если эмулятор перезапущен успешно, иначе False
        """
        with self._lock:
            logger.info(f"Перезапуск эмулятора с индексом {emulator_index}")

            # Останавливаем эмулятор
            if not self.stop_emulator(emulator_index):
                logger.error(f"Не удалось остановить эмулятор {emulator_index} для перезапуска")
                return False

            # Ждем 5 секунд
            time.sleep(5)

            # Запускаем эмулятор
            if not self.start_emulator(emulator_index):
                logger.error(f"Не удалось запустить эмулятор {emulator_index} после остановки")
                return False

            logger.info(f"Эмулятор {emulator_index} успешно перезапущен")
            return True

    def install_app(self, emulator_index: int, apk_path: str) -> bool:
        """
        Установка приложения на эмулятор.

        Args:
            emulator_index: Индекс эмулятора
            apk_path: Путь к APK файлу

        Returns:
            True если приложение установлено успешно, иначе False
        """
        with self._lock:
            if not os.path.exists(apk_path):
                logger.error(f"APK файл не найден: {apk_path}")
                return False

            logger.info(f"Установка приложения {apk_path} на эмулятор {emulator_index}")
            result = self.execute_ldconsole(f"installapp --index {emulator_index} --filename \"{apk_path}\"")

            if "success" in result.lower():
                logger.info(f"Приложение успешно установлено на эмулятор {emulator_index}")
                return True
            else:
                logger.error(f"Ошибка установки приложения на эмулятор {emulator_index}: {result}")
                return False

    def is_emulator_running(self, emulator_index: int) -> bool:
        """
        Проверка, запущен ли эмулятор.

        Args:
            emulator_index: Индекс эмулятора

        Returns:
            True если эмулятор запущен, иначе False
        """
        emulators = self.list_emulators()
        for emu in emulators:
            if emu["index"] == str(emulator_index) and emu["status"] == "running":
                return True
        return False