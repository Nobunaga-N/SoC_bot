import os
import subprocess
import time
from typing import Tuple, Optional, List, Union
import numpy as np
import cv2
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ADBController:
    """
    Класс для взаимодействия с эмулятором через ADB команды.
    Обеспечивает функционал для отправки команд, получения скриншотов и
    выполнения действий на устройстве.
    """

    def __init__(self, emulator_id: str):
        """
        Инициализация контроллера ADB для конкретного эмулятора.

        Args:
            emulator_id: Идентификатор эмулятора (например, 'emulator-5554')
        """
        self.emulator_id = emulator_id
        logger.info(f"Инициализация ADB контроллера для эмулятора {emulator_id}")

    def execute_command(self, command: str) -> str:
        """
        Выполнение ADB команды.

        Args:
            command: ADB команда для выполнения

        Returns:
            Результат выполнения команды
        """
        full_command = f"adb -s {self.emulator_id} {command}"
        logger.debug(f"Выполнение ADB команды: {full_command}")

        try:
            result = subprocess.check_output(full_command, shell=True, stderr=subprocess.STDOUT)
            return result.decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка выполнения ADB команды: {e}")
            return e.output.decode('utf-8').strip()

    def execute_command_with_timeout(self, command: str, timeout: float = 30.0) -> str:
        """
        Выполнение ADB команды с таймаутом.

        Args:
            command: ADB команда для выполнения
            timeout: Таймаут в секундах

        Returns:
            Результат выполнения команды

        Raises:
            ADBError: При ошибке выполнения команды или превышении таймаута
        """
        import subprocess
        import threading
        from ..utils.exceptions import ADBError

        full_command = f"adb -s {self.emulator_id} {command}"
        logger.debug(f"Выполнение ADB команды с таймаутом: {full_command}")

        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Используем threading.Timer для обеспечения таймаута
        timer = threading.Timer(timeout, process.kill)
        try:
            timer.start()
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore').strip()
                raise ADBError(f"Ошибка выполнения ADB команды: {error_msg}")
            return stdout.decode('utf-8', errors='ignore').strip()
        finally:
            timer.cancel()

    def check_adb_server(self) -> bool:
        """
        Проверка состояния ADB сервера и его перезапуск при необходимости.

        Returns:
            True если ADB сервер работает корректно, иначе False
        """
        try:
            import subprocess

            # Проверяем статус ADB сервера
            result = subprocess.run("adb devices", shell=True, capture_output=True, text=True)

            # Если в выводе есть "daemon not running", перезапускаем ADB сервер
            if "daemon not running" in result.stdout or "daemon not running" in result.stderr:
                logger.warning("ADB сервер не запущен, перезапуск...")
                subprocess.run("adb kill-server", shell=True)
                time.sleep(1)
                subprocess.run("adb start-server", shell=True)
                time.sleep(2)

                # Проверяем снова
                result = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
                if "daemon not running" in result.stdout or "daemon not running" in result.stderr:
                    logger.error("Не удалось перезапустить ADB сервер")
                    return False

            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке ADB сервера: {e}")
            return False

    def tap(self, x: int, y: int) -> None:
        """
        Выполнить клик по координатам.

        Args:
            x: Координата x для клика
            y: Координата y для клика
        """
        logger.debug(f"Клик по координатам x={x}, y={y}")
        self.execute_command(f"shell input tap {x} {y}")

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> None:
        """
        Выполнить свайп от одной точки к другой.

        Args:
            start_x: Начальная координата x
            start_y: Начальная координата y
            end_x: Конечная координата x
            end_y: Конечная координата y
            duration_ms: Продолжительность свайпа в миллисекундах
        """
        logger.debug(f"Свайп от ({start_x}, {start_y}) к ({end_x}, {end_y}), длительность: {duration_ms}ms")
        self.execute_command(f"shell input swipe {start_x} {start_y} {end_x} {end_y} {duration_ms}")

    def complex_swipe(self, coordinates: List[Tuple[int, int]], duration_ms: int = 800) -> None:
        """
        Выполнить сложный свайп через несколько точек.

        Args:
            coordinates: Список координат для свайпа [(x1, y1), (x2, y2), ...]
            duration_ms: Общая продолжительность свайпа в миллисекундах
        """
        logger.debug(f"Сложный свайп через точки {coordinates}, длительность: {duration_ms}ms")

        if len(coordinates) < 2:
            logger.error("Для сложного свайпа требуется минимум 2 точки")
            return

        # Разделяем общую продолжительность на отдельные свайпы
        segment_duration = duration_ms // (len(coordinates) - 1)

        for i in range(len(coordinates) - 1):
            start_x, start_y = coordinates[i]
            end_x, end_y = coordinates[i + 1]
            self.swipe(start_x, start_y, end_x, end_y, segment_duration)
            time.sleep(0.1)  # Небольшая задержка между сегментами

    def get_screenshot_buffered(self, use_buffer: bool = True) -> np.ndarray:
        """
        Получить скриншот с эмулятора с опцией буферизации для повышения производительности.

        Args:
            use_buffer: Использовать ли буферизацию (повторно использовать последний скриншот)

        Returns:
            Изображение в формате numpy array (BGR)
        """
        if not hasattr(self, '_last_screenshot') or not hasattr(self, '_last_screenshot_time'):
            self._last_screenshot = None
            self._last_screenshot_time = 0

        # Если буферизация включена и прошло менее 100 мс с момента последнего скриншота,
        # возвращаем сохраненный скриншот
        current_time = time.time()
        if use_buffer and self._last_screenshot is not None and (current_time - self._last_screenshot_time) < 0.1:
            return self._last_screenshot.copy()

        logger.debug("Получение нового скриншота с эмулятора")

        try:
            # Получаем скриншот через стандартный метод работы с файлами
            self.execute_command("shell screencap -p /sdcard/screenshot.png")

            # Вместо использования промежуточного файла на хосте, читаем напрямую в память
            raw_data = self.execute_command("exec-out cat /sdcard/screenshot.png")

            # Преобразуем бинарные данные в массив numpy
            nparr = np.frombuffer(raw_data.encode('latin1'), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Удаляем временный файл
            self.execute_command("shell rm /sdcard/screenshot.png")

            if img is None:
                logger.error("Не удалось декодировать скриншот")
                if self._last_screenshot is not None:
                    return self._last_screenshot.copy()
                return np.zeros((1080, 1920, 3), dtype=np.uint8)

            # Сохраняем скриншот и время получения
            self._last_screenshot = img
            self._last_screenshot_time = current_time

            return img
        except Exception as e:
            logger.error(f"Ошибка при получении скриншота: {e}")
            if self._last_screenshot is not None:
                return self._last_screenshot.copy()
            return np.zeros((1080, 1920, 3), dtype=np.uint8)

    def press_key(self, key_code: int) -> None:
        """
        Нажать клавишу по коду.

        Args:
            key_code: Код клавиши Android (например, 4 для BACK)
        """
        logger.debug(f"Нажатие клавиши с кодом {key_code}")
        self.execute_command(f"shell input keyevent {key_code}")

    def press_esc(self) -> None:
        """
        Нажать клавишу ESC (для закрытия рекламы).
        """
        logger.debug("Нажатие клавиши ESC")
        self.press_key(111)  # Код клавиши ESC

    def start_app(self, package_name: str, activity_name: str = None) -> None:
        """
        Запустить приложение на эмуляторе.

        Args:
            package_name: Имя пакета приложения
            activity_name: Имя активити для запуска (опционально)
        """
        if activity_name:
            logger.info(f"Запуск приложения {package_name}/{activity_name}")
            cmd = f"shell am start -n {package_name}/{activity_name}"
        else:
            logger.info(f"Запуск приложения {package_name}")
            cmd = f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"

        self.execute_command(cmd)

    def stop_app(self, package_name: str) -> None:
        """
        Остановить приложение на эмуляторе.

        Args:
            package_name: Имя пакета приложения
        """
        logger.info(f"Остановка приложения {package_name}")
        self.execute_command(f"shell am force-stop {package_name}")

    def is_app_running(self, package_name: str) -> bool:
        """
        Проверить, запущено ли приложение.

        Args:
            package_name: Имя пакета приложения

        Returns:
            True если приложение запущено, иначе False
        """
        result = self.execute_command(f"shell pidof {package_name}")
        return bool(result.strip())

    def wait_for_device(self, timeout: int = 30) -> bool:
        """
        Ожидание, когда устройство будет доступно.

        Args:
            timeout: Максимальное время ожидания в секундах

        Returns:
            True если устройство доступно, иначе False
        """
        logger.info(f"Ожидание доступности устройства {self.emulator_id}")
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = self.execute_command("get-state")
            if "device" in result:
                logger.info(f"Устройство {self.emulator_id} доступно")
                return True
            time.sleep(1)

        logger.error(f"Устройство {self.emulator_id} не доступно после {timeout}с ожидания")
        return False