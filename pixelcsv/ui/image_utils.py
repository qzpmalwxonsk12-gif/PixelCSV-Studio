"""Helpers for bridging Pillow images into Qt for display.

Converting via an in-memory PNG buffer (rather than ``PIL.ImageQt``) keeps this
robust across Qt bindings and Pillow versions, and is plenty fast for preview
thumbnails.
"""

from __future__ import annotations

import io

from PIL import Image
from PySide6.QtGui import QPixmap


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    """Convert a Pillow image into a :class:`QPixmap`."""
    buffer = io.BytesIO()
    image.convert("RGBA").save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap


def make_preview_pixmap(image: Image.Image, max_side: int = 1024) -> QPixmap:
    """Return a down-scaled :class:`QPixmap` suitable for on-screen preview.

    Large images are thumbnailed first so the GUI never has to hand a giant
    pixmap to Qt.  Aspect ratio is preserved.
    """
    preview = image
    if max(image.width, image.height) > max_side:
        preview = image.copy()
        preview.thumbnail((max_side, max_side), Image.Resampling.NEAREST)
    return pil_to_pixmap(preview)
