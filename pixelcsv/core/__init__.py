"""Core (UI-independent) logic for PixelCSV.

Everything in this sub-package can run head-less, without Qt.  This is what
keeps the image pipeline testable and reusable.
"""

from __future__ import annotations

__all__ = [
    "exceptions",
    "models",
    "image_loader",
    "image_processor",
    "exporters",
]
