"""
Модуль содержит стили для оформления пользовательского интерфейса.
"""

# Общие стили для всего приложения
STYLES = """
QMainWindow {
    background-color: #f5f5f5;
}

QTabWidget::pane {
    border: 1px solid #cccccc;
    background-color: white;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #e0e0e0;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid #cccccc;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom-color: white;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #cccccc;
    border-radius: 4px;
    margin-top: 16px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    margin-left: 2px;
    padding: 0 5px;
}

QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #BBDEFB;
    color: #90CAF9;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    padding: 6px;
    border: 1px solid #cccccc;
    border-radius: 4px;
    selection-background-color: #2196F3;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM2MDYwNjAiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0iZmVhdGhlciBmZWF0aGVyLWNoZXZyb24tZG93biI+PHBvbHlsaW5lIHBvaW50cz0iNiA5IDEyIDE1IDE4IDkiPjwvcG9seWxpbmU+PC9zdmc+);
    width: 16px;
    height: 16px;
}

QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 4px;
    text-align: center;
    background-color: #f5f5f5;
}

QProgressBar::chunk {
    background-color: #4CAF50;
    width: 10px;
    margin: 0.5px;
}

QListWidget, QTableWidget, QTextEdit {
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: white;
}

QListWidget::item {
    padding: 5px;
    border-bottom: 1px solid #f0f0f0;
}

QListWidget::item:selected {
    background-color: #BBDEFB;
    color: black;
}

QTableWidget {
    gridline-color: #f0f0f0;
}

QTableWidget QHeaderView::section {
    background-color: #f5f5f5;
    padding: 5px;
    border: 1px solid #cccccc;
    border-left: none;
    border-top: none;
}

QTableWidget::item:selected {
    background-color: #BBDEFB;
    color: black;
}

QLabel {
    color: #333333;
}

QCheckBox {
    spacing: 5px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QCheckBox::indicator:unchecked {
    border: 1px solid #cccccc;
    background-color: white;
}

QCheckBox::indicator:checked {
    border: 1px solid #2196F3;
    background-color: #2196F3;
}

QTextEdit {
    font-family: 'Consolas', 'Courier New', monospace;
    padding: 5px;
}
"""

# Стили для темной темы (можно добавить при необходимости)
DARK_STYLES = """
QMainWindow {
    background-color: #212121;
    color: #f5f5f5;
}

QTabWidget::pane {
    border: 1px solid #424242;
    background-color: #303030;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #424242;
    color: #f5f5f5;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid #424242;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #303030;
    border-bottom-color: #303030;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #424242;
    border-radius: 4px;
    margin-top: 16px;
    padding-top: 16px;
    color: #f5f5f5;
}

QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #424242;
    color: #757575;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    padding: 6px;
    border: 1px solid #424242;
    border-radius: 4px;
    background-color: #424242;
    color: #f5f5f5;
    selection-background-color: #2196F3;
}

QListWidget, QTableWidget, QTextEdit {
    border: 1px solid #424242;
    border-radius: 4px;
    background-color: #303030;
    color: #f5f5f5;
}

QLabel {
    color: #f5f5f5;
}

QProgressBar {
    border: 1px solid #424242;
    border-radius: 4px;
    text-align: center;
    background-color: #303030;
    color: #f5f5f5;
}

QTextEdit {
    font-family: 'Consolas', 'Courier New', monospace;
    padding: 5px;
    background-color: #303030;
    color: #f5f5f5;
}
"""