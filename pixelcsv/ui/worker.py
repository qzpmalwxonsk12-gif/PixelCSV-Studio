"""Background worker that runs the conversion off the UI thread.

Processing and writing a large image can take seconds, so it runs in a
:class:`QThread`.  The worker emits Qt signals for progress, success and
failure; the main window simply connects to them.  All exceptions are caught
and reported through the ``failed`` signal so the application never crashes.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..core.exceptions import PixelCsvError
from ..core.exporters.base import Exporter
from ..core.image_processor import ImageProcessor
from ..core.models import ExportResult, LoadedImage, ProcessingOptions


class ConversionWorker(QThread):
    """Runs process -> extract -> export and reports the outcome.

    Signals
    -------
    progress(int):
        Overall completion as a percentage (0-100).
    succeeded(object):
        Emitted with an :class:`ExportResult` when everything finishes.
    failed(str):
        Emitted with a user-facing message if anything goes wrong.
    """

    progress = Signal(int)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        loaded_image: LoadedImage,
        options: ProcessingOptions,
        exporter: Exporter,
        output_path: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._loaded = loaded_image
        self._options = options
        self._exporter = exporter
        self._output_path = Path(output_path)
        self._processor = ImageProcessor()

    def run(self) -> None:  # noqa: D401 - Qt entry point
        """Execute the pipeline on the worker thread."""
        started = time.perf_counter()
        try:
            # 1) Resize / convert to RGB (fast).
            processed = self._processor.process(self._loaded, self._options)
            self.progress.emit(5)

            # 2) Extract pixels (10% -> 40% of the bar).
            matrix = self._processor.extract_matrix(
                processed,
                progress_cb=lambda frac: self.progress.emit(5 + int(frac * 35)),
            )

            # 3) Export (40% -> 100% of the bar).
            self._exporter.export(
                matrix,
                self._output_path,
                progress_cb=lambda frac: self.progress.emit(40 + int(frac * 60)),
            )
            self.progress.emit(100)

            size = self._output_path.stat().st_size if self._output_path.exists() else 0
            result = ExportResult(
                output_path=self._output_path,
                exporter_name=self._exporter.name,
                width=processed.width,
                height=processed.height,
                pixel_count=processed.total_pixels,
                file_size_bytes=size,
                duration_seconds=time.perf_counter() - started,
            )
            self.succeeded.emit(result)
        except PixelCsvError as exc:
            self.failed.emit(str(exc))
        except MemoryError:
            self.failed.emit(
                "Ran out of memory while converting.\n\n"
                "Try resizing the image to a smaller resolution first."
            )
        except Exception as exc:  # pragma: no cover - last-resort safety net
            self.failed.emit(f"Unexpected error during conversion.\n\nDetails: {exc}")
