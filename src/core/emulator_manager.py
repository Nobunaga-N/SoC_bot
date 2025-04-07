import os
import re
import subprocess
import time
import threading
from typing import List, Dict, Optional, Tuple
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
        """
        with self._lock:
            if not os.path.exists(path):
                logger.error(f"Путь не существует: {path}")
                return False

            ldconsole = os.path.join(path, "ldconsole.exe")
            if not os.path.exists(ldconsole):
                logger.error(f"ldconsole.exe не найден в указанной директории: {path}")
                return False

            # Сохраняем путь в настройках
            from ..config.settings import user_settings
            user_settings.set("ldplayer_path", path)

            self.ldplayer_path = path
            self.ldconsole_path = ldconsole
            logger.info(f"Установлен путь к LDPlayer: {path}")
            return True

    def _try_find_ldplayer(self):
        """
        Попытка автоматически найти LDPlayer в стандартных местах.
        """
        default_paths = [
            "C:/Program Files/LDPlayer/LDPlayer9",
            "C:/LDPlayer/LDPlayer9",
            "D:/LDPlayer/LDPlayer9",
            "C:/Program Files (x86)/LDPlayer/LDPlayer9",
            os.path.expanduser("~/AppData/Local/LDPlayer/LDPlayer9")
        ]

        for path in default_paths:
            ldconsole = os.path.join(path, "ldconsole.exe")
            if os.path.exists(ldconsole):
                self.ldplayer_path = path
                self.ldconsole_path = ldconsole
                logger.info(f"Автоматически найден путь к LDPlayer: {path}")

                # Сохраняем в настройках
                from ..config.settings import user_settings
                user_settings.set("ldplayer_path", path)

                return True

        logger.error("Не удалось автоматически найти LDPlayer")
        return False

    def execute_ldconsole_with_timeout(self, command: str, timeout: float = 5.0) -> str:
        """
        Выполнение команды ldconsole с таймаутом.

        Args:
            command: Команда для выполнения
            timeout: Таймаут в секундах

        Returns:
            Результат выполнения команды
        """
        if not self.ldconsole_path or not os.path.exists(self.ldconsole_path):
            logger.error(f"Путь к ldconsole.exe не установлен или неверный: {self.ldconsole_path}")
            return ""

        try:
            full_command = f'"{self.ldconsole_path}" {command}'
            logger.debug(f"Выполнение команды LDConsole с таймаутом {timeout}с: {full_command}")

            import subprocess
            result = subprocess.run(full_command, shell=True, capture_output=True, text=True, timeout=timeout)

            if result.returncode != 0:
                logger.error(f"Ошибка выполнения команды LDConsole: {result.stderr}")
                return result.stderr

            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Таймаут выполнения команды LDConsole: {command}")
            return "ERROR: Timeout"
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при выполнении команды LDConsole: {e}")
            return ""

    def execute_ldconsole(self, command: str) -> str:
        """
        Выполнение команды ldconsole.
        """
        if not self.ldconsole_path or not os.path.exists(self.ldconsole_path):
            logger.error(f"Путь к ldconsole.exe не установлен или неверный: {self.ldconsole_path}")
            # Пробуем найти LDPlayer автоматически
            self._try_find_ldplayer()

            # Повторная проверка
            if not self.ldconsole_path or not os.path.exists(self.ldconsole_path):
                return ""

        try:
            full_command = f'"{self.ldconsole_path}" {command}'
            logger.debug(f"Выполнение команды LDConsole: {full_command}")

            result = subprocess.check_output(full_command, shell=True, stderr=subprocess.STDOUT, timeout=30)
            return result.decode('utf-8', errors='ignore').strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка выполнения команды LDConsole: {e}")
            return e.output.decode('utf-8', errors='ignore').strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Таймаут выполнения команды LDConsole: {command}")
            return "ERROR: Timeout"
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при выполнении команды LDConsole: {e}")
            return ""

    def list_emulators(self) -> List[Dict[str, str]]:
        """
        Получение списка всех эмуляторов LDPlayer.
        """
        with self._lock:
            result = self.execute_ldconsole("list2")
            logger.debug(f"Результат команды list2: {result}")
            emulators = []

            for line in result.splitlines():
                if not line.strip():
                    continue

                parts = line.split(',')

                if len(parts) >= 3:
                    emulator_index = parts[0]

                    # Проверяем статус напрямую через isrunning
                    running_result = self.execute_ldconsole(f"isrunning --index {emulator_index}")
                    is_running = "running" in running_result.lower() or "1" in running_result

                    emulator = {
                        "index": emulator_index,
                        "name": parts[1],
                        "status": "running" if is_running else "stopped"
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
        Улучшенная версия, которая не блокирует основной поток.
        """
        try:
            # Если уже знаем ID, вернем его сразу
            for adb_id, idx in self.active_emulators.items():
                if idx == str(emulator_index):
                    logger.info(f"Используем сохраненный ADB ID для эмулятора {emulator_index}: {adb_id}")
                    return adb_id

            # Проверяем, запущен ли эмулятор БЕЗ блокирования с помощью lock
            emulators = self.list_emulators()
            emulator_running = False

            for emu in emulators:
                if emu["index"] == str(emulator_index) and emu["status"] == "running":
                    emulator_running = True
                    break

            if not emulator_running:
                logger.warning(f"Эмулятор {emulator_index} не запущен, пропускаем получение ADB ID")
                return None

            # Получаем ADB ID через LDConsole с таймаутом
            logger.debug(f"Получение ADB ID для эмулятора {emulator_index}")
            result = self.execute_ldconsole_with_timeout(f"adb --index {emulator_index} --command \"get-serialno\"",
                                                         timeout=5)

            if result and result.strip():
                device_id = result.strip()
                with self._lock:  # Используем lock только для краткой операции записи в словарь
                    self.active_emulators[device_id] = str(emulator_index)
                logger.info(f"Получен ADB ID для эмулятора {emulator_index}: {device_id}")
                return device_id

            # Альтернативный способ - получить через список устройств ADB
            adb_devices = self.get_adb_devices()

            # Для LDPlayer обычно используется порт 5554 + 2*index или 5555 + 2*index
            expected_port1 = 5554 + emulator_index * 2
            expected_port2 = 5555 + emulator_index * 2

            for device_id, status in adb_devices.items():
                if status == "device" and (
                        f"emulator-{expected_port1}" in device_id or
                        f"127.0.0.1:{expected_port2}" in device_id
                ):
                    with self._lock:  # Краткая операция записи
                        self.active_emulators[device_id] = str(emulator_index)
                    logger.info(f"Получен ADB ID для эмулятора {emulator_index} через список устройств: {device_id}")
                    return device_id

            logger.error(f"Не удалось получить ADB ID для эмулятора {emulator_index}")
            return None

        except Exception as e:
            logger.error(f"Ошибка при получении ADB ID для эмулятора {emulator_index}: {e}")
            return None

    def start_emulator(self, emulator_index: int) -> bool:
        """
        Запуск эмулятора LDPlayer по его индексу.
        Улучшенная версия, которая не блокирует на долгое время.

        Args:
            emulator_index: Индекс эмулятора

        Returns:
            True если эмулятор запущен успешно, иначе False
        """
        # Проверяем, не запущен ли уже эмулятор
        emulators = self.list_emulators()
        for emu in emulators:
            if emu["index"] == str(emulator_index) and emu["status"] == "running":
                logger.info(f"Эмулятор {emulator_index} уже запущен")
                return True

        # Запускаем эмулятор - короткая операция с lock
        logger.info(f"Запуск эмулятора с индексом {emulator_index}")
        result = self.execute_ldconsole_with_timeout(f"launch --index {emulator_index}", timeout=5)

        # Проверяем запуск без удержания lock
        start_time = time.time()
        max_wait_time = 30  # Максимальное время ожидания в секундах
        check_interval = 2  # Интервал проверки в секундах

        while time.time() - start_time < max_wait_time:
            # Проверяем статус без блокировки
            is_running = False
            try:
                result = self.execute_ldconsole_with_timeout(
                    f"isrunning --index {emulator_index}",
                    timeout=3
                )
                is_running = "running" in result.lower() or "1" in result
            except Exception as e:
                logger.error(f"Ошибка при проверке статуса эмулятора {emulator_index}: {e}")

            if is_running:
                logger.info(f"Эмулятор {emulator_index} успешно запущен")
                return True

            logger.debug(f"Ожидание запуска эмулятора {emulator_index}, прошло {time.time() - start_time:.1f}с")
            time.sleep(check_interval)

        logger.error(f"Не удалось запустить эмулятор {emulator_index} после {max_wait_time}с ожидания")
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

    def is_emulator_responsive(self, emulator_index: int) -> bool:
        """
        Проверка, отвечает ли эмулятор на команды.

        Args:
            emulator_index: Индекс эмулятора

        Returns:
            True если эмулятор отвечает, иначе False
        """
        # Сначала проверяем, запущен ли эмулятор
        if not self.is_emulator_running(emulator_index):
            logger.warning(f"Эмулятор {emulator_index} не запущен")
            return False

        # Получаем ADB ID
        adb_id = self.get_emulator_adb_id(emulator_index)

        if not adb_id:
            logger.error(f"Не удалось получить ADB ID для эмулятора {emulator_index}")
            return False

        try:
            # Пытаемся выполнить простую ADB команду
            result = subprocess.run(
                f"adb -s {adb_id} shell dumpsys window",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )

            # Проверяем код возврата
            if result.returncode != 0:
                logger.warning(f"Эмулятор {emulator_index} не отвечает на ADB команды")
                return False

            # Если команда выполнена успешно, эмулятор отвечает
            return True
        except subprocess.TimeoutExpired:
            logger.warning(f"Таймаут при выполнении команды для эмулятора {emulator_index}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке эмулятора {emulator_index}: {e}")
            return False

    def restart_if_unresponsive(self, emulator_index: int, check_interval: int = 30) -> bool:
        """
        Перезапуск эмулятора, если он не отвечает на команды.

        Args:
            emulator_index: Индекс эмулятора
            check_interval: Интервал проверки в секундах

        Returns:
            True если эмулятор в рабочем состоянии (или успешно перезапущен), иначе False
        """
        # Проверяем, отвечает ли эмулятор
        if self.is_emulator_responsive(emulator_index):
            return True

        logger.warning(f"Эмулятор {emulator_index} не отвечает, попытка перезапуска")

        # Принудительно останавливаем эмулятор (в случае зависания)
        for attempt in range(3):
            try:
                self.execute_ldconsole(f"quit --index {emulator_index} --force")
                break
            except Exception as e:
                logger.error(f"Ошибка при остановке эмулятора {emulator_index}: {e}")

        # Ждем некоторое время
        time.sleep(5)

        # Пытаемся перезапустить эмулятор
        return self.restart_emulator(emulator_index)

    def start_emulator_with_params(self, emulator_index: int, params: dict = None) -> bool:
        """
        Запуск эмулятора с определенными параметрами.

        Args:
            emulator_index: Индекс эмулятора
            params: Словарь параметров {параметр: значение}

        Returns:
            True если эмулятор запущен успешно, иначе False
        """
        params = params or {}

        # Проверяем, не запущен ли уже эмулятор
        if self.is_emulator_running(emulator_index):
            logger.info(f"Эмулятор {emulator_index} уже запущен")
            return True

        # Формируем команду запуска с параметрами
        cmd = f"launch --index {emulator_index}"

        # Добавляем параметры
        for param, value in params.items():
            cmd += f" --{param} {value}"

        # Запускаем эмулятор
        result = self.execute_ldconsole(cmd)

        # Ждем запуска эмулятора
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)  # Ждем 2 секунды между проверками

            if self.is_emulator_running(emulator_index):
                logger.info(f"Эмулятор {emulator_index} успешно запущен с параметрами: {params}")
                return True

            logger.debug(f"Ожидание запуска эмулятора {emulator_index}, попытка {attempt + 1}/{max_attempts}")

        logger.error(f"Не удалось запустить эмулятор {emulator_index} после {max_attempts} попыток")
        return False
