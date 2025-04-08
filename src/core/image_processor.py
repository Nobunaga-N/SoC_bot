import os
import cv2
import numpy as np
from typing import Tuple, Optional, List, Dict, Any, Union
from pathlib import Path
from ..utils.logger import get_logger
from ..utils.exceptions import ImageError

logger = get_logger(__name__)


class ImageProcessor:
    """
    Класс для обработки изображений и поиска шаблонов на скриншотах эмулятора.
    Включает улучшенную предобработку изображений и адаптивный порог сходства.
    """

    def __init__(self, assets_path: str):
        """
        Инициализация обработчика изображений.

        Args:
            assets_path: Путь к директории с изображениями-шаблонами
        """
        self.assets_path = Path(assets_path)
        self.templates = {}  # Кэш для шаблонов
        self.template_info = {}  # Информация о шаблонах (размеры, особенности и т.д.)
        self._load_templates()

        # Словарь с оптимальными порогами для разных типов шаблонов
        self.template_thresholds = {
            # Общие настройки по умолчанию
            "default": 0.8,

            # Кнопки
            "skip": 0.75,  # Кнопка пропуска может иметь разные состояния
            "confirm_new_acc": 0.85,
            "start_battle": 0.82,

            # Иконки
            "open_profile": 0.70,
            "navigator": 0.85,
            "lite_apks": 0.82,
            "hero_face": 0.80,
            "upgrade_ship": 0.85,

            # Элементы игрового интерфейса
            "ship": 0.78,
            "Hell_Genry": 0.75,
            "shoot": 0.78,
            "close_menu": 0.8,
            "open_new_local_building": 0.82
        }

        # Настройки для разных разрешений
        self.resolution_map = {
            (1920, 1080): {"scale_factor": 1.0},  # Базовое разрешение
            (2400, 1080): {"scale_factor": 1.25},
            (1280, 720): {"scale_factor": 0.667},
            (2560, 1440): {"scale_factor": 1.333},
            (3840, 2160): {"scale_factor": 2.0}
        }

        # Текущее разрешение (будет определено при первом скриншоте)
        self.current_resolution = None
        self.scale_factor = 1.0

        logger.info(f"Инициализация обработчика изображений, загружено {len(self.templates)} шаблонов")

    def _load_templates(self) -> None:
        """
        Загрузка всех шаблонов из директории assets в память.
        Также анализируем и сохраняем информацию о каждом шаблоне.
        """
        if not self.assets_path.exists():
            logger.error(f"Директория с изображениями не найдена: {self.assets_path}")
            return

        for file_path in self.assets_path.glob("*.png"):
            template_name = file_path.stem
            template_img = cv2.imread(str(file_path))

            if template_img is not None:
                # Сохраняем шаблон
                self.templates[template_name] = template_img

                # Анализируем и сохраняем информацию о шаблоне
                height, width = template_img.shape[:2]
                aspect_ratio = width / height if height > 0 else 0

                # Вычисляем дополнительные характеристики шаблона
                gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
                features = {
                    "size": (width, height),
                    "aspect_ratio": aspect_ratio,
                    "mean_color": np.mean(template_img, axis=(0, 1)).tolist(),
                    "edges": cv2.Canny(gray, 100, 200),
                    "histogram": cv2.calcHist([gray], [0], None, [16], [0, 256]).flatten().tolist(),
                    "mask": None  # Маска будет создана при необходимости
                }

                # Если шаблон имеет прозрачность (4 канала), создаем маску
                if template_img.shape[2] == 4:
                    alpha_channel = template_img[:, :, 3]
                    features["mask"] = alpha_channel > 128

                self.template_info[template_name] = features

                logger.debug(f"Загружен шаблон: {template_name}, размер: {template_img.shape}")
            else:
                logger.error(f"Не удалось загрузить шаблон: {file_path}")

    def detect_resolution(self, screenshot: np.ndarray) -> Tuple[int, int]:
        """
        Определение разрешения экрана и настройка масштабирования.

        Args:
            screenshot: Изображение-скриншот

        Returns:
            Кортеж (ширина, высота)
        """
        if screenshot is None or screenshot.size == 0:
            return (0, 0)

        height, width = screenshot.shape[:2]
        resolution = (width, height)

        # Если разрешение изменилось, обновляем масштабный коэффициент
        if self.current_resolution != resolution:
            self.current_resolution = resolution

            # Находим ближайшее разрешение из известных
            closest_resolution = min(self.resolution_map.keys(),
                                     key=lambda r: abs(r[0] - width) + abs(r[1] - height))

            self.scale_factor = self.resolution_map[closest_resolution]["scale_factor"]
            logger.info(f"Обнаружено разрешение {resolution}, " +
                        f"используется масштабный коэффициент {self.scale_factor}")

        return resolution

    def preprocess_image(self, image: np.ndarray, preprocess_type: str = "default") -> np.ndarray:
        """
        Предобработка изображения для улучшения распознавания.

        Args:
            image: Исходное изображение
            preprocess_type: Тип предобработки ("default", "enhance", "edges", "hsv")

        Returns:
            Обработанное изображение
        """
        if image is None:
            return None

        if preprocess_type == "default":
            # Базовая обработка - просто возвращаем оригинал
            return image

        elif preprocess_type == "enhance":
            # Улучшение контраста и яркости
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge((l, a, b))
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        elif preprocess_type == "edges":
            # Выделение границ
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        elif preprocess_type == "hsv":
            # Преобразование в HSV для лучшего выделения цветов
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            return hsv

        else:
            logger.warning(f"Неизвестный тип предобработки: {preprocess_type}, используется стандартная")
            return image

    def scale_image(self, image: np.ndarray, scale_factor: float = None) -> np.ndarray:
        """
        Масштабирование изображения с учетом разрешения экрана.

        Args:
            image: Исходное изображение
            scale_factor: Коэффициент масштабирования (если None, используется текущий)

        Returns:
            Масштабированное изображение
        """
        if image is None:
            return None

        if scale_factor is None:
            scale_factor = self.scale_factor

        if scale_factor == 1.0:
            return image

        height, width = image.shape[:2]
        new_height = int(height * scale_factor)
        new_width = int(width * scale_factor)

        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

    def get_optimal_threshold(self, template_name: str) -> float:
        """
        Получение оптимального порога сходства для шаблона.

        Args:
            template_name: Имя шаблона

        Returns:
            Порог сходства (0.0 - 1.0)
        """
        # Если для шаблона есть индивидуальный порог, используем его
        if template_name in self.template_thresholds:
            return self.template_thresholds[template_name]

        # Иначе возвращаем порог по умолчанию
        return self.template_thresholds["default"]

    def find_template(self,
                      screenshot: np.ndarray,
                      template_name: str,
                      threshold: float = None,
                      preprocess_types: List[str] = None,
                      scale_variations: List[float] = None) -> Optional[Tuple[int, int, int, int]]:
        """
        Поиск шаблона на скриншоте с возможностью использования разных методов предобработки
        и масштабирования.

        Args:
            screenshot: Изображение-скриншот
            template_name: Имя шаблона для поиска (без расширения)
            threshold: Порог сходства (0.0 - 1.0)
            preprocess_types: Список методов предобработки для использования
            scale_variations: Список вариаций масштаба для поиска

        Returns:
            Координаты найденного шаблона (x, y, width, height) или None
        """
        if screenshot is None or screenshot.size == 0:
            logger.error("Скриншот пустой или поврежден")
            return None

        # Определяем разрешение экрана и настраиваем масштабирование
        self.detect_resolution(screenshot)

        # Если порог не указан, используем оптимальный для данного шаблона
        if threshold is None:
            threshold = self.get_optimal_threshold(template_name)

        # Если не указаны методы предобработки, используем только стандартный
        if preprocess_types is None:
            preprocess_types = ["default"]

        # Если не указаны вариации масштаба, используем текущий и +/-10%
        if scale_variations is None:
            scale_variations = [self.scale_factor, self.scale_factor * 0.9, self.scale_factor * 1.1]

        # Получаем шаблон
        if template_name not in self.templates:
            # Попробуем загрузить шаблон, если он еще не в кэше
            template_path = self.assets_path / f"{template_name}.png"
            if template_path.exists():
                self.templates[template_name] = cv2.imread(str(template_path))
                logger.debug(f"Загружен шаблон по запросу: {template_name}")
            else:
                logger.error(f"Шаблон не найден: {template_name}")
                return None

        template = self.templates[template_name]

        # Проверяем размеры
        if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
            logger.error(f"Шаблон {template_name} больше скриншота")
            return None

        best_match = None
        best_val = -1

        # Перебираем все комбинации методов предобработки и масштабов
        for preprocess_type in preprocess_types:
            processed_screenshot = self.preprocess_image(screenshot, preprocess_type)

            for scale in scale_variations:
                # Масштабируем шаблон под текущий масштаб
                scaled_template = self.scale_image(template, scale)

                # Проверяем, что масштабированный шаблон не больше скриншота
                if (scaled_template.shape[0] > processed_screenshot.shape[0] or
                        scaled_template.shape[1] > processed_screenshot.shape[1]):
                    continue

                # Поиск шаблона
                try:
                    result = cv2.matchTemplate(processed_screenshot, scaled_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                    if max_val > best_val:
                        best_val = max_val
                        x, y = max_loc
                        h, w = scaled_template.shape[:2]
                        best_match = (x, y, w, h)

                except Exception as e:
                    logger.error(f"Ошибка при поиске шаблона {template_name}: {e}")
                    continue

        # Если лучшее совпадение превышает порог, возвращаем его
        if best_val >= threshold:
            logger.debug(f"Найден шаблон {template_name} на координатах {best_match[:2]} "
                         f"со сходством {best_val:.2f} (порог: {threshold:.2f})")
            return best_match
        else:
            logger.debug(f"Шаблон {template_name} не найден "
                         f"(лучшее сходство: {best_val:.2f}, порог: {threshold:.2f})")
            return None

    def find_all_templates(self,
                           screenshot: np.ndarray,
                           template_name: str,
                           threshold: float = None,
                           preprocess_types: List[str] = None,
                           scale_variations: List[float] = None,
                           max_results: int = 10) -> List[Tuple[int, int, int, int]]:
        """
        Поиск всех вхождений шаблона на скриншоте.

        Args:
            screenshot: Изображение-скриншот
            template_name: Имя шаблона для поиска (без расширения)
            threshold: Порог сходства (0.0 - 1.0)
            preprocess_types: Список методов предобработки для использования
            scale_variations: Список вариаций масштаба для поиска
            max_results: Максимальное количество результатов

        Returns:
            Список координат найденных шаблонов [(x, y, width, height), ...]
        """
        if screenshot is None or screenshot.size == 0:
            logger.error("Скриншот пустой или поврежден")
            return []

        # Определяем разрешение экрана и настраиваем масштабирование
        self.detect_resolution(screenshot)

        # Если порог не указан, используем оптимальный для данного шаблона
        if threshold is None:
            threshold = self.get_optimal_threshold(template_name)

        # Если не указаны методы предобработки, используем только стандартный
        if preprocess_types is None:
            preprocess_types = ["default"]

        # Если не указаны вариации масштаба, используем текущий
        if scale_variations is None:
            scale_variations = [self.scale_factor]

        # Получаем шаблон
        if template_name not in self.templates:
            template_path = self.assets_path / f"{template_name}.png"
            if template_path.exists():
                self.templates[template_name] = cv2.imread(str(template_path))
            else:
                logger.error(f"Шаблон не найден: {template_name}")
                return []

        template = self.templates[template_name]

        # Проверяем размеры
        if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
            logger.error(f"Шаблон {template_name} больше скриншота")
            return []

        best_matches = []

        # Перебираем все комбинации методов предобработки и масштабов
        for preprocess_type in preprocess_types:
            processed_screenshot = self.preprocess_image(screenshot, preprocess_type)

            for scale in scale_variations:
                # Масштабируем шаблон под текущий масштаб
                scaled_template = self.scale_image(template, scale)

                # Проверяем, что масштабированный шаблон не больше скриншота
                if (scaled_template.shape[0] > processed_screenshot.shape[0] or
                        scaled_template.shape[1] > processed_screenshot.shape[1]):
                    continue

                # Поиск шаблона
                try:
                    result = cv2.matchTemplate(processed_screenshot, scaled_template, cv2.TM_CCOEFF_NORMED)
                    h, w = scaled_template.shape[:2]

                    # Находим все локации выше порога
                    locations = np.where(result >= threshold)

                    # Преобразуем в список координат
                    for pt in zip(*locations[::-1]):  # Разворачиваем, чтобы получить (x, y)
                        best_matches.append((pt[0], pt[1], w, h, result[pt[1], pt[0]]))

                except Exception as e:
                    logger.error(f"Ошибка при поиске шаблона {template_name}: {e}")
                    continue

        # Сортируем по значению совпадения
        best_matches.sort(key=lambda x: x[4], reverse=True)

        # Убираем дубликаты (близкие координаты)
        filtered_matches = []
        for match in best_matches:
            x1, y1 = match[0], match[1]
            w, h = match[2], match[3]
            is_duplicate = False

            for filtered in filtered_matches:
                x2, y2 = filtered[0], filtered[1]
                # Если точки близки друг к другу, считаем их дубликатами
                if abs(x1 - x2) < w // 2 and abs(y1 - y2) < h // 2:
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered_matches.append(match[:4])  # Отбрасываем значение совпадения

                # Ограничиваем количество результатов
                if len(filtered_matches) >= max_results:
                    break

        logger.debug(f"Найдено {len(filtered_matches)} вхождений шаблона {template_name}")
        return filtered_matches

    def center_of_template(self, template_match: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        Получить координаты центра найденного шаблона.

        Args:
            template_match: Координаты шаблона (x, y, width, height)

        Returns:
            Координаты центра (x, y)
        """
        x, y, w, h = template_match
        return (x + w // 2, y + h // 2)

    def wait_for_template(self,
                          adb_controller,
                          template_name: str,
                          timeout: float = 10.0,
                          interval: float = 0.5,
                          threshold: float = None,
                          preprocess_types: List[str] = None,
                          scale_variations: List[float] = None,
                          max_attempts: int = 20) -> Optional[Tuple[int, int]]:
        """
        Ожидание появления шаблона на экране.

        Args:
            adb_controller: Контроллер ADB для получения скриншотов
            template_name: Имя шаблона для поиска
            timeout: Максимальное время ожидания в секундах
            interval: Интервал между проверками в секундах
            threshold: Порог сходства
            preprocess_types: Список методов предобработки для использования
            scale_variations: Список вариаций масштаба для поиска
            max_attempts: Максимальное количество попыток

        Returns:
            Координаты центра найденного шаблона или None, если шаблон не найден за отведенное время
        """
        import time

        logger.info(f"Ожидание появления шаблона {template_name} (таймаут: {timeout}с)")
        start_time = time.time()
        attempts = 0

        while time.time() - start_time < timeout and attempts < max_attempts:
            try:
                screenshot = adb_controller.get_screenshot()
                template_match = self.find_template(
                    screenshot, template_name, threshold, preprocess_types, scale_variations
                )

                if template_match:
                    center = self.center_of_template(template_match)
                    logger.info(f"Шаблон {template_name} найден на координатах {center} "
                                f"(попытка {attempts + 1}, прошло {time.time() - start_time:.1f}с)")
                    return center
            except Exception as e:
                logger.error(f"Ошибка при поиске шаблона {template_name}: {e}")

            attempts += 1
            time.sleep(interval)

        logger.warning(f"Шаблон {template_name} не найден после {attempts} попыток за {time.time() - start_time:.1f}с")
        return None

    def extract_text_from_region(self,
                                 screenshot: np.ndarray,
                                 region: Tuple[int, int, int, int],
                                 preprocess: bool = True,
                                 lang: str = 'rus+eng') -> str:
        """
        Извлечение текста из указанной области скриншота (для парсинга сезонов и серверов).
        Для полноценной работы требуется установка pytesseract.

        Args:
            screenshot: Изображение-скриншот
            region: Область для извлечения текста (x, y, width, height)
            preprocess: Использовать предобработку для улучшения распознавания
            lang: Язык текста для распознавания

        Returns:
            Извлеченный текст
        """
        try:
            import pytesseract

            x, y, w, h = region
            roi = screenshot[y:y + h, x:x + w]

            if preprocess:
                # Предобработка для улучшения распознавания
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

                # Применяем гауссовское размытие для уменьшения шума
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)

                # Адаптивная бинаризация для лучшего распознавания текста разного размера и цвета
                thresh = cv2.adaptiveThreshold(
                    blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
                )

                # Морфологические операции для удаления шума и улучшения текста
                kernel = np.ones((1, 1), np.uint8)
                opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)

                # Распознавание текста с предобработанного изображения
                text = pytesseract.image_to_string(closing, lang=lang, config='--psm 6')
            else:
                # Распознавание текста без предобработки
                text = pytesseract.image_to_string(roi, lang=lang)

            # Удаляем лишние пробелы и переносы строк
            text = " ".join(text.strip().split())
            logger.debug(f"Извлечен текст из региона {region}: {text}")
            return text

        except ImportError:
            logger.error("pytesseract не установлен. Установите его для распознавания текста")
            return ""
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста: {e}")
            return ""

    def detect_season_text(self, screenshot: np.ndarray, season_regions: List[Tuple[int, int, int, int]]) -> Dict[
        str, Tuple[int, int]]:
        """
        Определение сезонов на экране.

        Args:
            screenshot: Изображение-скриншот
            season_regions: Список областей, где могут находиться сезоны [(x, y, width, height), ...]

        Returns:
            Словарь {название_сезона: координаты_центра}
        """
        seasons = {}

        for region in season_regions:
            x, y, w, h = region
            text = self.extract_text_from_region(screenshot, region)

            # Нормализуем текст для поиска сезона
            text = text.lower().replace(" ", "")

            # Ищем упоминания сезонов в тексте
            for season in ["s1", "s2", "s3", "s4", "s5", "x1", "x2", "x3"]:
                if season in text:
                    # Запоминаем центр региона для последующего клика
                    center_x = x + w // 2
                    center_y = y + h // 2
                    seasons[season.upper()] = (center_x, center_y)
                    logger.info(f"Обнаружен сезон {season.upper()} в регионе {region}, центр: ({center_x}, {center_y})")
                    break

        return seasons

    def detect_server_number(self, screenshot: np.ndarray, server_regions: List[Tuple[int, int, int, int]]) -> Dict[
        int, Tuple[int, int]]:
        """
        Определение номеров серверов на экране.

        Args:
            screenshot: Изображение-скриншот
            server_regions: Список областей, где могут находиться номера серверов [(x, y, width, height), ...]

        Returns:
            Словарь {номер_сервера: координаты_центра}
        """
        servers = {}

        for region in server_regions:
            x, y, w, h = region
            text = self.extract_text_from_region(screenshot, region)

            # Ищем цифры в тексте
            import re
            numbers = re.findall(r'\d+', text)

            if numbers:
                try:
                    server_number = int(numbers[0])
                    # Запоминаем центр региона для последующего клика
                    center_x = x + w // 2
                    center_y = y + h // 2
                    servers[server_number] = (center_x, center_y)
                    logger.info(
                        f"Обнаружен сервер #{server_number} в регионе {region}, центр: ({center_x}, {center_y})")
                except ValueError:
                    continue

        return servers