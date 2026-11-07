"""Image preview widgets, including the drag-and-drop surface.

* :class:`ImagePreview` shows a pixmap scaled to fit, with a placeholder when
  empty, and rescales smoothly on resize.
* :class:`ImageDropArea` extends it to accept dropped image files and emits a
  signal with the dropped path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

from ...core.image_loader import ImageLoader


class ImagePreview(QLabel):
    """A label that displays an image scaled to fit while keeping aspect ratio."""

    def __init__(self, placeholder: str = "No image", parent=None) -> None:
        super().__init__(parent)
        self._source: Optional[QPixmap] = None
        self._placeholder = placeholder
        self.setObjectName("PreviewSurface")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(280, 280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setWordWrap(True)
        self.setText(placeholder)

    def set_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        """Set (or clear, with ``None``) the displayed image."""
        self._source = pixmap
        self._render()

    def clear_image(self) -> None:
        """Remove the current image and show the placeholder again."""
        self.set_pixmap(None)

    def set_placeholder(self, text: str) -> None:
        """Change the placeholder text shown when there is no image."""
        self._placeholder = text
        if self._source is None:
            self.setText(text)

    def _render(self) -> None:
        """Scale the source pixmap to the current widget size."""
        if self._source is None or self._source.isNull():
            self.setText(self._placeholder)
            return
        scaled = self._source.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._render()


class ImageDropArea(ImagePreview):
    """An :class:`ImagePreview` that also accepts dropped image files."""

    #: Emitted with the local filesystem path of a dropped, supported image.
    imageDropped = Signal(str)

    def __init__(self, placeholder: str = "Drag & drop an image here", parent=None) -> None:
        super().__init__(placeholder, parent)
        self.setAcceptDrops(True)

    def _set_drag_active(self, active: bool) -> None:
        """Toggle the styled drag-highlight state."""
        self.setProperty("dragActive", active)
        # Force the stylesheet to re-evaluate the dynamic property.
        self.style().unpolish(self)
        self.style().polish(self)

    @staticmethod
    def _first_supported_url(event) -> Optional[str]:
        """Return the first dropped local path with a supported extension."""
        if not event.mimeData().hasUrls():
            return None
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            local = url.toLocalFile()
            if ImageLoader.is_supported(Path(local)):
                return local
        return None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._first_supported_url(event) is not None:
            self._set_drag_active(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._set_drag_active(False)
        path = self._first_supported_url(event)
        if path is not None:
            event.acceptProposedAction()
            self.imageDropped.emit(path)
        else:
            event.ignore()
