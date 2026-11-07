"""Light and dark theming for the application.

A single :func:`apply_theme` call swaps the whole look.  We pair the Fusion
style with a hand-tuned stylesheet so the result is consistent across
platforms.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

_DARK_QSS = """
* { font-size: 13px; }

QMainWindow, QDialog, QWidget {
    background-color: #1e1f22;
    color: #e6e6e6;
}
QLabel { color: #e6e6e6; }
QLabel#Heading { font-size: 15px; font-weight: 600; color: #ffffff; }
QLabel#Muted { color: #9aa0a6; }
QLabel#StatLabel { color: #9aa0a6; }
QLabel#StatValue { color: #ffffff; font-weight: 600; }

QGroupBox {
    border: 1px solid #34363b;
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 10px 10px 10px;
    background-color: #26282d;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    color: #c7cad1;
    font-weight: 600;
}

QPushButton {
    background-color: #34363b;
    border: 1px solid #3f424a;
    border-radius: 6px;
    padding: 7px 14px;
    color: #f0f0f0;
}
QPushButton:hover { background-color: #3d4047; }
QPushButton:pressed { background-color: #2c2e33; }
QPushButton:disabled { color: #6b6f76; background-color: #2a2c30; }

QPushButton#Primary {
    background-color: #3b82f6;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 600;
    padding: 10px 16px;
}
QPushButton#Primary:hover { background-color: #4f8ff7; }
QPushButton#Primary:pressed { background-color: #2f6fd6; }
QPushButton#Primary:disabled { background-color: #2f3b52; border-color: #2f3b52; color: #8a93a3; }

QLineEdit, QSpinBox, QComboBox {
    background-color: #1b1c1f;
    border: 1px solid #3f424a;
    border-radius: 6px;
    padding: 6px 8px;
    color: #f0f0f0;
    selection-background-color: #3b82f6;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #3b82f6; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: #1b1c1f;
    border: 1px solid #3f424a;
    selection-background-color: #3b82f6;
    color: #f0f0f0;
}

QRadioButton, QCheckBox { spacing: 8px; color: #e6e6e6; }

QTabWidget::pane { border: 1px solid #34363b; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #26282d;
    color: #b6bac1;
    padding: 7px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #34363b; color: #ffffff; }

QLabel#PreviewSurface {
    background-color: #161719;
    border: 1px dashed #3f424a;
    border-radius: 8px;
    color: #8a8f98;
}
QLabel#PreviewSurface[dragActive="true"] {
    border: 2px dashed #3b82f6;
    background-color: #1d2330;
    color: #cdd6e6;
}

QProgressBar {
    border: 1px solid #3f424a;
    border-radius: 6px;
    background-color: #1b1c1f;
    text-align: center;
    color: #e6e6e6;
}
QProgressBar::chunk { background-color: #3b82f6; border-radius: 5px; }

QStatusBar { background-color: #26282d; color: #c7cad1; }
QMenuBar { background-color: #1e1f22; color: #e6e6e6; }
QMenuBar::item:selected { background: #34363b; }
QMenu { background-color: #26282d; color: #e6e6e6; border: 1px solid #34363b; }
QMenu::item:selected { background-color: #3b82f6; }
QScrollArea { border: none; }
"""

_LIGHT_QSS = """
* { font-size: 13px; }

QLabel#Heading { font-size: 15px; font-weight: 600; }
QLabel#Muted, QLabel#StatLabel { color: #5f6368; }
QLabel#StatValue { font-weight: 600; }

QGroupBox {
    border: 1px solid #d6d8dc;
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px;
    background-color: #fbfbfc;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    font-weight: 600;
    color: #3c4043;
}

QPushButton {
    background-color: #f1f3f4;
    border: 1px solid #d6d8dc;
    border-radius: 6px;
    padding: 7px 14px;
}
QPushButton:hover { background-color: #e8eaed; }
QPushButton:disabled { color: #9aa0a6; }

QPushButton#Primary {
    background-color: #1a73e8;
    border: 1px solid #1a73e8;
    color: #ffffff;
    font-weight: 600;
    padding: 10px 16px;
}
QPushButton#Primary:hover { background-color: #1b66c9; }
QPushButton#Primary:disabled { background-color: #a9c7f5; border-color: #a9c7f5; }

QLineEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #d6d8dc;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: #1a73e8;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #1a73e8; }

QTabWidget::pane { border: 1px solid #d6d8dc; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #f1f3f4;
    padding: 7px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #ffffff; }

QLabel#PreviewSurface {
    background-color: #f4f5f7;
    border: 1px dashed #c4c7cc;
    border-radius: 8px;
    color: #80868b;
}
QLabel#PreviewSurface[dragActive="true"] {
    border: 2px dashed #1a73e8;
    background-color: #e8f0fe;
    color: #1a4fa0;
}

QProgressBar {
    border: 1px solid #d6d8dc;
    border-radius: 6px;
    background-color: #ffffff;
    text-align: center;
}
QProgressBar::chunk { background-color: #1a73e8; border-radius: 5px; }
"""


def apply_theme(app: QApplication, dark: bool) -> None:
    """Apply the light or dark theme to the whole application."""
    app.setStyle("Fusion")
    app.setStyleSheet(_DARK_QSS if dark else _LIGHT_QSS)
