"""
Фабрика для создания стандартизированных UI элементов.
Обеспечивает консистентность стиля в приложении.
"""

from PyQt6.QtWidgets import (
    QPushButton, QLabel, QSpinBox, QComboBox, QCheckBox,
    QLineEdit, QTextEdit, QGroupBox, QProgressBar, QTableWidget,
    QListWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon


class UIFactory:
    """
    Фабрика для создания UI элементов в едином стиле.
    """

    @staticmethod
    def create_button(text, icon=None, tooltip=None, enabled=True, checkable=False):
        """
        Создание кнопки.

        Args:
            text: Текст кнопки
            icon: Путь к иконке (если есть)
            tooltip: Всплывающая подсказка
            enabled: Флаг активности кнопки
            checkable: Флаг возможности нажатия/отжатия

        Returns:
            Стилизованная кнопка
        """
        button = QPushButton(text)

        if icon:
            button.setIcon(QIcon(icon))
            button.setIconSize(QSize(16, 16))

        if tooltip:
            button.setToolTip(tooltip)

        button.setEnabled(enabled)
        button.setCheckable(checkable)

        return button

    @staticmethod
    def create_primary_button(text, icon=None, tooltip=None, enabled=True):
        """
        Создание главной кнопки (акцентной).

        Args:
            text: Текст кнопки
            icon: Путь к иконке (если есть)
            tooltip: Всплывающая подсказка
            enabled: Флаг активности кнопки

        Returns:
            Стилизованная главная кнопка
        """
        button = UIFactory.create_button(text, icon, tooltip, enabled)
        button.setProperty("primary", True)
        button.setStyleSheet("""
            QPushButton[primary=true] {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
            }
            QPushButton[primary=true]:hover {
                background-color: #1976D2;
            }
            QPushButton[primary=true]:pressed {
                background-color: #0D47A1;
            }
        """)
        return button

    @staticmethod
    def create_danger_button(text, icon=None, tooltip=None, enabled=True):
        """
        Создание кнопки для опасных действий.

        Args:
            text: Текст кнопки
            icon: Путь к иконке (если есть)
            tooltip: Всплывающая подсказка
            enabled: Флаг активности кнопки

        Returns:
            Стилизованная кнопка для опасных действий
        """
        button = UIFactory.create_button(text, icon, tooltip, enabled)
        button.setProperty("danger", True)
        button.setStyleSheet("""
            QPushButton[danger=true] {
                background-color: #F44336;
                color: white;
            }
            QPushButton[danger=true]:hover {
                background-color: #D32F2F;
            }
            QPushButton[danger=true]:pressed {
                background-color: #B71C1C;
            }
        """)
        return button

    @staticmethod
    def create_success_button(text, icon=None, tooltip=None, enabled=True):
        """
        Создание кнопки для успешных действий.

        Args:
            text: Текст кнопки
            icon: Путь к иконке (если есть)
            tooltip: Всплывающая подсказка
            enabled: Флаг активности кнопки

        Returns:
            Стилизованная кнопка для успешных действий
        """
        button = UIFactory.create_button(text, icon, tooltip, enabled)
        button.setProperty("success", True)
        button.setStyleSheet("""
            QPushButton[success=true] {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton[success=true]:hover {
                background-color: #388E3C;
            }
            QPushButton[success=true]:pressed {
                background-color: #1B5E20;
            }
        """)
        return button

    @staticmethod
    def create_label(text, bold=False, font_size=None, tooltip=None, alignment=Qt.AlignmentFlag.AlignLeft):
        """
        Создание метки.

        Args:
            text: Текст метки
            bold: Флаг жирного текста
            font_size: Размер шрифта (если нужен особый)
            tooltip: Всплывающая подсказка
            alignment: Выравнивание текста

        Returns:
            Стилизованная метка
        """
        label = QLabel(text)

        if bold or font_size:
            font = label.font()
            if bold:
                font.setBold(True)
            if font_size:
                font.setPointSize(font_size)
            label.setFont(font)

        if tooltip:
            label.setToolTip(tooltip)

        label.setAlignment(alignment)

        return label

    @staticmethod
    def create_heading(text, level=1, tooltip=None):
        """
        Создание заголовка.

        Args:
            text: Текст заголовка
            level: Уровень заголовка (1-6)
            tooltip: Всплывающая подсказка

        Returns:
            Стилизованный заголовок
        """
        font_size = 18 - (level * 2)  # От 16 до 6 в зависимости от уровня
        font_size = max(font_size, 8)  # Не меньше 8

        return UIFactory.create_label(
            text, bold=True, font_size=font_size,
            tooltip=tooltip, alignment=Qt.AlignmentFlag.AlignLeft
        )

    @staticmethod
    def create_spin_box(min_value=0, max_value=100, value=0, prefix="", suffix="", tooltip=None):
        """
        Создание счетчика.

        Args:
            min_value: Минимальное значение
            max_value: Максимальное значение
            value: Начальное значение
            prefix: Префикс перед значением
            suffix: Суффикс после значения
            tooltip: Всплывающая подсказка

        Returns:
            Стилизованный счетчик
        """
        spin_box = QSpinBox()
        spin_box.setRange(min_value, max_value)
        spin_box.setValue(value)

        if prefix:
            spin_box.setPrefix(prefix)

        if suffix:
            spin_box.setSuffix(suffix)

        if tooltip:
            spin_box.setToolTip(tooltip)

        return spin_box

    @staticmethod
    def create_combo_box(items=None, current_index=0, editable=False, tooltip=None):
        """
        Создание выпадающего списка.

        Args:
            items: Список элементов
            current_index: Индекс выбранного элемента
            editable: Флаг возможности редактирования
            tooltip: Всплывающая подсказка

        Returns:
            Стилизованный выпадающий список
        """
        combo_box = QComboBox()

        if items:
            combo_box.addItems(items)
            combo_box.setCurrentIndex(current_index)

        combo_box.setEditable(editable)

        if tooltip:
            combo_box.setToolTip(tooltip)

        return combo_box

    @staticmethod
    def create_check_box(text, checked=False, tooltip=None):
        """
        Создание флажка.

        Args:
            text: Текст флажка
            checked: Флаг выбора
            tooltip: Всплывающая подсказка

        Returns:
            Стилизованный флажок
        """
        check_box = QCheckBox(text)
        check_box.setChecked(checked)

        if tooltip:
            check_box.setToolTip(tooltip)

        return check_box

    @staticmethod
    def create_line_edit(text="", placeholder="", tooltip=None, read_only=False):
        """
        Создание поля ввода текста.

        Args:
            text: Начальный текст
            placeholder: Текст-подсказка
            tooltip: Всплывающая подсказка
            read_only: Флаг только для чтения

        Returns:
            Стилизованное поле ввода
        """
        line_edit = QLineEdit(text)

        if placeholder:
            line_edit.setPlaceholderText(placeholder)

        if tooltip:
            line_edit.setToolTip(tooltip)

        line_edit.setReadOnly(read_only)

        return line_edit

    @staticmethod
    def create_text_edit(text="", placeholder="", tooltip=None, read_only=False):
        """
        Создание многострочного поля ввода текста.

        Args:
            text: Начальный текст
            placeholder: Текст-подсказка
            tooltip: Всплывающая подсказка
            read_only: Флаг только для чтения

        Returns:
            Стилизованное многострочное поле ввода
        """
        text_edit = QTextEdit()

        if text:
            text_edit.setPlainText(text)

        if placeholder:
            text_edit.setPlaceholderText(placeholder)

        if tooltip:
            text_edit.setToolTip(tooltip)

        text_edit.setReadOnly(read_only)

        return text_edit

    @staticmethod
    def create_group_box(title, layout=None, tooltip=None):
        """
        Создание группы с рамкой.

        Args:
            title: Заголовок группы
            layout: Макет для группы (если есть)
            tooltip: Всплывающая подсказка

        Returns:
            Стилизованная группа
        """
        group_box = QGroupBox(title)

        if layout:
            group_box.setLayout(layout)

        if tooltip:
            group_box.setToolTip(tooltip)

        return group_box

    @staticmethod
    def create_progress_bar(min_value=0, max_value=100, value=0, format="%p%", tooltip=None):
        """
        Создание индикатора прогресса.

        Args:
            min_value: Минимальное значение
            max_value: Максимальное значение
            value: Текущее значение
            format: Формат отображения значения
            tooltip: Всплывающая подсказка

        Returns:
            Стилизованный индикатор прогресса
        """
        progress_bar = QProgressBar()
        progress_bar.setRange(min_value, max_value)
        progress_bar.setValue(value)
        progress_bar.setFormat(format)

        if tooltip:
            progress_bar.setToolTip(tooltip)

        return progress_bar

    @staticmethod
    def create_list_widget(items=None, tooltip=None, selection_mode=None):
        """
        Создание списка элементов.

        Args:
            items: Список элементов
            tooltip: Всплывающая подсказка
            selection_mode: Режим выбора элементов

        Returns:
            Стилизованный список элементов
        """
        list_widget = QListWidget()

        if items:
            list_widget.addItems(items)

        if tooltip:
            list_widget.setToolTip(tooltip)

        if selection_mode is not None:
            list_widget.setSelectionMode(selection_mode)

        return list_widget

    @staticmethod
    def create_table_widget(rows=0, columns=0, headers=None, tooltip=None):
        """
        Создание таблицы.

        Args:
            rows: Количество строк
            columns: Количество столбцов
            headers: Заголовки столбцов
            tooltip: Всплывающая подсказка

        Returns:
            Стилизованная таблица
        """
        table_widget = QTableWidget(rows, columns)

        if headers:
            table_widget.setHorizontalHeaderLabels(headers)

        if tooltip:
            table_widget.setToolTip(tooltip)

        return table_widget