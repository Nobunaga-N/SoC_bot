import os
import sys
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QPushButton, QSpinBox, QComboBox,
    QListWidget, QListWidgetItem, QCheckBox, QGroupBox,
    QFormLayout, QTextEdit, QSplitter, QMessageBox,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QIcon, QTextCursor

from ..core.adb_controller import ADBController
from ..core.image_processor import ImageProcessor
from ..core.emulator_manager import EmulatorManager
from ..tutorial.tutorial_engine import TutorialEngine
from ..tutorial.tutorial_steps import create_tutorial_steps
from ..utils.logger import get_logger, add_ui_logger, remove_ui_logger
from .ui_factory import UIFactory
from .styles import STYLES

logger = get_logger(__name__)


class BotWorker(QThread):
    """
    Рабочий поток для выполнения операций бота.
    """
    step_completed = pyqtSignal(str, bool)
    tutorial_completed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, emulator_id, assets_path, server_range):
        super().__init__()
        self.emulator_id = emulator_id
        self.assets_path = assets_path
        self.server_range = server_range
        self.stop_flag = False
        self.tutorial_engine = None

    def run(self):
        try:
            # Инициализация контроллеров
            adb = ADBController(self.emulator_id)
            img_processor = ImageProcessor(self.assets_path)

            # Создание движка туториала
            self.tutorial_engine = TutorialEngine(
                adb_controller=adb,
                image_processor=img_processor,
                server_range=self.server_range,
                on_step_complete=lambda step_id, success: self.step_completed.emit(step_id, success),
                on_tutorial_complete=lambda success: self.tutorial_completed.emit(success)
            )

            # Загрузка шагов туториала
            steps = create_tutorial_steps(self.tutorial_engine)
            self.tutorial_engine.steps = steps

            # Запуск туториала
            self.tutorial_engine.start()

            # Ожидаем завершения или остановки
            while self.tutorial_engine.is_running() and not self.stop_flag:
                self.msleep(500)

            # Если была запрошена остановка, останавливаем движок
            if self.stop_flag and self.tutorial_engine.is_running():
                self.tutorial_engine.stop()

        except Exception as e:
            logger.error(f"Ошибка в потоке бота: {e}", exc_info=True)
            self.error_occurred.emit(str(e))

    def stop(self):
        self.stop_flag = True
        if self.tutorial_engine:
            self.tutorial_engine.stop()


class StatsTracker:
    """
    Класс для отслеживания статистики выполнения бота.
    """

    def __init__(self):
        self.total_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0
        self.start_time = None
        self.completed_servers = set()
        self.history = []  # [(timestamp, server, success)]

    def start_run(self):
        self.start_time = datetime.now()

    def end_run(self, server, success):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            self.total_runs += 1

            if success:
                self.successful_runs += 1
                self.completed_servers.add(server)
            else:
                self.failed_runs += 1

            self.history.append((datetime.now(), server, success, duration))
            self.start_time = None

    def get_success_rate(self):
        if self.total_runs == 0:
            return 0
        return (self.successful_runs / self.total_runs) * 100

    def get_average_duration(self):
        if not self.history:
            return 0

        total_duration = sum(item[3] for item in self.history)
        return total_duration / len(self.history)

    def clear(self):
        self.total_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0
        self.start_time = None
        self.completed_servers = set()
        self.history = []


class MainWindow(QMainWindow):
    """
    Главное окно приложения.
    """

    def __init__(self):
        super().__init__()

        # Инициализация менеджера эмуляторов
        self.emulator_manager = EmulatorManager()

        # Статистика
        self.stats = StatsTracker()

        # Путь к ассетам
        self.assets_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / ".." / "assets" / "images"

        # Рабочие потоки для ботов
        self.bot_workers = {}

        # Обработчик логов для UI
        self.ui_logger_handler = None

        # Инициализация UI
        self.setup_ui()

        # Загрузка списка эмуляторов
        self.refresh_emulators()

        # Запуск таймера для обновления статуса
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Обновление каждые 5 секунд

    def setup_ui(self):
        """
        Настройка пользовательского интерфейса.
        """
        self.setWindowTitle("Sea of Conquest Bot")
        self.setMinimumSize(900, 700)

        # Создание вкладок
        self.tabs = QTabWidget()

        # Создание вкладки настроек
        self.settings_tab = self.create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Настройки")

        # Создание вкладки статистики
        self.stats_tab = self.create_stats_tab()
        self.tabs.addTab(self.stats_tab, "Статистика")

        # Создание вкладки логов
        self.logs_tab = self.create_logs_tab()
        self.tabs.addTab(self.logs_tab, "Логи")

        # Установка вкладок как центрального виджета
        self.setCentralWidget(self.tabs)

        # Подключение логов к UI
        self.setup_ui_logger()

        # Применение стилей
        self.apply_styles()

    def apply_styles(self):
        """
        Применение стилей к интерфейсу.
        """
        self.setStyleSheet(STYLES)

    def create_settings_tab(self):
        """
        Создание вкладки настроек.

        Returns:
            Виджет вкладки настроек
        """
        tab = QWidget()
        layout = QVBoxLayout()

        # Группа настроек эмуляторов
        emulator_group = QGroupBox("Настройки эмуляторов")
        emulator_layout = QVBoxLayout()

        # Комбо-бокс для выбора пути к LDPlayer
        ldpath_layout = QHBoxLayout()
        ldpath_layout.addWidget(QLabel("Путь к LDPlayer:"))

        self.ldplayer_path_combo = QComboBox()
        self.ldplayer_path_combo.setEditable(True)
        self.ldplayer_path_combo.addItems([
            "C:/Program Files/LDPlayer/LDPlayer9",
            "C:/LDPlayer/LDPlayer9",
            "D:/LDPlayer/LDPlayer9"
        ])
        ldpath_layout.addWidget(self.ldplayer_path_combo, 1)

        self.set_ldpath_btn = QPushButton("Установить")
        self.set_ldpath_btn.clicked.connect(self.set_ldplayer_path)
        ldpath_layout.addWidget(self.set_ldpath_btn)

        emulator_layout.addLayout(ldpath_layout)

        # Список эмуляторов
        emulator_layout.addWidget(QLabel("Доступные эмуляторы:"))

        self.emulators_list = QListWidget()
        self.emulators_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        emulator_layout.addWidget(self.emulators_list)

        # Кнопка обновления списка эмуляторов
        refresh_btn_layout = QHBoxLayout()
        self.refresh_emulators_btn = QPushButton("Обновить список")
        self.refresh_emulators_btn.clicked.connect(self.refresh_emulators)
        refresh_btn_layout.addWidget(self.refresh_emulators_btn)

        # Кнопка запуска выбранных эмуляторов
        self.start_emulators_btn = QPushButton("Запустить выбранные")
        self.start_emulators_btn.clicked.connect(self.start_selected_emulators)
        refresh_btn_layout.addWidget(self.start_emulators_btn)

        # Кнопка остановки выбранных эмуляторов
        self.stop_emulators_btn = QPushButton("Остановить выбранные")
        self.stop_emulators_btn.clicked.connect(self.stop_selected_emulators)
        refresh_btn_layout.addWidget(self.stop_emulators_btn)

        emulator_layout.addLayout(refresh_btn_layout)
        emulator_group.setLayout(emulator_layout)

        layout.addWidget(emulator_group)

        # Группа настроек сервера
        server_group = QGroupBox("Настройки серверов")
        server_layout = QFormLayout()

        self.start_server_spin = QSpinBox()
        self.start_server_spin.setRange(1, 600)
        self.start_server_spin.setValue(1)
        server_layout.addRow("Начальный сервер:", self.start_server_spin)

        self.end_server_spin = QSpinBox()
        self.end_server_spin.setRange(1, 600)
        self.end_server_spin.setValue(10)
        server_layout.addRow("Конечный сервер:", self.end_server_spin)

        # Опции для сезонов
        self.season_combo = QComboBox()
        self.season_combo.addItems(["Все сезоны", "S1", "S2", "S3", "S4", "S5", "X1", "X2", "X3"])
        self.season_combo.currentIndexChanged.connect(self.update_server_range_from_season)
        server_layout.addRow("Сезон:", self.season_combo)

        server_group.setLayout(server_layout)
        layout.addWidget(server_group)

        # Кнопки управления ботом
        bot_control_layout = QHBoxLayout()

        self.start_bot_btn = QPushButton("Запустить бота")
        self.start_bot_btn.clicked.connect(self.start_bot)
        bot_control_layout.addWidget(self.start_bot_btn)

        self.stop_bot_btn = QPushButton("Остановить бота")
        self.stop_bot_btn.clicked.connect(self.stop_bot)
        self.stop_bot_btn.setEnabled(False)
        bot_control_layout.addWidget(self.stop_bot_btn)

        layout.addLayout(bot_control_layout)

        # Статус выполнения
        status_group = QGroupBox("Статус выполнения")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("Бот не запущен")
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        tab.setLayout(layout)
        return tab

    def create_stats_tab(self):
        """
        Создание вкладки статистики.

        Returns:
            Виджет вкладки статистики
        """
        tab = QWidget()
        layout = QVBoxLayout()

        # Общая статистика
        stats_group = QGroupBox("Общая статистика")
        stats_layout = QFormLayout()

        self.total_runs_label = QLabel("0")
        stats_layout.addRow("Всего запусков:", self.total_runs_label)

        self.success_runs_label = QLabel("0")
        stats_layout.addRow("Успешных запусков:", self.success_runs_label)

        self.failed_runs_label = QLabel("0")
        stats_layout.addRow("Неудачных запусков:", self.failed_runs_label)

        self.success_rate_label = QLabel("0%")
        stats_layout.addRow("Процент успеха:", self.success_rate_label)

        self.avg_duration_label = QLabel("0 сек")
        stats_layout.addRow("Среднее время выполнения:", self.avg_duration_label)

        self.completed_servers_label = QLabel("0")
        stats_layout.addRow("Пройдено серверов:", self.completed_servers_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Таблица с историей
        history_group = QGroupBox("История выполнения")
        history_layout = QVBoxLayout()

        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["Время", "Сервер", "Статус", "Длительность (сек)"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self.history_table)

        # Кнопка очистки статистики
        clear_btn_layout = QHBoxLayout()
        clear_btn_layout.addStretch()

        self.clear_stats_btn = QPushButton("Очистить статистику")
        self.clear_stats_btn.clicked.connect(self.clear_statistics)
        clear_btn_layout.addWidget(self.clear_stats_btn)

        history_layout.addLayout(clear_btn_layout)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        tab.setLayout(layout)
        return tab

    def create_logs_tab(self):
        """
        Создание вкладки логов.

        Returns:
            Виджет вкладки логов
        """
        tab = QWidget()
        layout = QVBoxLayout()

        # Текстовое поле для логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Кнопки управления логами
        log_btns_layout = QHBoxLayout()
        log_btns_layout.addStretch()

        self.clear_logs_btn = QPushButton("Очистить логи")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        log_btns_layout.addWidget(self.clear_logs_btn)

        layout.addLayout(log_btns_layout)

        tab.setLayout(layout)
        return tab

    def setup_ui_logger(self):
        """
        Настройка логгера для отображения в UI.
        """
        self.ui_logger_handler = add_ui_logger(self.handle_log_message)

    def handle_log_message(self, message, level):
        """
        Обработка сообщения лога для отображения в UI.

        Args:
            message: Текст сообщения
            level: Уровень важности сообщения
        """
        # Определение цвета в зависимости от уровня важности
        color = QColor(Qt.GlobalColor.black)

        if level >= 40:  # ERROR и выше
            color = QColor(Qt.GlobalColor.red)
        elif level >= 30:  # WARNING
            color = QColor(Qt.GlobalColor.darkYellow)
        elif level >= 20:  # INFO
            color = QColor(Qt.GlobalColor.blue)

        # Добавление сообщения в текстовое поле
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.setTextColor(color)
        self.log_text.insertPlainText(message + "\n")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def clear_logs(self):
        """
        Очистка текстового поля с логами.
        """
        self.log_text.clear()

    def set_ldplayer_path(self):
        """
        Установка пути к LDPlayer.
        """
        path = self.ldplayer_path_combo.currentText()
        success = self.emulator_manager.set_ldplayer_path(path)

        if success:
            self.refresh_emulators()
            QMessageBox.information(self, "Успех", "Путь к LDPlayer успешно установлен.")
        else:
            QMessageBox.warning(self, "Ошибка",
                                "Неверный путь к LDPlayer. Убедитесь, что директория существует и содержит ldconsole.exe.")

    def refresh_emulators(self):
        """
        Обновление списка доступных эмуляторов.
        """
        self.emulators_list.clear()

        emulators = self.emulator_manager.list_emulators()

        for emu in emulators:
            item = QListWidgetItem(f"{emu['name']} (Индекс: {emu['index']}, Статус: {emu['status']})")
            item.setData(Qt.ItemDataRole.UserRole, emu['index'])

            # Раскрашиваем в зависимости от статуса
            if emu['status'] == 'running':
                item.setForeground(QColor(Qt.GlobalColor.green))
            else:
                item.setForeground(QColor(Qt.GlobalColor.gray))

            self.emulators_list.addItem(item)

    def start_selected_emulators(self):
        """
        Запуск выбранных эмуляторов.
        """
        selected_items = self.emulators_list.selectedItems()

        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Не выбрано ни одного эмулятора.")
            return

        for item in selected_items:
            emulator_index = item.data(Qt.ItemDataRole.UserRole)

            # Запускаем эмулятор в отдельном потоке
            def start_emulator_thread(index):
                success = self.emulator_manager.start_emulator(index)
                if success:
                    logger.info(f"Эмулятор {index} успешно запущен")
                else:
                    logger.error(f"Не удалось запустить эмулятор {index}")
                # Обновляем список в основном потоке
                QTimer.singleShot(1000, self.refresh_emulators)

            # Создаем и запускаем поток
            thread = QThread()
            thread.run = lambda idx=emulator_index: start_emulator_thread(idx)
            thread.start()

    def stop_selected_emulators(self):
        """
        Остановка выбранных эмуляторов.
        """
        selected_items = self.emulators_list.selectedItems()

        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Не выбрано ни одного эмулятора.")
            return

        for item in selected_items:
            emulator_index = item.data(Qt.ItemDataRole.UserRole)

            # Останавливаем эмулятор в отдельном потоке
            def stop_emulator_thread(index):
                success = self.emulator_manager.stop_emulator(index)
                if success:
                    logger.info(f"Эмулятор {index} успешно остановлен")
                else:
                    logger.error(f"Не удалось остановить эмулятор {index}")
                # Обновляем список в основном потоке
                QTimer.singleShot(1000, self.refresh_emulators)

            # Создаем и запускаем поток
            thread = QThread()
            thread.run = lambda idx=emulator_index: stop_emulator_thread(idx)
            thread.start()

    def update_server_range_from_season(self):
        """
        Обновление диапазона серверов на основе выбранного сезона.
        """
        season = self.season_combo.currentText()

        if season == "Все сезоны":
            self.start_server_spin.setValue(1)
            self.end_server_spin.setValue(600)
        elif season == "S1":
            self.start_server_spin.setValue(577)
            self.end_server_spin.setValue(600)
        elif season == "S2":
            self.start_server_spin.setValue(541)
            self.end_server_spin.setValue(576)
        elif season == "S3":
            self.start_server_spin.setValue(505)
            self.end_server_spin.setValue(540)
        elif season == "S4":
            self.start_server_spin.setValue(481)
            self.end_server_spin.setValue(504)
        elif season == "S5":
            self.start_server_spin.setValue(433)
            self.end_server_spin.setValue(480)
        elif season == "X1":
            self.start_server_spin.setValue(409)
            self.end_server_spin.setValue(432)
        elif season == "X2":
            self.start_server_spin.setValue(266)
            self.end_server_spin.setValue(407)
        elif season == "X3":
            self.start_server_spin.setValue(1)
            self.end_server_spin.setValue(264)

    def start_bot(self):
        """
        Запуск бота на выбранных эмуляторах.
        """
        selected_items = self.emulators_list.selectedItems()

        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Не выбрано ни одного эмулятора.")
            return

        start_server = self.start_server_spin.value()
        end_server = self.end_server_spin.value()

        if start_server > end_server:
            QMessageBox.warning(self, "Предупреждение", "Начальный сервер должен быть меньше или равен конечному.")
            return

        # Получаем ADB ID для каждого выбранного эмулятора
        for item in selected_items:
            emulator_index = item.data(Qt.ItemDataRole.UserRole)
            emulator_name = item.text().split(" (")[0]

            # Проверяем, запущен ли эмулятор
            if not self.emulator_manager.is_emulator_running(emulator_index):
                logger.warning(f"Эмулятор {emulator_name} не запущен. Пропускаем.")
                continue

            # Получаем ADB ID
            adb_id = self.emulator_manager.get_emulator_adb_id(emulator_index)

            if not adb_id:
                logger.error(f"Не удалось получить ADB ID для эмулятора {emulator_name}")
                continue

            logger.info(f"Запуск бота для эмулятора {emulator_name} (ADB ID: {adb_id})")

            # Запускаем бота в отдельном потоке
            worker = BotWorker(
                emulator_id=adb_id,
                assets_path=self.assets_path,
                server_range=(start_server, end_server)
            )

            # Подключаем сигналы
            worker.step_completed.connect(lambda step_id, success, emu_idx=emulator_index:
                                          self.handle_step_completed(emu_idx, step_id, success))
            worker.tutorial_completed.connect(lambda success, emu_idx=emulator_index:
                                              self.handle_tutorial_completed(emu_idx, success))
            worker.error_occurred.connect(lambda error, emu_idx=emulator_index:
                                          self.handle_error(emu_idx, error))

            # Сохраняем и запускаем поток
            self.bot_workers[emulator_index] = worker
            worker.start()

            # Обновляем статистику
            self.stats.start_run()

        # Обновляем UI
        self.start_bot_btn.setEnabled(False)
        self.stop_bot_btn.setEnabled(True)
        self.status_label.setText("Бот запущен")
        self.update_statistics()

    def stop_bot(self):
        """
        Остановка бота на всех эмуляторах.
        """
        if not self.bot_workers:
            logger.warning("Нет запущенных ботов для остановки")
            return

        for emulator_index, worker in self.bot_workers.items():
            logger.info(f"Остановка бота для эмулятора {emulator_index}")
            worker.stop()

        # Обновляем UI
        self.start_bot_btn.setEnabled(True)
        self.stop_bot_btn.setEnabled(False)
        self.status_label.setText("Бот остановлен")

    def handle_step_completed(self, emulator_index, step_id, success):
        """
        Обработка завершения шага туториала.

        Args:
            emulator_index: Индекс эмулятора
            step_id: ID шага
            success: Флаг успешного выполнения
        """
        logger.info(f"Эмулятор {emulator_index}: Шаг {step_id} {'выполнен успешно' if success else 'не выполнен'}")

        # Обновляем прогресс бар
        if step_id.startswith("step"):
            try:
                step_num = int(step_id[4:])
                # В ТЗ указано 125 шагов
                progress = min(100, int((step_num / 126) * 100))
                self.progress_bar.setValue(progress)
            except ValueError:
                pass

    def handle_tutorial_completed(self, emulator_index, success):
        """
        Обработка завершения туториала.

        Args:
            emulator_index: Индекс эмулятора
            success: Флаг успешного выполнения
        """
        logger.info(f"Эмулятор {emulator_index}: Туториал {'успешно завершен' if success else 'не завершен'}")

        # Очищаем рабочий поток
        if emulator_index in self.bot_workers:
            worker = self.bot_workers.pop(emulator_index)
            worker.deleteLater()

        # Обновляем статистику
        start_server = self.start_server_spin.value()
        self.stats.end_run(start_server, success)
        self.update_statistics()

        # Если все боты завершили работу, обновляем UI
        if not self.bot_workers:
            self.start_bot_btn.setEnabled(True)
            self.stop_bot_btn.setEnabled(False)
            self.status_label.setText("Бот не запущен")
            self.progress_bar.setValue(0)

    def handle_error(self, emulator_index, error):
        """
        Обработка ошибки в рабочем потоке.

        Args:
            emulator_index: Индекс эмулятора
            error: Текст ошибки
        """
        logger.error(f"Эмулятор {emulator_index}: Ошибка: {error}")

        # Очищаем рабочий поток
        if emulator_index in self.bot_workers:
            worker = self.bot_workers.pop(emulator_index)
            worker.deleteLater()

        # Обновляем статистику
        start_server = self.start_server_spin.value()
        self.stats.end_run(start_server, False)
        self.update_statistics()

        # Если все боты завершили работу, обновляем UI
        if not self.bot_workers:
            self.start_bot_btn.setEnabled(True)
            self.stop_bot_btn.setEnabled(False)
            self.status_label.setText("Бот не запущен")
            self.progress_bar.setValue(0)

    def update_status(self):
        """
        Обновление статуса эмуляторов.
        """
        # Обновляем список эмуляторов
        self.refresh_emulators()

    def update_statistics(self):
        """
        Обновление отображения статистики.
        """
        # Обновляем метки с основной статистикой
        self.total_runs_label.setText(str(self.stats.total_runs))
        self.success_runs_label.setText(str(self.stats.successful_runs))
        self.failed_runs_label.setText(str(self.stats.failed_runs))
        self.success_rate_label.setText(f"{self.stats.get_success_rate():.1f}%")
        self.avg_duration_label.setText(f"{self.stats.get_average_duration():.1f} сек")
        self.completed_servers_label.setText(str(len(self.stats.completed_servers)))

        # Обновляем таблицу с историей
        self.update_history_table()

    def update_history_table(self):
        """
        Обновление таблицы с историей выполнения.
        """
        self.history_table.setRowCount(0)  # Очищаем таблицу

        for i, (timestamp, server, success, duration) in enumerate(self.stats.history):
            self.history_table.insertRow(i)

            # Время
            time_item = QTableWidgetItem(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            self.history_table.setItem(i, 0, time_item)

            # Сервер
            server_item = QTableWidgetItem(str(server))
            self.history_table.setItem(i, 1, server_item)

            # Статус
            status_item = QTableWidgetItem("Успех" if success else "Ошибка")
            status_item.setForeground(QColor(Qt.GlobalColor.green if success else Qt.GlobalColor.red))
            self.history_table.setItem(i, 2, status_item)

            # Длительность
            duration_item = QTableWidgetItem(f"{duration:.1f}")
            self.history_table.setItem(i, 3, duration_item)

    def clear_statistics(self):
        """
        Очистка статистики.
        """
        self.stats.clear()
        self.update_statistics()

    def closeEvent(self, event):
        """
        Обработка закрытия окна приложения.

        Args:
            event: Событие закрытия
        """
        # Останавливаем всех ботов
        for worker in self.bot_workers.values():
            worker.stop()

        # Удаляем обработчик логов
        if self.ui_logger_handler:
            remove_ui_logger(self.ui_logger_handler)

        event.accept()