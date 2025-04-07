import os
import cv2
import numpy as np
from typing import Tuple, Optional, List, Dict
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """
    Класс для обработки изображений и поиска шаблонов на скриншотах эмулятора.
    """

    def __init__(self, assets_path: str):
        """
        Инициализация обработчика изображений.

        Args:
            assets_path: Путь к директории с изображениями-шаблонами
        """
        self.assets_path = Path(assets_path)
        self.templates = {}  # Кэш для шаблонов
        self._load_templates()
        logger.info(f"Инициализация обработчика изображений, загружено {len(self.templates)} шаблонов")

    def _load_templates(self) -> None:
        """
        Загрузка всех шаблонов из директории assets в память.
        """
        if not self.assets_path.exists():
            logger.error(f"Директория с изображениями не найдена: {self.assets_path}")
            return

        for file_path in self.assets_path.glob("*.png"):
            template_name = file_path.stem
            template_img = cv2.imread(str(file_path))

            if template_img is not None:
                self.templates[template_name] = template_img
                logger.debug(f"Загружен шаблон: {template_name}, размер: {template_img.shape}")
            else:
                logger.error(f"Не удалось загрузить шаблон: {file_path}")

    def find_template(self,
                      screenshot: np.ndarray,
                      template_name: str,
                      threshold: float = 0.8) -> Optional[Tuple[int, int, int, int]]:
        """
        Поиск шаблона на скриншоте.

        Args:
            screenshot: Изображение-скриншот
            template_name: Имя шаблона для поиска (без расширения)
            threshold: Порог сходства (0.0 - 1.0)

        Returns:
            Координаты найденного шаблона (x, y, width, height) или None
        """
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

        # Проверяем, что скриншот не пустой
        if screenshot is None or screenshot.size == 0:
            logger.error("Скриншот пустой или поврежден")
            return None

        # Проверяем размеры
        if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
            logger.error(f"Шаблон {template_name} больше скриншота")
            return None

        # Поиск шаблона
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            x, y = max_loc
            h, w = template.shape[:2]
            logger.debug(f"Найден шаблон {template_name} на координатах ({x}, {y}) со сходством {max_val:.2f}")
            return (x, y, w, h)
        else:
            logger.debug(f"Шаблон {template_name} не найден (лучшее сходство: {max_val:.2f})")
            return None

    def find_all_templates(self,
                           screenshot: np.ndarray,
                           template_name: str,
                           threshold: float = 0.8) -> List[Tuple[int, int, int, int]]:
        """
        Поиск всех вхождений шаблона на скриншоте.

        Args:
            screenshot: Изображение-скриншот
            template_name: Имя шаблона для поиска (без расширения)
            threshold: Порог сходства (0.0 - 1.0)

        Returns:
            Список координат найденных шаблонов [(x, y, width, height), ...]
        """
        if template_name not in self.templates:
            template_path = self.assets_path / f"{template_name}.png"
            if template_path.exists():
                self.templates[template_name] = cv2.imread(str(template_path))
            else:
                logger.error(f"Шаблон не найден: {template_name}")
                return []

        template = self.templates[template_name]

        # Проверяем, что скриншот не пустой
        if screenshot is None or screenshot.size == 0:
            logger.error("Скриншот пустой или поврежден")
            return []

        # Проверяем размеры
        if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
            logger.error(f"Шаблон {template_name} больше скриншота")
            return []

        # Поиск шаблона
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        h, w = template.shape[:2]

        # Находим все локации выше порога
        locations = np.where(result >= threshold)

        # Преобразуем в список координат
        matches = []
        for pt in zip(*locations[::-1]):  # Разворачиваем, чтобы получить (x, y)
            matches.append((pt[0], pt[1], w, h))

        # Убираем дубликаты (близкие координаты)
        filtered_matches = []
        for match in matches:
            x1, y1 = match[0], match[1]
            is_duplicate = False

            for filtered in filtered_matches:
                x2, y2 = filtered[0], filtered[1]
                # Если точки близки друг к другу, считаем их дубликатами
                if abs(x1 - x2) < w // 2 and abs(y1 - y2) < h // 2:
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered_matches.append(match)

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
                          threshold: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        Ожидание появления шаблона на экране.

        Args:
            adb_controller: Контроллер ADB для получения скриншотов
            template_name: Имя шаблона для поиска
            timeout: Максимальное время ожидания в секундах
            interval: Интервал между проверками в секундах
            threshold: Порог сходства

        Returns:
            Координаты центра найденного шаблона или None, если шаблон не найден за отведенное время
        """
        import time

        logger.info(f"Ожидание появления шаблона {template_name} (таймаут: {timeout}с)")
        start_time = time.time()

        while time.time() - start_time < timeout:
            screenshot = adb_controller.get_screenshot()
            template_match = self.find_template(screenshot, template_name, threshold)

            if template_match:
                center = self.center_of_template(template_match)
                logger.info(f"Шаблон {template_name} найден на координатах {center}")
                return center

            time.sleep(interval)

        logger.warning(f"Шаблон {template_name} не найден после {timeout}с ожидания")
        return None

    def extract_text_from_region(self,
                                 screenshot: np.ndarray,
                                 region: Tuple[int, int, int, int]) -> str:
        """
        Извлечение текста из указанной области скриншота (для парсинга сезонов и серверов).
        Для полноценной работы требуется установка pytesseract.

        Args:
            screenshot: Изображение-скриншот
            region: Область для извлечения текста (x, y, width, height)

        Returns:
            Извлеченный текст
        """
        try:
            import pytesseract

            x, y, w, h = region
            roi = screenshot[y:y + h, x:x + w]

            # Предобработка для улучшения распознавания
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

            # Распознавание текста
            text = pytesseract.image_to_string(thresh, lang='rus+eng')
            logger.debug(f"Извлечен текст из региона {region}: {text}")
            return text.strip()

        except ImportError:
            logger.error("pytesseract не установлен. Установите его для распознавания текста")
            return ""
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста: {e}")
            return ""