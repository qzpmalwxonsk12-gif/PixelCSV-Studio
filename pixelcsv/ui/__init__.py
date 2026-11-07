"""PySide6 user-interface layer.

The UI talks to the core exclusively through :mod:`pixelcsv.core` objects and a
background :class:`~pixelcsv.ui.worker.ConversionWorker`, so it never blocks the
event loop and never manipulates image data directly.
"""

from __future__ import annotations

__all__ = ["main_window", "theme", "worker"]
