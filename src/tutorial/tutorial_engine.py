import time
import random
from typing import List, Dict, Optional, Callable, Tuple, Any
from dataclasses import dataclass
from threading import Thread, Event
from ..core.adb_controller import ADBController
from ..core.image_processor import ImageProcessor
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TutorialStep:
    """
    Класс, представляющий шаг туториала.
    """
    id: str  # Уникальный идентификатор шага
    description: str  # Описание шага
    action: Callable  # Функция, выполняющая действие
    args: Tuple = ()  # Аргументы для функции
    kwargs: Dict[str, Any] = None  # Именованные аргументы для функции
    timeout: float = 10.0  # Таймаут ожидания выполнения шага
    retry_count: int = 3  # Количество попыток при неудаче

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class TutorialEngine:
    """
    Движок для выполнения шагов туториала.
    """

    def __init__(self,
                 adb_controller: ADBController,
                 image_processor: ImageProcessor,
                 server_range: Tuple[int, int] = None,
                 on_step_complete: Callable[[str, bool], None] = None,
                 on_tutorial_complete: Callable[[bool], None] = None):
        """
        Инициализация движка туториала.

        Args:
            adb_controller: Контроллер ADB для управления эмулятором
            image_processor: Обработчик изображений для поиска элементов на экране
            server_range: Диапазон серверов для прохождения (начало, конец)
            on_step_complete: Колбэк, вызываемый при завершении шага
            on_tutorial_complete: Колбэк, вызываемый при завершении туториала
        """
        self.adb = adb_controller
        self.image_processor = image_processor
        self.server_range = server_range or (1, 600)  # По умолчанию все сервера
        self.on_step_complete = on_step_complete
        self.on_tutorial_complete = on_tutorial_complete

        self.stop_event = Event()  # Событие для остановки выполнения
        self.current_step = None
        self.steps = []  # Список шагов туториала
        self._tutorial_thread = None
        self._initialize_steps()

        logger.info(f"Инициализация движка туториала. Диапазон серверов: {self.server_range}")

    def _initialize_steps(self):
        """
        Инициализация списка шагов туториала.
        """
        # Шаги будут определены в tutorial_steps.py и будут
        # загружены при запуске движка туториала
        pass

    def set_server_range(self, start: int, end: int):
        """
        Установка диапазона серверов для прохождения.

        Args:
            start: Начальный сервер
            end: Конечный сервер
        """
        self.server_range = (start, end)
        logger.info(f"Установлен диапазон серверов: {self.server_range}")

    def start(self):
        """
        Запуск выполнения туториала в отдельном потоке.
        """
        if self._tutorial_thread and self._tutorial_thread.is_alive():
            logger.warning("Туториал уже запущен")
            return

        self.stop_event.clear()
        self._tutorial_thread = Thread(target=self._run_tutorial, daemon=True)
        self._tutorial_thread.start()
        logger.info("Запущено выполнение туториала")

    def stop(self):
        """
        Остановка выполнения туториала.
        """
        if self._tutorial_thread and self._tutorial_thread.is_alive():
            logger.info("Остановка выполнения туториала")
            self.stop_event.set()
            self._tutorial_thread.join(timeout=3.0)
        else:
            logger.warning("Туториал не запущен или уже остановлен")

    def is_running(self) -> bool:
        """
        Проверка, выполняется ли туториал.

        Returns:
            True если туториал выполняется, иначе False
        """
        return self._tutorial_thread is not None and self._tutorial_thread.is_alive()

    def _run_tutorial(self):
        """
        Основной метод выполнения туториала.
        """
        logger.info("Начало выполнения туториала")
        success = False

        try:
            # Перебираем шаги туториала
            for step in self.steps:
                if self.stop_event.is_set():
                    logger.info("Выполнение туториала прервано")
                    break

                self.current_step = step
                logger.info(f"Выполнение шага {step.id}: {step.description}")

                # Выполняем шаг с заданным количеством попыток
                step_success = False
                for attempt in range(step.retry_count):
                    if self.stop_event.is_set():
                        break

                    try:
                        # Выполняем действие шага
                        result = step.action(*step.args, **step.kwargs)
                        step_success = True
                        break
                    except Exception as e:
                        logger.error(
                            f"Ошибка при выполнении шага {step.id} (попытка {attempt + 1}/{step.retry_count}): {e}")
                        if attempt < step.retry_count - 1:
                            time.sleep(1.0)  # Пауза перед следующей попыткой

                # Вызываем колбэк завершения шага
                if self.on_step_complete:
                    self.on_step_complete(step.id, step_success)

                if not step_success:
                    logger.error(f"Шаг {step.id} не выполнен после {step.retry_count} попыток")
                    break

            # Если дошли до конца и не было прерывания, считаем туториал успешным
            success = not self.stop_event.is_set() and self.current_step.id == self.steps[-1].id
            logger.info(f"Туториал {'успешно завершен' if success else 'не завершен'}")

        except Exception as e:
            logger.error(f"Неожиданная ошибка при выполнении туториала: {e}", exc_info=True)

        # Вызываем колбэк завершения туториала
        if self.on_tutorial_complete:
            self.on_tutorial_complete(success)

        self.current_step = None

    # Вспомогательные методы для выполнения шагов

    def click_on_image(self, image_name: str, timeout: float = 10.0, threshold: float = 0.8) -> bool:
        """
        Клик по изображению на экране.

        Args:
            image_name: Имя изображения для поиска
            timeout: Максимальное время ожидания появления изображения
            threshold: Порог сходства для поиска изображения

        Returns:
            True если клик выполнен успешно, иначе False
        """
        coords = self.image_processor.wait_for_template(
            self.adb, image_name, timeout=timeout, threshold=threshold
        )

        if coords:
            x, y = coords
            self.adb.tap(x, y)
            return True
        return False

    def click_on_coordinates(self, x: int, y: int, wait_time: float = 0) -> bool:
        """
        Клик по заданным координатам.

        Args:
            x: Координата x
            y: Координата y
            wait_time: Время ожидания перед кликом

        Returns:
            True всегда
        """
        if wait_time > 0:
            time.sleep(wait_time)

        self.adb.tap(x, y)
        return True

    def perform_swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> bool:
        """
        Выполнение свайпа от одной точки к другой.

        Args:
            start_x: Начальная координата x
            start_y: Начальная координата y
            end_x: Конечная координата x
            end_y: Конечная координата y
            duration_ms: Продолжительность свайпа в миллисекундах

        Returns:
            True всегда
        """
        self.adb.swipe(start_x, start_y, end_x, end_y, duration_ms)
        return True

    def perform_complex_swipe(self, points: List[Tuple[int, int]], duration_ms: int = 800) -> bool:
        """
        Выполнение сложного свайпа через несколько точек.

        Args:
            points: Список координат для свайпа [(x1, y1), (x2, y2), ...]
            duration_ms: Общая продолжительность свайпа в миллисекундах

        Returns:
            True всегда
        """
        self.adb.complex_swipe(points, duration_ms)
        return True

    def wait_for_image(self, image_name: str, timeout: float = 10.0, threshold: float = 0.8) -> bool:
        """
        Ожидание появления изображения на экране.

        Args:
            image_name: Имя изображения для поиска
            timeout: Максимальное время ожидания
            threshold: Порог сходства

        Returns:
            True если изображение найдено, иначе False
        """
        return self.image_processor.wait_for_template(
            self.adb, image_name, timeout=timeout, threshold=threshold
        ) is not None

    def wait_fixed_time(self, seconds: float) -> bool:
        """
        Ожидание фиксированного времени.

        Args:
            seconds: Время ожидания в секундах

        Returns:
            True всегда
        """
        time.sleep(seconds)
        return True

    def press_esc_until_image(self, image_name: str, interval: float = 10.0, max_attempts: int = 10) -> bool:
        """
        Нажатие клавиши ESC с интервалом до появления изображения.

        Args:
            image_name: Имя изображения для поиска
            interval: Интервал между нажатиями ESC
            max_attempts: Максимальное количество попыток

        Returns:
            True если изображение найдено, иначе False
        """
        for attempt in range(max_attempts):
            screenshot = self.adb.get_screenshot()
            template_match = self.image_processor.find_template(screenshot, image_name)

            if template_match:
                return True

            self.adb.press_esc()
            time.sleep(interval)

        return False

    def find_season_and_click(self, target_server: int) -> bool:
        """
        Поиск нужного сезона на основе целевого сервера и клик по нему.

        Args:
            target_server: Номер целевого сервера

        Returns:
            True если сезон найден и клик выполнен, иначе False
        """
        # Определение сезона по номеру сервера
        season = None

        if 577 <= target_server <= 600:
            season = "S1"
        elif 541 <= target_server <= 576:
            season = "S2"
        elif 505 <= target_server <= 540:
            season = "S3"
        elif 481 <= target_server <= 504:
            season = "S4"
        elif 433 <= target_server <= 480:
            season = "S5"
        elif 409 <= target_server <= 432:
            season = "X1"
        elif 266 <= target_server <= 407:
            season = "X2"
        elif 1 <= target_server <= 264:
            season = "X3"
        else:
            logger.error(f"Невозможно определить сезон для сервера {target_server}")
            return False

        logger.info(f"Поиск сезона {season} для сервера {target_server}")

        # Определяем, нужно ли прокручивать список сезонов
        needs_scroll = season in ["X2", "X3"]

        if needs_scroll:
            # Прокрутка вниз для доступа к сезонам X2, X3
            logger.info("Прокрутка списка сезонов вниз")
            self.perform_swipe(257, 353, 254, 187, 500)
            time.sleep(1.0)

        # Теперь ищем и кликаем по сезону
        # Получаем скриншот
        screenshot = self.adb.get_screenshot()

        # Координаты для различных сезонов (примерные, нужно уточнить)
        season_coords = {
            "S1": (400, 150),
            "S2": (400, 200),
            "S3": (400, 250),
            "S4": (400, 300),
            "S5": (400, 350),
            "X1": (400, 400),
            "X2": (400, 250),  # После прокрутки
            "X3": (400, 300)  # После прокрутки
        }

        if season in season_coords:
            x, y = season_coords[season]
            self.adb.tap(x, y)
            logger.info(f"Клик по сезону {season} на координатах ({x}, {y})")
            return True
        else:
            logger.error(f"Координаты для сезона {season} не определены")
            return False

    def find_server_and_click(self, target_server: int) -> bool:
        """
        Поиск нужного сервера и клик по нему.

        Args:
            target_server: Номер целевого сервера

        Returns:
            True если сервер найден и клик выполнен, иначе False
        """
        logger.info(f"Поиск сервера {target_server}")

        # Максимальное количество прокруток вниз
        max_scrolls = 20
        scroll_count = 0

        while scroll_count < max_scrolls:
            # Получаем скриншот
            screenshot = self.adb.get_screenshot()

            # Здесь должна быть логика поиска номера сервера на скриншоте
            # Для примера используем примитивный подход:

            # Получаем все видимые номера серверов (в реальности нужно использовать OCR)
            visible_servers = []

            # Для тестирования просто предположим, что нашли сервер
            # В реальном коде здесь должен быть парсинг номеров серверов с экрана
            if target_server in visible_servers:
                # Если нашли нужный сервер, кликаем по нему
                # В реальности координаты клика будут зависеть от положения найденного сервера
                x, y = 500, 300  # Примерные координаты
                self.adb.tap(x, y)
                logger.info(f"Клик по серверу {target_server}")
                return True

            # Если не нашли сервер на текущем экране, прокручиваем вниз
            if scroll_count < max_scrolls - 1:
                logger.info(f"Прокрутка списка серверов (попытка {scroll_count + 1})")
                self.perform_swipe(778, 567, 778, 130, 500)
                time.sleep(1.0)
                scroll_count += 1
            else:
                logger.warning(f"Сервер {target_server} не найден после {max_scrolls} прокруток")
                return False

        return False