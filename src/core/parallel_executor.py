import os
import time
import queue
import threading
from typing import List, Dict, Tuple, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from ..core.adb_controller import ADBController
from ..core.image_processor import ImageProcessor
from ..core.emulator_manager import EmulatorManager
from ..tutorial.tutorial_engine import TutorialEngine
from ..tutorial.tutorial_steps import create_tutorial_steps
from ..utils.logger import get_logger
from ..utils.exceptions import EmulatorError, ADBError

logger = get_logger(__name__)


class EmulatorTask:
    """
    Класс, представляющий задачу для выполнения на эмуляторе.
    """

    def __init__(self, emulator_id: str, task_id: str, func: Callable, args: Tuple = (),
                 kwargs: Dict[str, Any] = None):
        """
        Инициализация задачи.

        Args:
            emulator_id: Идентификатор эмулятора
            task_id: Идентификатор задачи
            func: Функция для выполнения
            args: Аргументы функции
            kwargs: Именованные аргументы функции
        """
        self.emulator_id = emulator_id
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.result = None
        self.error = None
        self.completed = False
        self.start_time = None
        self.end_time = None

    def execute(self):
        """
        Выполнение задачи.

        Returns:
            Результат выполнения задачи
        """
        self.start_time = time.time()
        try:
            self.result = self.func(*self.args, **self.kwargs)
            return self.result
        except Exception as e:
            self.error = e
            raise
        finally:
            self.end_time = time.time()
            self.completed = True

    def duration(self) -> float:
        """
        Длительность выполнения задачи в секундах.

        Returns:
            Длительность в секундах
        """
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time


class ParallelEmulatorExecutor:
    """
    Класс для параллельного выполнения задач на нескольких эмуляторах.
    """

    def __init__(self, assets_path: str, max_workers: int = None, timeout: float = 600.0, emulator_manager=None):
        """
        Инициализация исполнителя задач.

        Args:
            assets_path: Путь к директории с изображениями-шаблонами
            max_workers: Максимальное количество рабочих потоков (если None, то равно количеству эмуляторов)
            timeout: Таймаут выполнения задачи в секундах
            emulator_manager: Существующий экземпляр EmulatorManager (если None, создается новый)
        """
        self.assets_path = assets_path
        self.max_workers = max_workers
        self.timeout = timeout

        # Используем переданный экземпляр EmulatorManager или создаем новый
        if emulator_manager is not None:
            self.emulator_manager = emulator_manager
        else:
            # Импортируем здесь, чтобы избежать циклических импортов
            from ..config.settings import user_settings
            ldplayer_path = user_settings.get("ldplayer_path", "")
            self.emulator_manager = EmulatorManager(ldplayer_path)

        # Словарь контроллеров ADB для эмуляторов
        # {emulator_id: adb_controller}
        self.adb_controllers = {}

        # Словарь обработчиков изображений для эмуляторов
        # {emulator_id: image_processor}
        self.image_processors = {}

        # Словарь движков туториала для эмуляторов
        # {emulator_id: tutorial_engine}
        self.tutorial_engines = {}

        # Словарь текущих задач для эмуляторов
        # {emulator_id: task}
        self.current_tasks = {}

        # Блокировка для безопасного доступа к общим ресурсам
        self.lock = threading.RLock()

        # Очередь задач
        self.task_queue = queue.Queue()

        # Пул потоков для выполнения задач
        self.executor = None

        # Словарь будущих результатов
        # {task_id: future}
        self.futures = {}

        # Флаг остановки
        self.stop_flag = threading.Event()

        # Инициализация базовых ресурсов
        self._init_resources()

        logger.info(f"Инициализация параллельного исполнителя с максимальным количеством потоков: {max_workers}")

    def _init_resources(self):
        """
        Инициализация общих ресурсов.
        """
        # Создаем один общий обработчик изображений, который будет использоваться всеми эмуляторами
        self.global_image_processor = ImageProcessor(self.assets_path)
        logger.info(f"Инициализирован глобальный обработчик изображений")

    def initialize_emulator(self, emulator_id: str, check_device: bool = False) -> bool:
        """
        Инициализация ресурсов для конкретного эмулятора.

        Args:
            emulator_id: Идентификатор эмулятора
            check_device: Флаг проверки доступности устройства (может блокировать поток)

        Returns:
            True если инициализация успешна, иначе False
        """
        with self.lock:
            try:
                # Проверяем, не инициализирован ли уже этот эмулятор
                if emulator_id in self.adb_controllers:
                    logger.debug(f"Эмулятор {emulator_id} уже инициализирован")
                    return True

                # Создаем контроллер ADB
                adb_controller = ADBController(emulator_id)

                # Проверяем доступность устройства (только если указан флаг)
                if check_device:
                    if not adb_controller.wait_for_device(timeout=5):  # Уменьшаем таймаут до 5 секунд
                        logger.error(f"Устройство {emulator_id} недоступно")
                        return False

                # Сохраняем контроллер
                self.adb_controllers[emulator_id] = adb_controller

                # Используем глобальный обработчик изображений для экономии памяти
                self.image_processors[emulator_id] = self.global_image_processor

                logger.info(f"Эмулятор {emulator_id} успешно инициализирован")
                return True

            except Exception as e:
                logger.error(f"Ошибка при инициализации эмулятора {emulator_id}: {e}")
                # Очистка ресурсов в случае ошибки
                if emulator_id in self.adb_controllers:
                    del self.adb_controllers[emulator_id]
                if emulator_id in self.image_processors:
                    del self.image_processors[emulator_id]
                return False

    def initialize_tutorial_engine(self, emulator_id: str, server_range: Tuple[int, int],
                                   on_step_complete: Callable = None,
                                   on_tutorial_complete: Callable = None) -> bool:
        """
        Инициализация движка туториала для конкретного эмулятора.

        Args:
            emulator_id: Идентификатор эмулятора
            server_range: Диапазон серверов (начало, конец)
            on_step_complete: Колбэк завершения шага
            on_tutorial_complete: Колбэк завершения туториала

        Returns:
            True если инициализация успешна, иначе False
        """
        with self.lock:
            try:
                # Проверяем, инициализирован ли эмулятор
                if emulator_id not in self.adb_controllers:
                    logger.error(f"Эмулятор {emulator_id} не инициализирован")
                    return False

                adb_controller = self.adb_controllers[emulator_id]
                image_processor = self.image_processors[emulator_id]

                # Создаем функции-обертки для колбэков с передачей ID эмулятора
                step_callback = None
                complete_callback = None

                if on_step_complete:
                    step_callback = lambda step_id, success: on_step_complete(emulator_id, step_id, success)

                if on_tutorial_complete:
                    complete_callback = lambda success: on_tutorial_complete(emulator_id, success)

                # Создаем движок туториала
                tutorial_engine = TutorialEngine(
                    adb_controller=adb_controller,
                    image_processor=image_processor,
                    server_range=server_range,
                    on_step_complete=step_callback,
                    on_tutorial_complete=complete_callback
                )

                # Загружаем шаги туториала
                steps = create_tutorial_steps(tutorial_engine)
                tutorial_engine.steps = steps

                # Сохраняем движок
                self.tutorial_engines[emulator_id] = tutorial_engine

                logger.info(f"Движок туториала для эмулятора {emulator_id} успешно инициализирован")
                return True

            except Exception as e:
                logger.error(f"Ошибка при инициализации движка туториала для эмулятора {emulator_id}: {e}")
                # Очистка ресурсов в случае ошибки
                if emulator_id in self.tutorial_engines:
                    del self.tutorial_engines[emulator_id]
                return False

    def cleanup_emulator(self, emulator_id: str):
        """
        Очистка ресурсов для конкретного эмулятора.

        Args:
            emulator_id: Идентификатор эмулятора
        """
        with self.lock:
            try:
                # Останавливаем выполнение туториала, если он запущен
                if emulator_id in self.tutorial_engines and self.tutorial_engines[emulator_id].is_running():
                    self.tutorial_engines[emulator_id].stop()

                # Удаляем ресурсы
                if emulator_id in self.adb_controllers:
                    del self.adb_controllers[emulator_id]
                if emulator_id in self.image_processors:
                    del self.image_processors[emulator_id]
                if emulator_id in self.tutorial_engines:
                    del self.tutorial_engines[emulator_id]
                if emulator_id in self.current_tasks:
                    del self.current_tasks[emulator_id]

                logger.info(f"Ресурсы для эмулятора {emulator_id} очищены")

            except Exception as e:
                logger.error(f"Ошибка при очистке ресурсов для эмулятора {emulator_id}: {e}")

    def start_tutorial(self, emulator_id: str, server_range: Tuple[int, int],
                       on_step_complete: Callable = None,
                       on_tutorial_complete: Callable = None) -> str:
        """
        Запуск туториала на указанном эмуляторе.

        Args:
            emulator_id: Идентификатор эмулятора
            server_range: Диапазон серверов (начало, конец)
            on_step_complete: Колбэк завершения шага
            on_tutorial_complete: Колбэк завершения туториала

        Returns:
            Идентификатор задачи или None в случае ошибки
        """
        # Инициализация эмулятора, если он еще не инициализирован
        # Не проверяем доступность устройства здесь, это может блокировать поток
        if not self.initialize_emulator(emulator_id, check_device=False):
            return None

        # Инициализация движка туториала
        if not self.initialize_tutorial_engine(emulator_id, server_range, on_step_complete, on_tutorial_complete):
            return None

        # Создаем задачу для запуска туториала
        task_id = f"tutorial_{emulator_id}_{int(time.time())}"
        task = EmulatorTask(
            emulator_id=emulator_id,
            task_id=task_id,
            func=self._run_tutorial,
            args=(emulator_id,)
        )

        # Добавляем задачу в очередь
        with self.lock:
            self.current_tasks[emulator_id] = task
            self.task_queue.put(task)

        logger.info(f"Задача {task_id} добавлена в очередь для эмулятора {emulator_id}")
        return task_id

    def _run_tutorial(self, emulator_id: str) -> bool:
        """
        Внутренний метод для выполнения туториала.

        Args:
            emulator_id: Идентификатор эмулятора

        Returns:
            True если туториал выполнен успешно, иначе False
        """
        try:
            with self.lock:
                if emulator_id not in self.adb_controllers:
                    logger.error(f"Контроллер ADB для эмулятора {emulator_id} не инициализирован")
                    return False

                adb_controller = self.adb_controllers[emulator_id]

                if emulator_id not in self.tutorial_engines:
                    logger.error(f"Движок туториала для эмулятора {emulator_id} не инициализирован")
                    return False

                tutorial_engine = self.tutorial_engines[emulator_id]

            # Проверяем доступность устройства здесь, в рабочем потоке
            if not adb_controller.wait_for_device(timeout=10):
                logger.error(f"Устройство {emulator_id} недоступно перед запуском туториала")
                return False

            # Запускаем туториал
            tutorial_engine.start()

            # Ждем завершения или остановки
            while tutorial_engine.is_running() and not self.stop_flag.is_set():
                time.sleep(0.5)

            # Если была запрошена остановка, останавливаем движок
            if self.stop_flag.is_set() and tutorial_engine.is_running():
                tutorial_engine.stop()
                return False

            # Проверяем успешность выполнения
            success = not self.stop_flag.is_set() and tutorial_engine.current_step is None

            return success

        except Exception as e:
            logger.error(f"Ошибка при выполнении туториала на эмуляторе {emulator_id}: {e}")
            return False

    def run_task(self, task: EmulatorTask) -> Any:
        """
        Выполнение задачи на эмуляторе.

        Args:
            task: Задача для выполнения

        Returns:
            Результат выполнения задачи
        """
        try:
            logger.info(f"Выполнение задачи {task.task_id} на эмуляторе {task.emulator_id}")
            result = task.execute()
            logger.info(f"Задача {task.task_id} на эмуляторе {task.emulator_id} выполнена за {task.duration():.2f}с")
            return result
        except Exception as e:
            logger.error(f"Ошибка при выполнении задачи {task.task_id} на эмуляторе {task.emulator_id}: {e}")
            raise

    def start(self):
        """
        Запуск обработки задач в отдельных потоках.
        """
        if self.executor is not None:
            logger.warning("Исполнитель уже запущен")
            return

        # Устанавливаем максимальное количество потоков
        if self.max_workers is None:
            # Если не указано, используем количество доступных эмуляторов
            active_emulators = len(self.emulator_manager.list_emulators())
            self.max_workers = max(1, active_emulators)
            logger.info(f"Определено количество рабочих потоков: {self.max_workers}")

        # Создаем пул потоков
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.stop_flag.clear()

        # Запускаем отдельный поток для обработки очереди задач
        threading.Thread(target=self._task_queue_worker, daemon=True).start()

        logger.info(f"Запущен обработчик задач с {self.max_workers} рабочими потоками")

    def stop(self):
        """
        Остановка обработки задач.
        """
        if self.executor is None:
            logger.warning("Исполнитель не запущен")
            return

        logger.info("Остановка обработчика задач")
        self.stop_flag.set()

        # Отменяем все незавершенные задачи
        with self.lock:
            for task_id, future in list(self.futures.items()):
                if not future.done():
                    future.cancel()
                    logger.info(f"Задача {task_id} отменена")

        # Завершаем пул потоков
        self.executor.shutdown(wait=False)
        self.executor = None

        logger.info("Обработчик задач остановлен")

    def _task_queue_worker(self):
        """
        Рабочий поток для обработки очереди задач.
        """
        while not self.stop_flag.is_set():
            try:
                # Извлекаем задачу из очереди с таймаутом
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Создаем и запускаем задачу в пуле потоков
                with self.lock:
                    future = self.executor.submit(self.run_task, task)
                    self.futures[task.task_id] = future

                # Устанавливаем обработчик завершения
                future.add_done_callback(lambda f, task_id=task.task_id: self._on_task_completed(task_id, f))

                # Отмечаем задачу как обработанную
                self.task_queue.task_done()

            except Exception as e:
                logger.error(f"Ошибка в рабочем потоке очереди задач: {e}")
                time.sleep(1.0)  # Пауза перед повторной попыткой

        logger.info("Рабочий поток очереди задач завершен")

    def _on_task_completed(self, task_id: str, future: Future):
        """
        Обработчик завершения задачи.

        Args:
            task_id: Идентификатор задачи
            future: Будущий результат
        """
        with self.lock:
            # Удаляем задачу из списка текущих задач
            for emulator_id, task in list(self.current_tasks.items()):
                if task.task_id == task_id:
                    del self.current_tasks[emulator_id]
                    break

            # Удаляем будущий результат из словаря
            if task_id in self.futures:
                del self.futures[task_id]

        try:
            # Получаем результат задачи
            result = future.result()
            logger.info(f"Задача {task_id} завершена с результатом: {result}")
        except Exception as e:
            logger.error(f"Задача {task_id} завершена с ошибкой: {e}")

    def get_task_result(self, task_id: str, timeout: float = None) -> Optional[Any]:
        """
        Получение результата выполнения задачи.

        Args:
            task_id: Идентификатор задачи
            timeout: Таймаут ожидания в секундах

        Returns:
            Результат задачи или None, если задача не найдена или не завершена
        """
        with self.lock:
            if task_id not in self.futures:
                logger.warning(f"Задача {task_id} не найдена")
                return None

            future = self.futures[task_id]

        try:
            # Ждем завершения задачи
            return future.result(timeout=timeout)
        except TimeoutError:
            logger.warning(f"Таймаут ожидания результата задачи {task_id}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении результата задачи {task_id}: {e}")
            return None

    def is_task_completed(self, task_id: str) -> bool:
        """
        Проверка, завершена ли задача.

        Args:
            task_id: Идентификатор задачи

        Returns:
            True если задача завершена, иначе False
        """
        with self.lock:
            if task_id not in self.futures:
                logger.warning(f"Задача {task_id} не найдена")
                return False

            return self.futures[task_id].done()

    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение списка активных задач.

        Returns:
            Словарь {task_id: {emulator_id, start_time, duration, status}}
        """
        active_tasks = {}

        with self.lock:
            for emulator_id, task in self.current_tasks.items():
                status = "running"

                if task.task_id in self.futures:
                    future = self.futures[task.task_id]
                    if future.done():
                        try:
                            future.result(timeout=0)
                            status = "completed"
                        except Exception:
                            status = "failed"

                active_tasks[task.task_id] = {
                    "emulator_id": emulator_id,
                    "start_time": task.start_time,
                    "duration": task.duration(),
                    "status": status
                }

        return active_tasks

    def process_multiple_emulators(self, emulator_indices: List[int], server_ranges: Dict[int, Tuple[int, int]],
                                   on_step_complete: Callable = None,
                                   on_tutorial_complete: Callable = None) -> Dict[int, str]:
        """
        Запуск туториала на нескольких эмуляторах одновременно.
        Эта функция больше не используется напрямую из MainWindow, так как ее функциональность
        перемещена в отдельные потоки EmulatorInitWorker и TutorialStartWorker.

        Args:
            emulator_indices: Список индексов эмуляторов
            server_ranges: Словарь диапазонов серверов {emulator_index: (start, end)}
            on_step_complete: Колбэк завершения шага
            on_tutorial_complete: Колбэк завершения туториала

        Returns:
            Словарь {emulator_index: task_id}
        """
        # Запускаем обработчик задач, если он не запущен
        if self.executor is None:
            self.start()

        # Получаем ADB ID для каждого эмулятора
        emulator_ids = {}

        for index in emulator_indices:
            # Проверяем, запущен ли эмулятор
            if not self.emulator_manager.is_emulator_running(index):
                logger.warning(f"Эмулятор {index} не запущен, пропускаем")
                continue

            # Получаем ADB ID
            adb_id = self.emulator_manager.get_emulator_adb_id(index)

            if not adb_id:
                logger.error(f"Не удалось получить ADB ID для эмулятора {index}")
                continue

            emulator_ids[index] = adb_id

        # Запускаем туториал на каждом эмуляторе
        task_ids = {}

        for index, adb_id in emulator_ids.items():
            # Определяем диапазон серверов для этого эмулятора
            server_range = server_ranges.get(index, (1, 10))  # По умолчанию 1-10

            # Запускаем туториал
            task_id = self.start_tutorial(
                emulator_id=adb_id,
                server_range=server_range,
                on_step_complete=on_step_complete,
                on_tutorial_complete=on_tutorial_complete
            )

            if task_id:
                task_ids[index] = task_id
                logger.info(f"Запущен туториал на эмуляторе {index} (ADB ID: {adb_id}) с задачей {task_id}")
            else:
                logger.error(f"Не удалось запустить туториал на эмуляторе {index}")

        return task_ids