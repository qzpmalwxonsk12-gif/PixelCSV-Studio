"""Application bootstrap.

Creates the :class:`QApplication`, wires up persistent settings and the theme,
shows the main window and runs the Qt event loop.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import APP_NAME, ORG_NAME
from .config.settings import AppSettings
from .ui.main_window import MainWindow
from .ui.theme import apply_theme


def run() -> int:
    """Launch the PixelCSV GUI and return the process exit code."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORG_NAME)

    settings = AppSettings()
    apply_theme(app, settings.dark_mode)

    window = MainWindow(settings)
    window.show()

    return app.exec()
