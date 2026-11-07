"""Thin, typed wrapper around :class:`QSettings`.

Centralising persistence here means the UI never sprinkles raw ``QSettings``
keys around, and the set of remembered preferences is documented in one place:

* last used output directory
* recently opened files
* dark-mode preference
* last selected resize algorithm and export format
* main-window geometry
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QSettings

from .. import APP_NAME, ORG_NAME

_MAX_RECENT_FILES = 8


class AppSettings:
    """Typed accessors over a single :class:`QSettings` store."""

    def __init__(self) -> None:
        self._settings = QSettings(ORG_NAME, APP_NAME)

    # ------------------------------------------------------------------ #
    # Output directory
    # ------------------------------------------------------------------ #
    @property
    def output_dir(self) -> Optional[str]:
        """The last directory the user exported to, if any still exists."""
        value = self._settings.value("output/dir", "", type=str)
        if value and Path(value).is_dir():
            return value
        return None

    @output_dir.setter
    def output_dir(self, value: str) -> None:
        self._settings.setValue("output/dir", str(value))

    # ------------------------------------------------------------------ #
    # Recent files
    # ------------------------------------------------------------------ #
    @property
    def recent_files(self) -> List[str]:
        """List of recently opened files, most recent first (existing only)."""
        raw = self._settings.value("files/recent", [])
        if raw is None:
            items: List[str] = []
        elif isinstance(raw, str):
            items = [raw]
        else:
            items = [str(item) for item in raw]
        return [item for item in items if Path(item).is_file()]

    def add_recent_file(self, path: str) -> None:
        """Record *path* as the most recently opened file."""
        path = str(path)
        items = [p for p in self.recent_files if p != path]
        items.insert(0, path)
        del items[_MAX_RECENT_FILES:]
        self._settings.setValue("files/recent", items)

    def clear_recent_files(self) -> None:
        """Forget all recently opened files."""
        self._settings.setValue("files/recent", [])

    # ------------------------------------------------------------------ #
    # Appearance
    # ------------------------------------------------------------------ #
    @property
    def dark_mode(self) -> bool:
        """Whether dark mode is enabled (defaults to ``True``)."""
        return self._settings.value("ui/dark_mode", True, type=bool)

    @dark_mode.setter
    def dark_mode(self, value: bool) -> None:
        self._settings.setValue("ui/dark_mode", bool(value))

    # ------------------------------------------------------------------ #
    # Last-used pipeline choices
    # ------------------------------------------------------------------ #
    @property
    def last_algorithm(self) -> str:
        """Label of the last selected resize algorithm (defaults to Lanczos)."""
        return self._settings.value("pipeline/algorithm", "Lanczos", type=str)

    @last_algorithm.setter
    def last_algorithm(self, value: str) -> None:
        self._settings.setValue("pipeline/algorithm", str(value))

    @property
    def last_format(self) -> str:
        """Key of the last selected export format (defaults to CSV)."""
        return self._settings.value("pipeline/format", "csv", type=str)

    @last_format.setter
    def last_format(self, value: str) -> None:
        self._settings.setValue("pipeline/format", str(value))

    # ------------------------------------------------------------------ #
    # Window geometry
    # ------------------------------------------------------------------ #
    @property
    def window_geometry(self):
        """Saved main-window geometry blob, or ``None``."""
        return self._settings.value("ui/geometry")

    @window_geometry.setter
    def window_geometry(self, value) -> None:
        self._settings.setValue("ui/geometry", value)
