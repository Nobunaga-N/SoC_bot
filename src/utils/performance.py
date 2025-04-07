import csv
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from threading import Lock
from .logger import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """
    Класс для мониторинга производительности и сбора статистики.
    """

    def __init__(self):
        """
        Инициализация монитора производительности.
        """
        self.lock = Lock()
        self.start_time = time.time()
        self.stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_duration": 0.0,
            "runs_by_server": {},
            "runs_by_emulator": {},
            "step_stats": {},
            "errors": []
        }
        self.current_runs = {}  # {run_id: {start_time, emulator_id, server, ...}}

    def start_run(self, run_id: str, emulator_id: str, server: int) -> None:
        """
        Начало выполнения прохождения туториала.

        Args:
            run_id: Уникальный идентификатор запуска
            emulator_id: Идентификатор эмулятора
            server: Номер сервера
        """
        with self.lock:
            self.current_runs[run_id] = {
                "start_time": time.time(),
                "emulator_id": emulator_id,
                "server": server,
                "steps": {},
                "current_step": None,
                "completed": False,
                "success": False,
                "duration": 0.0
            }
            logger.debug(f"Начато выполнение #{run_id} на эмуляторе {emulator_id}, сервер {server}")

    def end_run(self, run_id: str, success: bool) -> None:
        """
        Завершение выполнения прохождения туториала.

        Args:
            run_id: Уникальный идентификатор запуска
            success: Флаг успешного выполнения
        """
        with self.lock:
            if run_id not in self.current_runs:
                logger.warning(f"Попытка завершить несуществующий запуск: {run_id}")
                return

            run_info = self.current_runs[run_id]
            duration = time.time() - run_info["start_time"]
            run_info["duration"] = duration
            run_info["completed"] = True
            run_info["success"] = success

            # Обновляем общую статистику
            self.stats["total_runs"] += 1
            self.stats["total_duration"] += duration

            if success:
                self.stats["successful_runs"] += 1
            else:
                self.stats["failed_runs"] += 1

            # Обновляем статистику по серверам
            server = run_info["server"]
            if server not in self.stats["runs_by_server"]:
                self.stats["runs_by_server"][server] = {
                    "total": 0, "success": 0, "failed": 0, "total_duration": 0.0
                }
            self.stats["runs_by_server"][server]["total"] += 1
            self.stats["runs_by_server"][server]["total_duration"] += duration
            if success:
                self.stats["runs_by_server"][server]["success"] += 1
            else:
                self.stats["runs_by_server"][server]["failed"] += 1

            # Обновляем статистику по эмуляторам
            emulator_id = run_info["emulator_id"]
            if emulator_id not in self.stats["runs_by_emulator"]:
                self.stats["runs_by_emulator"][emulator_id] = {
                    "total": 0, "success": 0, "failed": 0, "total_duration": 0.0
                }
            self.stats["runs_by_emulator"][emulator_id]["total"] += 1
            self.stats["runs_by_emulator"][emulator_id]["total_duration"] += duration
            if success:
                self.stats["runs_by_emulator"][emulator_id]["success"] += 1
            else:
                self.stats["runs_by_emulator"][emulator_id]["failed"] += 1

            logger.debug(f"Завершено выполнение #{run_id} на эмуляторе {emulator_id}, "
                         f"сервер {server}, успех: {success}, длительность: {duration:.2f}с")

    def record_step(self, run_id: str, step_id: str, success: bool, duration: float) -> None:
        """
        Запись информации о выполнении шага.

        Args:
            run_id: Идентификатор запуска
            step_id: Идентификатор шага
            success: Флаг успешного выполнения
            duration: Длительность выполнения шага
        """
        with self.lock:
            if run_id not in self.current_runs:
                logger.warning(f"Попытка записать шаг для несуществующего запуска: {run_id}")
                return

            # Записываем информацию о шаге для текущего запуска
            self.current_runs[run_id]["steps"][step_id] = {
                "success": success,
                "duration": duration
            }
            self.current_runs[run_id]["current_step"] = step_id

            # Обновляем общую статистику по шагам
            if step_id not in self.stats["step_stats"]:
                self.stats["step_stats"][step_id] = {
                    "total": 0, "success": 0, "failed": 0, "total_duration": 0.0
                }
            self.stats["step_stats"][step_id]["total"] += 1
            self.stats["step_stats"][step_id]["total_duration"] += duration
            if success:
                self.stats["step_stats"][step_id]["success"] += 1
            else:
                self.stats["step_stats"][step_id]["failed"] += 1

            logger.debug(f"Записан шаг {step_id} для запуска #{run_id}, "
                         f"успех: {success}, длительность: {duration:.2f}с")

    def record_error(self, run_id: str, step_id: str, error_message: str) -> None:
        """
        Запись информации об ошибке.

        Args:
            run_id: Идентификатор запуска
            step_id: Идентификатор шага
            error_message: Сообщение об ошибке
        """
        with self.lock:
            # Записываем информацию об ошибке
            error_info = {
                "timestamp": time.time(),
                "run_id": run_id,
                "step_id": step_id,
                "message": error_message
            }
            self.stats["errors"].append(error_info)

            # Если запуск существует, записываем ошибку в его информацию
            if run_id in self.current_runs:
                if "errors" not in self.current_runs[run_id]:
                    self.current_runs[run_id]["errors"] = []
                self.current_runs[run_id]["errors"].append(error_info)

            logger.debug(f"Записана ошибка для запуска #{run_id}, шаг {step_id}: {error_message}")

    def get_run_info(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о конкретном запуске.

        Args:
            run_id: Идентификатор запуска

        Returns:
            Информация о запуске или None, если запуск не найден
        """
        with self.lock:
            if run_id in self.current_runs:
                return dict(self.current_runs[run_id])
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение текущей статистики.

        Returns:
            Словарь с текущей статистикой
        """
        with self.lock:
            stats = dict(self.stats)

            # Вычисляем дополнительные метрики
            if stats["total_runs"] > 0:
                stats["success_rate"] = (stats["successful_runs"] / stats["total_runs"]) * 100
                stats["average_duration"] = stats["total_duration"] / stats["total_runs"]
            else:
                stats["success_rate"] = 0
                stats["average_duration"] = 0

            # Добавляем информацию о проблемных шагах
            problem_steps = []
            for step_id, step_stats in stats["step_stats"].items():
                if step_stats["total"] > 0:
                    failure_rate = (step_stats["failed"] / step_stats["total"]) * 100
                    if failure_rate > 10:  # Шаги с более чем 10% ошибок
                        problem_steps.append({
                            "step_id": step_id,
                            "failure_rate": failure_rate,
                            "total_attempts": step_stats["total"]
                        })

            stats["problem_steps"] = sorted(problem_steps, key=lambda x: x["failure_rate"], reverse=True)

            return stats

    def clear_statistics(self) -> None:
        """
        Очистка всей статистики.
        """
        with self.lock:
            self.start_time = time.time()
            self.stats = {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "total_duration": 0.0,
                "runs_by_server": {},
                "runs_by_emulator": {},
                "step_stats": {},
                "errors": []
            }
            self.current_runs = {}
            logger.info("Статистика очищена")

    def export_to_csv(self, file_path: str = None) -> str:
        """
        Экспорт статистики в CSV файл.

        Args:
            file_path: Путь к файлу (если None, генерируется автоматически)

        Returns:
            Путь к сохраненному файлу
        """
        if file_path is None:
            # Генерируем имя файла на основе текущей даты и времени
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"statistics_{timestamp}.csv"

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Записываем общую статистику
                writer.writerow(["Общая статистика"])
                writer.writerow(["Всего запусков", "Успешных", "Неудачных", "Процент успеха", "Среднее время (с)"])

                stats = self.get_statistics()
                writer.writerow([
                    stats["total_runs"],
                    stats["successful_runs"],
                    stats["failed_runs"],
                    f"{stats['success_rate']:.2f}%",
                    f"{stats['average_duration']:.2f}"
                ])

                writer.writerow([])  # Пустая строка для разделения

                # Записываем статистику по серверам
                writer.writerow(["Статистика по серверам"])
                writer.writerow(["Сервер", "Всего", "Успешных", "Неудачных", "Процент успеха", "Среднее время (с)"])

                for server, server_stats in sorted(stats["runs_by_server"].items()):
                    success_rate = (server_stats["success"] / server_stats["total"] * 100) if server_stats[
                                                                                                  "total"] > 0 else 0
                    avg_duration = (server_stats["total_duration"] / server_stats["total"]) if server_stats[
                                                                                                   "total"] > 0 else 0
                    writer.writerow([
                        server,
                        server_stats["total"],
                        server_stats["success"],
                        server_stats["failed"],
                        f"{success_rate:.2f}%",
                        f"{avg_duration:.2f}"
                    ])

                writer.writerow([])  # Пустая строка для разделения

                # Записываем статистику по эмуляторам
                writer.writerow(["Статистика по эмуляторам"])
                writer.writerow(["Эмулятор", "Всего", "Успешных", "Неудачных", "Процент успеха", "Среднее время (с)"])

                for emulator, emulator_stats in sorted(stats["runs_by_emulator"].items()):
                    success_rate = (emulator_stats["success"] / emulator_stats["total"] * 100) if emulator_stats[
                                                                                                      "total"] > 0 else 0
                    avg_duration = (emulator_stats["total_duration"] / emulator_stats["total"]) if emulator_stats[
                                                                                                       "total"] > 0 else 0
                    writer.writerow([
                        emulator,
                        emulator_stats["total"],
                        emulator_stats["success"],
                        emulator_stats["failed"],
                        f"{success_rate:.2f}%",
                        f"{avg_duration:.2f}"
                    ])

                writer.writerow([])  # Пустая строка для разделения

                # Записываем статистику по шагам
                writer.writerow(["Статистика по шагам"])
                writer.writerow(["Шаг", "Всего", "Успешных", "Неудачных", "Процент успеха", "Среднее время (с)"])

                for step_id, step_stats in sorted(stats["step_stats"].items()):
                    success_rate = (step_stats["success"] / step_stats["total"] * 100) if step_stats["total"] > 0 else 0
                    avg_duration = (step_stats["total_duration"] / step_stats["total"]) if step_stats[
                                                                                               "total"] > 0 else 0
                    writer.writerow([
                        step_id,
                        step_stats["total"],
                        step_stats["success"],
                        step_stats["failed"],
                        f"{success_rate:.2f}%",
                        f"{avg_duration:.2f}"
                    ])

                writer.writerow([])  # Пустая строка для разделения

                # Записываем информацию о проблемных шагах
                writer.writerow(["Проблемные шаги (> 10% ошибок)"])
                writer.writerow(["Шаг", "Процент ошибок", "Всего попыток"])

                for step in stats["problem_steps"]:
                    writer.writerow([
                        step["step_id"],
                        f"{step['failure_rate']:.2f}%",
                        step["total_attempts"]
                    ])

            logger.info(f"Статистика экспортирована в CSV: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Ошибка при экспорте статистики в CSV: {e}")
            return None

    def export_to_json(self, file_path: str = None) -> str:
        """
        Экспорт статистики в JSON файл.

        Args:
            file_path: Путь к файлу (если None, генерируется автоматически)

        Returns:
            Путь к сохраненному файлу
        """
        if file_path is None:
            # Генерируем имя файла на основе текущей даты и времени
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"statistics_{timestamp}.json"

        try:
            stats = self.get_statistics()

            # Преобразуем временные метки в строки для JSON
            for error in stats["errors"]:
                error["timestamp"] = datetime.fromtimestamp(error["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

            # Добавляем метаинформацию
            stats["meta"] = {
                "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_runtime": time.time() - self.start_time
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4, ensure_ascii=False)

            logger.info(f"Статистика экспортирована в JSON: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Ошибка при экспорте статистики в JSON: {e}")
            return None


# Глобальный экземпляр монитора производительности
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """
    Получение глобального экземпляра монитора производительности.

    Returns:
        Глобальный экземпляр монитора производительности
    """
    return performance_monitor


class StepTimer:
    """
    Класс для замера времени выполнения шагов.
    """

    def __init__(self, run_id: str, step_id: str):
        """
        Инициализация таймера.

        Args:
            run_id: Идентификатор запуска
            step_id: Идентификатор шага
        """
        self.run_id = run_id
        self.step_id = step_id
        self.start_time = None
        self.monitor = get_performance_monitor()

    def __enter__(self):
        """
        Начало замера времени.
        """
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Окончание замера времени и запись статистики.

        Args:
            exc_type: Тип исключения (если было)
            exc_val: Значение исключения (если было)
            exc_tb: Трассировка исключения (если было)
        """
        duration = time.time() - self.start_time
        success = exc_type is None

        # Записываем информацию о шаге
        self.monitor.record_step(self.run_id, self.step_id, success, duration)

        # Если было исключение, записываем информацию об ошибке
        if exc_type is not None:
            self.monitor.record_error(self.run_id, self.step_id, str(exc_val))

        # Не подавляем исключение
        return False