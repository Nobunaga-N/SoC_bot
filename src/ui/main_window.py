import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QPushButton, QSpinBox, QComboBox,
    QListWidget, QListWidgetItem, QCheckBox, QGroupBox,
    QFormLayout, QTextEdit, QSplitter, QMessageBox,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QIcon, QTextCursor

from ..core.adb_controller import ADBController
from ..core.image_processor import ImageProcessor
from ..core.emulator_manager import EmulatorManager
from ..tutorial.tutorial_engine import TutorialEngine
from ..tutorial.tutorial_steps import create_tutorial_steps
from ..utils.logger import get_logger, add_ui_logger, remove_ui_logger
from ..core.parallel_executor import ParallelEmulatorExecutor
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

    def __init__(self, emulator_id: str, assets_path: str, server_range: tuple):
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
    # Определение атрибутов класса для устранения предупреждений PyCharm
    emulator_manager: EmulatorManager
    stats: StatsTracker
    assets_path: Path
    parallel_executor: ParallelEmulatorExecutor
    ui_logger_handler: Any

    # Вкладки
    tabs: QTabWidget
    settings_tab: QWidget
    stats_tab: QWidget
    logs_tab: QWidget
    emulators_tab: QWidget

    # Виджеты настроек
    ldplayer_path_combo: QComboBox
    emulators_list: QListWidget
    refresh_emulators_btn: QPushButton
    start_emulators_btn: QPushButton
    stop_emulators_btn: QPushButton
    start_server_spin: QSpinBox
    end_server_spin: QSpinBox
    season_combo: QComboBox
    start_bot_btn: QPushButton
    stop_bot_btn: QPushButton
    status_label: QLabel
    progress_bar: QProgressBar

    # Виджеты статистики
    total_runs_label: QLabel
    success_runs_label: QLabel
    failed_runs_label: QLabel
    success_rate_label: QLabel
    avg_duration_label: QLabel
    completed_servers_label: QLabel
    history_table: QTableWidget
    clear_stats_btn: QPushButton

    # Виджеты логов
    log_text: QTextEdit
    clear_logs_btn: QPushButton

    # Виджеты эмуляторов
    emulators_progress_container: QLayout
    emulator_progress_bars: Dict[int, Union[QProgressBar, Dict[str, Any]]]
    emulator_status_labels: Dict[int, QLabel]
    emulators_container: QWidget
    emulators_layout: QVBoxLayout
    refresh_emulators_status_btn: QPushButton
    restart_unresponsive_btn: QPushButton
    emulators_status_table: QTableWidget

    # Вспомогательные атрибуты
    status_timer: QTimer
    bot_workers: Dict[str, BotWorker]

    def __init__(self):
        super().__init__()

        # Инициализация атрибутов с пустыми значениями для типизации
        self.bot_workers = {}

        # Инициализация менеджера эмуляторов
        self.emulator_manager = EmulatorManager()

        # Статистика
        self.stats = StatsTracker()

        # Путь к ассетам
        self.assets_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / ".." / "assets" / "images"

        # Инициализация параллельного выполнения (вместо self.bot_workers = {})
        self.parallel_executor = ParallelEmulatorExecutor(
            assets_path=str(self.assets_path),
            max_workers=None  # Автоматическое определение по количеству эмуляторов
        )

        # Обработчик логов для UI
        self.ui_logger_handler = None

        # Инициализация UI
        self.setup_ui()

        # Добавляем индикаторы прогресса для эмуляторов
        self._add_emulator_progress_indicators()

        # Инициализация элементов UI для эмуляторов
        self.initialize_emulator_ui_elements()

        # Загрузка списка эмуляторов
        self.refresh_emulators()

        # Запуск таймера для обновления статуса
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(30000)  # Обновление каждые 5 секунд

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

        # Добавляем кнопки сохранения и загрузки настроек
        settings_btn_layout = QHBoxLayout()
        save_settings_btn = QPushButton("Сохранить настройки")
        save_settings_btn.clicked.connect(self.save_settings_to_file)
        settings_btn_layout.addWidget(save_settings_btn)

        load_settings_btn = QPushButton("Загрузить настройки")
        load_settings_btn.clicked.connect(self.load_settings_from_file)
        settings_btn_layout.addWidget(load_settings_btn)

        emulator_layout.addLayout(settings_btn_layout)

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
        Обновление списка доступных эмуляторов с сохранением выбора.
        """
        # Сохраняем текущий выбор
        selected_indices = []
        for item in self.emulators_list.selectedItems():
            selected_indices.append(item.data(Qt.ItemDataRole.UserRole))

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

            # Восстанавливаем выбор
            if emu['index'] in selected_indices:
                item.setSelected(True)

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

    def _add_emulator_progress_indicators(self):
        """
        Добавить индикаторы прогресса для каждого эмулятора.
        """
        # Создаем словарь для хранения индикаторов прогресса
        self.emulator_progress_bars = {}

        # Создаем отдельную вкладку для мониторинга эмуляторов
        self.emulators_tab = QWidget()
        emulators_layout = QVBoxLayout()

        # Группа с индикаторами прогресса
        progress_group = QGroupBox("Прогресс выполнения по эмуляторам")
        progress_layout = QVBoxLayout()

        # Добавляем прокручиваемую область для индикаторов
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Этот контейнер будет хранить индикаторы
        self.emulators_progress_container = scroll_layout

        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        progress_layout.addWidget(scroll_area)

        progress_group.setLayout(progress_layout)
        emulators_layout.addWidget(progress_group)

        # Добавляем кнопки управления
        control_layout = QHBoxLayout()

        # Кнопка обновления статуса эмуляторов
        self.refresh_emulators_status_btn = QPushButton("Обновить статус")
        self.refresh_emulators_status_btn.clicked.connect(self.refresh_emulators_status)
        control_layout.addWidget(self.refresh_emulators_status_btn)

        # Кнопка перезапуска зависших эмуляторов
        self.restart_unresponsive_btn = QPushButton("Перезапустить зависшие")
        self.restart_unresponsive_btn.clicked.connect(self.restart_unresponsive_emulators)
        control_layout.addWidget(self.restart_unresponsive_btn)

        emulators_layout.addLayout(control_layout)

        # Добавляем таблицу со статусом эмуляторов
        self.emulators_status_table = QTableWidget(0, 5)
        self.emulators_status_table.setHorizontalHeaderLabels(
            ["Индекс", "Имя", "Статус", "Сервер", "Прогресс"])
        self.emulators_status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        emulators_layout.addWidget(self.emulators_status_table)

        self.emulators_tab.setLayout(emulators_layout)

        # Добавляем вкладку в основной виджет вкладок
        self.tabs.addTab(self.emulators_tab, "Эмуляторы")

    def update_emulator_progress(self, emulator_index, step_id, success):
        """
        Обновить индикатор прогресса для конкретного эмулятора.

        Args:
            emulator_index: Индекс эмулятора
            step_id: ID текущего шага
            success: Флаг успешного выполнения
        """
        # Если для этого эмулятора еще нет индикатора, создаем его
        if emulator_index not in self.emulator_progress_bars:
            # Создаем контейнер для этого эмулятора
            emulator_container = QWidget()
            emulator_layout = QVBoxLayout(emulator_container)

            # Добавляем метку с информацией об эмуляторе
            emulator_label = QLabel(f"Эмулятор {emulator_index}")
            emulator_label.setStyleSheet("font-weight: bold;")
            emulator_layout.addWidget(emulator_label)

            # Добавляем метку с текущим шагом
            step_label = QLabel("Текущий шаг: -")
            emulator_layout.addWidget(step_label)

            # Добавляем индикатор прогресса
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 126)  # 126 шагов в туториале
            progress_bar.setValue(0)
            emulator_layout.addWidget(progress_bar)

            # Сохраняем ссылки на виджеты
            self.emulator_progress_bars[emulator_index] = {
                "container": emulator_container,
                "step_label": step_label,
                "progress_bar": progress_bar
            }

            # Добавляем контейнер в основной контейнер
            self.emulators_progress_container.addWidget(emulator_container)

        # Получаем виджеты для этого эмулятора
        widgets = self.emulator_progress_bars[emulator_index]

        # Обновляем метку с текущим шагом
        widgets["step_label"].setText(f"Текущий шаг: {step_id}")

        # Обновляем индикатор прогресса
        if step_id.startswith("step"):
            try:
                step_num = int(step_id[4:])
                widgets["progress_bar"].setValue(step_num)

                # Устанавливаем цвет в зависимости от успешности выполнения
                if success:
                    widgets["progress_bar"].setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
                else:
                    widgets["progress_bar"].setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
            except ValueError:
                pass

        # Обновляем таблицу статуса эмуляторов
        self.update_emulators_status_table()

    def refresh_emulators_status(self):
        """
        Обновить статус всех эмуляторов.
        """
        # Обновляем список эмуляторов
        self.refresh_emulators()

        # Обновляем таблицу статуса
        self.update_emulators_status_table()

    def update_emulators_status_table(self):
        """
        Обновить таблицу статуса эмуляторов.
        """
        # Получаем информацию о всех эмуляторах
        emulators = self.emulator_manager.list_emulators()

        # Очищаем таблицу
        self.emulators_status_table.setRowCount(0)

        # Добавляем строки для каждого эмулятора
        for i, emu in enumerate(emulators):
            self.emulators_status_table.insertRow(i)

            # Индекс
            index_item = QTableWidgetItem(emu["index"])
            self.emulators_status_table.setItem(i, 0, index_item)

            # Имя
            name_item = QTableWidgetItem(emu["name"])
            self.emulators_status_table.setItem(i, 1, name_item)

            # Статус
            status_item = QTableWidgetItem(emu["status"])
            if emu["status"] == "running":
                status_item.setForeground(QColor(Qt.GlobalColor.green))
            else:
                status_item.setForeground(QColor(Qt.GlobalColor.gray))
            self.emulators_status_table.setItem(i, 2, status_item)

            # Сервер (если есть активная задача)
            server_item = QTableWidgetItem("-")
            if hasattr(self, 'bot_workers') and isinstance(self.bot_workers, dict) and emu["index"] in self.bot_workers:
                server_range = self.bot_workers[emu["index"]].server_range
                server_item.setText(f"{server_range[0]}-{server_range[1]}")
            self.emulators_status_table.setItem(i, 3, server_item)

            # Прогресс (если есть)
            progress_item = QTableWidgetItem("-")
            if emu["index"] in self.emulator_progress_bars:
                progress_bar_data = self.emulator_progress_bars[emu["index"]]
                if isinstance(progress_bar_data, dict) and "progress_bar" in progress_bar_data:
                    progress = progress_bar_data["progress_bar"].value()
                elif isinstance(progress_bar_data, QProgressBar):
                    progress = progress_bar_data.value()
                else:
                    progress = 0
                progress_item.setText(f"{progress}/126 ({int(progress / 1.26)}%)")
            self.emulators_status_table.setItem(i, 4, progress_item)

    def restart_unresponsive_emulators(self):
        """
        Перезапустить зависшие эмуляторы.
        """
        # Получаем список всех эмуляторов
        emulators = self.emulator_manager.list_emulators()

        restarted = 0
        for emu in emulators:
            if emu["status"] == "running":
                # Проверяем, отвечает ли эмулятор
                if not self.emulator_manager.is_emulator_responsive(int(emu["index"])):
                    # Перезапускаем эмулятор
                    success = self.emulator_manager.restart_if_unresponsive(int(emu["index"]))
                    if success:
                        restarted += 1

        # Сообщаем о результате
        if restarted > 0:
            QMessageBox.information(self, "Перезапуск эмуляторов",
                                    f"Успешно перезапущено {restarted} эмуляторов")
        else:
            QMessageBox.information(self, "Перезапуск эмуляторов",
                                    "Все эмуляторы отвечают, перезапуск не требуется")

        # Обновляем статус
        self.refresh_emulators_status()

    def save_settings_to_file(self):
        """
        Сохранить настройки в файл.
        """
        # Создаем словарь с настройками
        settings = {
            "ldplayer_path": self.ldplayer_path_combo.currentText(),
            "start_server": self.start_server_spin.value(),
            "end_server": self.end_server_spin.value(),
            "selected_season": self.season_combo.currentText()
        }

        # Сохраняем выбранные эмуляторы
        selected_emulators = []
        for item in self.emulators_list.selectedItems():
            selected_emulators.append(item.data(Qt.ItemDataRole.UserRole))
        settings["selected_emulators"] = selected_emulators

        # Сохраняем настройки в файл
        try:
            import json
            from pathlib import Path

            # Создаем директорию config, если она не существует
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)

            # Сохраняем настройки в файл
            with open(config_dir / "ui_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)

            QMessageBox.information(self, "Сохранение настроек", "Настройки успешно сохранены")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {e}")

    def load_settings_from_file(self):
        """
        Загрузить настройки из файла.
        """
        try:
            import json
            from pathlib import Path

            # Путь к файлу настроек
            settings_file = Path("config/ui_settings.json")

            # Проверяем, существует ли файл
            if not settings_file.exists():
                QMessageBox.information(self, "Загрузка настроек",
                                        "Файл настроек не найден. Будут использованы настройки по умолчанию.")
                return

            # Загружаем настройки из файла
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)

            # Применяем настройки
            if "ldplayer_path" in settings:
                index = self.ldplayer_path_combo.findText(settings["ldplayer_path"])
                if index >= 0:
                    self.ldplayer_path_combo.setCurrentIndex(index)
                else:
                    self.ldplayer_path_combo.setCurrentText(settings["ldplayer_path"])

            if "start_server" in settings:
                self.start_server_spin.setValue(settings["start_server"])

            if "end_server" in settings:
                self.end_server_spin.setValue(settings["end_server"])

            if "selected_season" in settings:
                index = self.season_combo.findText(settings["selected_season"])
                if index >= 0:
                    self.season_combo.setCurrentIndex(index)

            # Загружаем список эмуляторов
            self.refresh_emulators()

            # Выбираем сохраненные эмуляторы
            if "selected_emulators" in settings:
                for i in range(self.emulators_list.count()):
                    item = self.emulators_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) in settings["selected_emulators"]:
                        item.setSelected(True)

            QMessageBox.information(self, "Загрузка настроек", "Настройки успешно загружены")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить настройки: {e}")

    def initialize_emulator_ui_elements(self):
        """
        Инициализация UI элементов для отслеживания каждого эмулятора.
        """
        # Создаем словари для хранения элементов UI
        self.emulator_progress_bars = {}
        self.emulator_status_labels = {}

        # Создаем контейнер для элементов, если его еще нет
        if not hasattr(self, 'emulators_container'):
            self.emulators_container = QWidget()
            emulators_layout = QVBoxLayout(self.emulators_container)

            # Добавляем заголовок
            title_label = QLabel("Статус эмуляторов")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            emulators_layout.addWidget(title_label)

            # Создаем прокручиваемую область
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_content = QWidget()
            self.emulators_layout = QVBoxLayout(scroll_content)
            scroll_content.setLayout(self.emulators_layout)
            scroll_area.setWidget(scroll_content)
            emulators_layout.addWidget(scroll_area)

            # Добавляем на вкладку настроек или создаем отдельную вкладку
            if hasattr(self, 'settings_tab'):
                self.settings_tab.layout().addWidget(self.emulators_container)
            else:
                emulators_tab = QWidget()
                emulators_tab.setLayout(emulators_layout)
                self.tabs.addTab(emulators_tab, "Эмуляторы")

        # Очищаем существующие элементы
        if hasattr(self, 'emulators_layout'):
            # Удаляем все виджеты из layout
            while self.emulators_layout.count():
                item = self.emulators_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Получаем список эмуляторов
        emulators = self.emulator_manager.list_emulators()

        # Создаем элементы UI для каждого эмулятора
        for emu in emulators:
            emulator_index = int(emu["index"])

            # Создаем группу для эмулятора
            group_box = QGroupBox(f"Эмулятор {emu['name']} (Индекс: {emulator_index})")
            group_layout = QVBoxLayout()

            # Создаем метку статуса
            status_label = QLabel("Статус: не запущен")
            group_layout.addWidget(status_label)

            # Создаем индикатор прогресса
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 126)  # 126 шагов всего
            progress_bar.setValue(0)
            progress_bar.setFormat("%v/%m (%p%)")
            group_layout.addWidget(progress_bar)

            # Сохраняем ссылки на элементы
            self.emulator_status_labels[emulator_index] = status_label
            self.emulator_progress_bars[emulator_index] = progress_bar

            # Завершаем настройку группы
            group_box.setLayout(group_layout)
            self.emulators_layout.addWidget(group_box)

        # Добавляем растягивающийся элемент в конец
        self.emulators_layout.addStretch(1)

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
        try:
            selected_items = self.emulators_list.selectedItems()

            if not selected_items:
                QMessageBox.warning(self, "Предупреждение", "Не выбрано ни одного эмулятора.")
                return

            start_server = self.start_server_spin.value()
            end_server = self.end_server_spin.value()

            if start_server > end_server:
                QMessageBox.warning(self, "Предупреждение", "Начальный сервер должен быть меньше или равен конечному.")
                return

            # Получаем индексы выбранных эмуляторов
            emulator_indices = []
            for item in selected_items:
                emulator_indices.append(int(item.data(Qt.ItemDataRole.UserRole)))

            # Подготавливаем диапазоны серверов для каждого эмулятора
            server_ranges = {}
            for idx in emulator_indices:
                server_ranges[idx] = (start_server, end_server)

            # Запускаем параллельное выполнение
            self.parallel_executor.start()

            task_ids = self.parallel_executor.process_multiple_emulators(
                emulator_indices=emulator_indices,
                server_ranges=server_ranges,
                on_step_complete=self.handle_step_completed,
                on_tutorial_complete=self.handle_tutorial_completed
            )

            if task_ids:
                # Обновляем UI
                self.start_bot_btn.setEnabled(False)
                self.stop_bot_btn.setEnabled(True)
                self.status_label.setText(f"Бот запущен на {len(task_ids)} эмуляторах")
                self.update_statistics()
            else:
                QMessageBox.warning(self, "Предупреждение", "Не удалось запустить бота ни на одном эмуляторе.")
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при запуске бота: {str(e)}")

    def stop_bot(self):
        """
        Остановка бота на всех эмуляторах.
        """
        if not self.parallel_executor:
            logger.warning("Параллельный выполнитель не инициализирован")
            return

        # Останавливаем выполнение
        self.parallel_executor.stop()

        # Обновляем UI
        self.start_bot_btn.setEnabled(True)
        self.stop_bot_btn.setEnabled(False)
        self.status_label.setText("Бот остановлен")

    def handle_step_completed(self, emulator_id, step_id, success):
        """
        Обработка завершения шага туториала.

        Args:
            emulator_id: Идентификатор эмулятора (ADB ID)
            step_id: ID шага
            success: Флаг успешного выполнения
        """
        # Получаем индекс эмулятора по его ADB ID
        emulator_index = None
        for idx, adb_id in self.parallel_executor.emulator_ids.items() if hasattr(self.parallel_executor,
                                                                                  'emulator_ids') else {}:
            if adb_id == emulator_id:
                emulator_index = idx
                break

        if emulator_index is None:
            logger.warning(f"Не удалось определить индекс эмулятора для ADB ID: {emulator_id}")
            return

        logger.info(f"Эмулятор {emulator_index} (ADB ID: {emulator_id}): "
                    f"Шаг {step_id} {'выполнен успешно' if success else 'не выполнен'}")

        # Обновляем главный прогресс бар (для общего прогресса)
        if step_id.startswith("step"):
            try:
                step_num = int(step_id[4:])
                # В ТЗ указано 125 шагов
                progress = min(100, int((step_num / 126) * 100))
                self.progress_bar.setValue(progress)
            except ValueError:
                pass

        # Обновляем индивидуальный прогресс для конкретного эмулятора
        self.update_emulator_progress(emulator_index, step_id, success)

    def handle_tutorial_completed(self, emulator_id, success):
        """
        Обработка завершения туториала.

        Args:
            emulator_id: Идентификатор эмулятора (ADB ID)
            success: Флаг успешного выполнения
        """
        # Получаем индекс эмулятора по его ADB ID
        emulator_index = None
        for idx, adb_id in self.parallel_executor.emulator_ids.items() if hasattr(self.parallel_executor,
                                                                                  'emulator_ids') else {}:
            if adb_id == emulator_id:
                emulator_index = idx
                break

        if emulator_index is None:
            logger.warning(f"Не удалось определить индекс эмулятора для ADB ID: {emulator_id}")

        logger.info(f"Эмулятор {emulator_index if emulator_index else 'неизвестный'} (ADB ID: {emulator_id}): "
                    f"Туториал {'успешно завершен' if success else 'не завершен'}")

        # Обновляем статистику
        start_server = self.start_server_spin.value()
        self.stats.end_run(start_server, success)
        self.update_statistics()

        # Обновляем UI для конкретного эмулятора
        if emulator_index is not None:
            # Обновляем индикатор прогресса
            if hasattr(self, 'emulator_progress_bars') and emulator_index in self.emulator_progress_bars:
                progress_bar_data = self.emulator_progress_bars[emulator_index]

                # Проверяем тип progress_bar_data
                if isinstance(progress_bar_data, dict) and "progress_bar" in progress_bar_data:
                    progress_bar = progress_bar_data["progress_bar"]
                elif isinstance(progress_bar_data, QProgressBar):
                    progress_bar = progress_bar_data
                else:
                    logger.warning(f"Неизвестный тип данных для progress_bar_data: {type(progress_bar_data)}")
                    progress_bar = None

                if progress_bar:
                    if success:
                        progress_bar.setValue(126)  # Максимальное значение
                        progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
                    else:
                        progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")

            # Обновляем статус
            if hasattr(self, 'emulator_status_labels') and emulator_index in self.emulator_status_labels:
                status_label = self.emulator_status_labels[emulator_index]
                if success:
                    status_label.setText("Туториал успешно завершен")
                    status_label.setStyleSheet("color: green; font-weight: bold;")
                else:
                    status_label.setText("Туториал не завершен")
                    status_label.setStyleSheet("color: red; font-weight: bold;")

        # Проверяем, все ли активные задачи завершены
        active_tasks = self.parallel_executor.get_active_tasks()
        all_completed = len(active_tasks) == 0 or all(task.get('status') != 'running' for task in active_tasks.values())

        if all_completed:
            # Если все задачи завершены, обновляем общий UI
            self.start_bot_btn.setEnabled(True)
            self.stop_bot_btn.setEnabled(False)
            self.status_label.setText("Бот не запущен")
            self.progress_bar.setValue(0)

            # Показываем итоговую статистику
            completed_count = sum(1 for task in active_tasks.values() if task.get('status') == 'completed')
            failed_count = sum(1 for task in active_tasks.values() if task.get('status') == 'failed')

            QMessageBox.information(
                self,
                "Выполнение завершено",
                f"Все задачи завершены.\n"
                f"Успешно: {completed_count}\n"
                f"С ошибками: {failed_count}"
            )

    def handle_error(self, emulator_id, error_message):
        """
        Обработка ошибки в работе бота.

        Args:
            emulator_id: Идентификатор эмулятора (ADB ID)
            error_message: Сообщение об ошибке
        """
        # Получаем индекс эмулятора по его ADB ID
        emulator_index = None
        for idx, adb_id in self.parallel_executor.emulator_ids.items() if hasattr(self.parallel_executor,
                                                                                  'emulator_ids') else {}:
            if adb_id == emulator_id:
                emulator_index = idx
                break

        logger.error(f"Эмулятор {emulator_index if emulator_index else 'неизвестный'} (ADB ID: {emulator_id}): "
                     f"Ошибка: {error_message}")

        # Обновляем UI для конкретного эмулятора, если возможно
        if emulator_index is not None and hasattr(self,
                                                  'emulator_status_labels') and emulator_index in self.emulator_status_labels:
            status_label = self.emulator_status_labels[emulator_index]
            status_label.setText(f"Ошибка: {error_message[:50]}...")
            status_label.setStyleSheet("color: red;")

        # Добавляем ошибку в лог ошибок (если есть)
        if hasattr(self, 'error_log'):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.error_log.append(f"[{timestamp}] Эмулятор {emulator_id}: {error_message}")

        # Показываем уведомление об ошибке
        QMessageBox.warning(
            self,
            "Ошибка выполнения",
            f"Эмулятор {emulator_index if emulator_index else emulator_id}: {error_message}"
        )

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
        if hasattr(self, 'bot_workers') and isinstance(self.bot_workers, dict):
            for worker in self.bot_workers.values():
                worker.stop()

        # Останавливаем параллельный исполнитель
        if hasattr(self, 'parallel_executor'):
            self.parallel_executor.stop()

        # Удаляем обработчик логов
        if hasattr(self, 'ui_logger_handler') and self.ui_logger_handler:
            remove_ui_logger(self.ui_logger_handler)

        event.accept()