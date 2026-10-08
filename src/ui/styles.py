
# Modern white application theme

MAIN_WINDOW_STYLE = """
QMainWindow {
    background-color: #ffffff;
    color: #1f1f1f;
}
"""

WIDGET_STYLE = """
QWidget {
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    font-size: 12px;
    color: #1f1f1f;
    selection-background-color: #d7e9ff;
    selection-color: #1f1f1f;
}

QLabel {
    color: #3f3f46;
}

QLabel#appTitle {
    font-size: 18px;
    font-weight: 700;
    color: #172033;
}

QLabel#sectionLabel {
    font-size: 14px;
}

QLabel#sectionLabel {
    color: #1f1f1f;
    font-weight: 700;
    padding: 5px 0 2px 0;
}

QLabel#statusReady {
    color: #166534;
    font-weight: 600;
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 6px;
    padding: 4px 8px;
}

QLabel#statusMissing {
    color: #b91c1c;
    font-weight: 600;
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 6px;
    padding: 4px 8px;
}

QTabWidget::pane {
    border: 0;
    border-top: 1px solid #e6e6e6;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: transparent;
    color: #71717a;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 9px;
    margin: 2px 2px 3px 0;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #f3f3f3;
    color: #1f1f1f;
    border-color: #e0e0e0;
}

QTabBar::tab:hover {
    background-color: #f5f5f5;
    color: #1f1f1f;
}

QSplitter::handle {
    background-color: #e6e6e6;
    width: 1px;
}

QGroupBox {
    border: 0;
    border-top: 1px solid #e6e6e6;
    border-radius: 0;
    margin-top: 8px;
    padding: 7px 0 0 0;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 0;
    padding: 0 6px 0 0;
    color: #27272a;
    font-weight: 600;
}

QPushButton {
    background-color: #2f2f33;
    color: #ffffff;
    border: 1px solid #2f2f33;
    border-radius: 6px;
    padding: 5px 10px;
    font-weight: 600;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #1f1f23;
    border-color: #1f1f23;
}

QPushButton:pressed {
    background-color: #111113;
    border-color: #111113;
}

QPushButton:disabled {
    background-color: #e5e7eb;
    border-color: #e5e7eb;
    color: #9ca3af;
}

QPushButton#secondaryButton {
    background-color: #ffffff;
    color: #3f3f46;
    border: 1px solid #d6d6d6;
}

QPushButton#secondaryButton:hover {
    background-color: #f5f5f5;
    border-color: #bdbdbd;
}

QPushButton#stepperButton {
    background-color: #f7f7f7;
    color: #3f3f46;
    border: 1px solid #d6d6d6;
    border-radius: 4px;
    padding: 0;
    font-size: 13px;
    font-weight: 700;
    min-width: 24px;
    max-width: 24px;
    min-height: 22px;
    max-height: 22px;
}

QPushButton#stepperButton:hover {
    background-color: #eeeeee;
    border-color: #bdbdbd;
}

QLineEdit#stepperValue {
    border: 1px solid #d6d6d6;
    border-radius: 4px;
    padding: 2px 4px;
    min-height: 18px;
    max-height: 22px;
    background-color: #ffffff;
}

QLineEdit, QComboBox, QFontComboBox {
    border: 1px solid #d6d6d6;
    border-radius: 6px;
    padding: 3px 22px 3px 7px;
    background-color: #ffffff;
    color: #1f1f1f;
    min-height: 20px;
}

QSpinBox, QDoubleSpinBox {
    border: 1px solid #d6d6d6;
    border-radius: 6px;
    padding: 3px 20px 3px 7px;
    background-color: #ffffff;
    color: #1f1f1f;
    min-height: 20px;
}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 15px;
    border-left: 1px solid #d6d6d6;
    background-color: #fafafa;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    border-top-right-radius: 5px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    border-bottom-right-radius: 5px;
}

QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QFontComboBox:disabled {
    background-color: #f6f6f6;
    color: #a1a1aa;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QFontComboBox:focus {
    border: 1px solid #60a5fa;
    background-color: #ffffff;
}

QCheckBox {
    spacing: 6px;
    color: #3f3f46;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #d6d6d6;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #111827;
    border-color: #111827;
}

QListWidget {
    border: 1px solid #e6e6e6;
    border-radius: 6px;
    background-color: #fafafa;
    padding: 6px;
    outline: none;
}

QListWidget::item {
    background-color: transparent;
    border: 0;
    border-radius: 4px;
    padding: 4px 6px;
    margin-bottom: 1px;
}

QListWidget::item:selected {
    background-color: #e8e8e8;
    color: #1f1f1f;
}

QTextEdit {
    background-color: #ffffff;
    color: #27272a;
    border: 1px solid #e6e6e6;
    border-radius: 6px;
    padding: 7px;
    font-family: 'Consolas', 'D2Coding', monospace;
    font-size: 11px;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #d4d4d8;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
