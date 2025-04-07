import json
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Union, Tuple, Optional, Callable
from ..core.adb_controller import ADBController
from ..core.image_processor import ImageProcessor
from .logger import get_logger

logger = get_logger(__name__)


class GameTester:
    """
    Инструмент для тестирования отдельных частей игры и записи последовательности действий.
    """

    def __init__(self, adb_controller: ADBController, image_processor: ImageProcessor):
        """
        Инициализация тестера игры.

        Args:
            adb_controller: Контроллер ADB для управления эмулятором
            image_processor: Обработчик изображений для поиска на экране
        """
        self.adb = adb_controller
        self.image_processor = image_processor
        self.recording = False
        self.actions = []  # Список записанных действий
        self.screenshot_history = []  # История скриншотов

    def start_recording(self):
        """
        Начать запись последовательности действий.
        """
        self.recording = True
        self.actions = []
        self.screenshot_history = []
        logger.info("Начата запись последовательности действий")

    def stop_recording(self) -> List[Dict[str, Any]]:
        """
        Остановить запись последовательности действий.

        Returns:
            Список записанных действий
        """
        self.recording = False
        logger.info(f"Остановлена запись последовательности действий. Записано {len(self.actions)} действий.")
        return self.actions

    def save_recording(self, file_path: str) -> bool:
        """
        Сохранить записанную последовательность действий в файл.

        Args:
            file_path: Путь к файлу для сохранения

        Returns:
            True если сохранение успешно, иначе False
        """
        try:
            # Преобразуем numpy массивы в списки для сохранения в JSON
            cleaned_actions = []
            for action in self.actions:
                cleaned_action = dict(action)
                if "screenshot" in cleaned_action:
                    del cleaned_action["screenshot"]  # Не сохраняем скриншоты в JSON
                cleaned_actions.append(cleaned_action)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_actions, f, indent=4, ensure_ascii=False)

            logger.info(f"Последовательность действий сохранена в файл: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении последовательности действий: {e}")
            return False

    def load_recording(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Загрузить последовательность действий из файла.

        Args:
            file_path: Путь к файлу с записанной последовательностью

        Returns:
            Список загруженных действий
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.actions = json.load(f)

            logger.info(f"Загружена последовательность действий из файла: {file_path}, {len(self.actions)} действий")
            return self.actions
        except Exception as e:
            logger.error(f"Ошибка при загрузке последовательности действий: {e}")
            return []

    def play_recording(self, speed_factor: float = 1.0) -> bool:
        """
        Воспроизвести записанную последовательность действий.

        Args:
            speed_factor: Коэффициент скорости воспроизведения (1.0 - нормальная скорость)

        Returns:
            True если воспроизведение успешно, иначе False
        """
        if not self.actions:
            logger.warning("Нет записанных действий для воспроизведения")
            return False

        logger.info(f"Начато воспроизведение {len(self.actions)} действий со скоростью {speed_factor}")

        try:
            for i, action in enumerate(self.actions):
                logger.debug(f"Выполнение действия {i + 1}/{len(self.actions)}: {action['type']}")

                if action["type"] == "tap":
                    self.adb.tap(action["x"], action["y"])
                elif action["type"] == "swipe":
                    self.adb.swipe(
                        action["start_x"], action["start_y"],
                        action["end_x"], action["end_y"],
                        int(action["duration_ms"] / speed_factor)
                    )
                elif action["type"] == "complex_swipe":
                    self.adb.complex_swipe(
                        action["points"],
                        int(action["duration_ms"] / speed_factor)
                    )
                elif action["type"] == "wait":
                    time.sleep(action["duration"] / speed_factor)
                elif action["type"] == "key":
                    self.adb.press_key(action["key_code"])
                elif action["type"] == "esc":
                    self.adb.press_esc()

                # Выполняем задержку между действиями, если она указана
                if "delay_after" in action:
                    time.sleep(action["delay_after"] / speed_factor)

            logger.info("Воспроизведение последовательности действий завершено успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка при воспроизведении последовательности действий: {e}")
            return False

    def record_tap(self, x: int, y: int, description: str = None):
        """
        Записать действие клика.

        Args:
            x: Координата x
            y: Координата y
            description: Описание действия
        """
        # Выполняем клик
        self.adb.tap(x, y)

        # Если идет запись, сохраняем действие
        if self.recording:
            screenshot = self.adb.get_screenshot()
            action = {
                "type": "tap",
                "x": x,
                "y": y,
                "timestamp": time.time(),
                "description": description,
                "screenshot": screenshot,  # Сохраняем скриншот для анализа
                "delay_after": 0.5  # Стандартная задержка после клика
            }
            self.actions.append(action)
            self.screenshot_history.append(screenshot)
            logger.debug(f"Записан клик по координатам ({x}, {y})")

    def record_swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
                     duration_ms: int = 300, description: str = None):
        """
        Записать действие свайпа.

        Args:
            start_x: Начальная координата x
            start_y: Начальная координата y
            end_x: Конечная координата x
            end_y: Конечная координата y
            duration_ms: Длительность свайпа в миллисекундах
            description: Описание действия
        """
        # Выполняем свайп
        self.adb.swipe(start_x, start_y, end_x, end_y, duration_ms)

        # Если идет запись, сохраняем действие
        if self.recording:
            screenshot = self.adb.get_screenshot()
            action = {
                "type": "swipe",
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "duration_ms": duration_ms,
                "timestamp": time.time(),
                "description": description,
                "screenshot": screenshot,
                "delay_after": 1.0  # Стандартная задержка после свайпа
            }
            self.actions.append(action)
            self.screenshot_history.append(screenshot)
            logger.debug(f"Записан свайп от ({start_x}, {start_y}) к ({end_x}, {end_y})")

    def record_complex_swipe(self, points: List[Tuple[int, int]],
                             duration_ms: int = 800, description: str = None):
        """
        Записать действие сложного свайпа через несколько точек.

        Args:
            points: Список точек [(x1, y1), (x2, y2), ...]
            duration_ms: Общая длительность свайпа в миллисекундах
            description: Описание действия
        """
        # Выполняем сложный свайп
        self.adb.complex_swipe(points, duration_ms)

        # Если идет запись, сохраняем действие
        if self.recording:
            screenshot = self.adb.get_screenshot()
            action = {
                "type": "complex_swipe",
                "points": points,
                "duration_ms": duration_ms,
                "timestamp": time.time(),
                "description": description,
                "screenshot": screenshot,
                "delay_after": 1.5  # Стандартная задержка после сложного свайпа
            }
            self.actions.append(action)
            self.screenshot_history.append(screenshot)
            logger.debug(f"Записан сложный свайп через {len(points)} точек")

    def record_wait(self, duration: float, description: str = None):
        """
        Записать действие ожидания.

        Args:
            duration: Длительность ожидания в секундах
            description: Описание действия
        """
        # Выполняем ожидание
        time.sleep(duration)

        # Если идет запись, сохраняем действие
        if self.recording:
            screenshot = self.adb.get_screenshot()
            action = {
                "type": "wait",
                "duration": duration,
                "timestamp": time.time(),
                "description": description,
                "screenshot": screenshot,
                "delay_after": 0.0  # Нет дополнительной задержки после ожидания
            }
            self.actions.append(action)
            self.screenshot_history.append(screenshot)
            logger.debug(f"Записано ожидание {duration} секунд")

    def record_key_press(self, key_code: int, description: str = None):
        """
        Записать нажатие клавиши.

        Args:
            key_code: Код клавиши
            description: Описание действия
        """
        # Выполняем нажатие клавиши
        self.adb.press_key(key_code)

        # Если идет запись, сохраняем действие
        if self.recording:
            screenshot = self.adb.get_screenshot()
            action = {
                "type": "key",
                "key_code": key_code,
                "timestamp": time.time(),
                "description": description,
                "screenshot": screenshot,
                "delay_after": 0.5  # Стандартная задержка после нажатия клавиши
            }
            self.actions.append(action)
            self.screenshot_history.append(screenshot)
            logger.debug(f"Записано нажатие клавиши с кодом {key_code}")

    def record_esc_press(self, description: str = None):
        """
        Записать нажатие клавиши ESC.

        Args:
            description: Описание действия
        """
        # Выполняем нажатие ESC
        self.adb.press_esc()

        # Если идет запись, сохраняем действие
        if self.recording:
            screenshot = self.adb.get_screenshot()
            action = {
                "type": "esc",
                "timestamp": time.time(),
                "description": description,
                "screenshot": screenshot,
                "delay_after": 0.5  # Стандартная задержка после нажатия ESC
            }
            self.actions.append(action)
            self.screenshot_history.append(screenshot)
            logger.debug("Записано нажатие клавиши ESC")

    def wait_and_click_on_image(self, image_name: str, timeout: float = 10.0,
                                interval: float = 0.5, threshold: float = 0.8,
                                description: str = None) -> bool:
        """
        Ожидание появления изображения и клик по нему с записью действия.

        Args:
            image_name: Имя изображения для поиска
            timeout: Максимальное время ожидания в секундах
            interval: Интервал между проверками в секундах
            threshold: Порог сходства
            description: Описание действия

        Returns:
            True если изображение найдено и клик выполнен, иначе False
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            screenshot = self.adb.get_screenshot()
            template_match = self.image_processor.find_template(
                screenshot, image_name, threshold
            )

            if template_match:
                # Получаем координаты центра
                x, y = self.image_processor.center_of_template(template_match)

                # Выполняем клик
                self.adb.tap(x, y)

                # Если идет запись, сохраняем действие
                if self.recording:
                    action = {
                        "type": "tap",
                        "x": x,
                        "y": y,
                        "timestamp": time.time(),
                        "description": description or f"Клик по изображению {image_name}",
                        "image_name": image_name,
                        "threshold": threshold,
                        "screenshot": screenshot,
                        "delay_after": 0.5  # Стандартная задержка после клика
                    }
                    self.actions.append(action)
                    self.screenshot_history.append(screenshot)
                    logger.debug(f"Записан клик по изображению {image_name} на координатах ({x}, {y})")

                return True

            time.sleep(interval)

        logger.warning(f"Изображение {image_name} не найдено после {timeout} секунд ожидания")
        return False

    def find_and_analyze_template(self, template_name: str, threshold: float = 0.8,
                                  preprocess_types: List[str] = None,
                                  scale_variations: List[float] = None) -> Dict[str, Any]:
        """
        Найти и проанализировать шаблон на текущем экране.

        Args:
            template_name: Имя шаблона для поиска
            threshold: Порог сходства
            preprocess_types: Список методов предобработки
            scale_variations: Список вариаций масштаба

        Returns:
            Словарь с результатами анализа
        """
        screenshot = self.adb.get_screenshot()

        # Если не указаны методы предобработки, используем все доступные
        if preprocess_types is None:
            preprocess_types = ["default", "enhance", "edges", "hsv"]

        # Если не указаны вариации масштаба, используем несколько
        if scale_variations is None:
            scale_variations = [0.9, 0.95, 1.0, 1.05, 1.1]

        results = {}

        # Перебираем все комбинации методов предобработки и масштабов
        for preprocess_type in preprocess_types:
            for scale in scale_variations:
                # Предобрабатываем скриншот
                processed_screenshot = self.image_processor.preprocess_image(screenshot, preprocess_type)

                # Масштабируем шаблон
                template = self.image_processor.templates.get(template_name)
                if template is None:
                    continue

                scaled_template = self.image_processor.scale_image(template, scale)

                # Проверяем, что масштабированный шаблон не больше скриншота
                if (scaled_template.shape[0] > processed_screenshot.shape[0] or
                        scaled_template.shape[1] > processed_screenshot.shape[1]):
                    continue

                # Поиск шаблона
                try:
                    result = cv2.matchTemplate(processed_screenshot, scaled_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                    key = f"{preprocess_type}_{scale:.2f}"
                    results[key] = {
                        "preprocess_type": preprocess_type,
                        "scale": scale,
                        "max_val": max_val,
                        "location": max_loc,
                        "dimensions": (scaled_template.shape[1], scaled_template.shape[0]),
                        "found": max_val >= threshold
                    }

                except Exception as e:
                    logger.error(f"Ошибка при анализе шаблона {template_name} "
                                 f"с предобработкой {preprocess_type} и масштабом {scale}: {e}")

        # Находим лучший результат
        best_result = None
        best_val = -1

        for key, result in results.items():
            if result["max_val"] > best_val:
                best_val = result["max_val"]
                best_result = result

        if best_result:
            best_result["best"] = True

        return {
            "template_name": template_name,
            "results": results,
            "best_result": best_result,
            "found": best_val >= threshold,
            "threshold": threshold,
            "screenshot": screenshot
        }

    def generate_sequence_for_tutorial_step(self, step_id: str) -> List[Dict[str, Any]]:
        """
        Сгенерировать последовательность действий для конкретного шага туториала.

        Args:
            step_id: Идентификатор шага туториала

        Returns:
            Список действий для шага
        """
        # Определяем действия в зависимости от шага
        if step_id.startswith("step"):
            try:
                step_num = int(step_id[4:])

                # Шаги из ТЗ
                if step_num == 1:  # Клик по иконке профиля
                    return [{
                        "type": "tap",
                        "x": 54,
                        "y": 55,
                        "description": "Клик по иконке профиля",
                        "delay_after": 1.0
                    }]
                elif step_num == 2:  # Клик по иконке настроек
                    return [{
                        "type": "tap",
                        "x": 1073,
                        "y": 35,
                        "description": "Клик по иконке настроек",
                        "delay_after": 1.0
                    }]
                # ... и так далее для всех шагов

            except ValueError:
                pass

        logger.warning(f"Шаблонная последовательность для шага {step_id} не определена")
        return []