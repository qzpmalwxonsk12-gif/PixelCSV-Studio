"""JSON exporter — demonstrates how trivially a new format slots in.

Produces a structured document::

    {
      "width": 2,
      "height": 2,
      "pixels": [
        [[255,0,0],[0,255,0]],
        [[0,0,255],[255,255,255]]
      ]
    }

The file is streamed row by row rather than built in memory, so it scales to
large images.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..exceptions import ExportError
from ..models import PixelMatrix
from .base import Exporter, PathLike, ProgressCallback

_PROGRESS_STEPS = 100


class JsonExporter(Exporter):
    """Writes a pixel matrix as nested JSON arrays."""

    key = "json"
    name = "JSON (nested arrays)"
    extension = ".json"
    description = "A width/height header plus a 2-D array of [r, g, b] pixels."

    def export(
        self,
        matrix: PixelMatrix,
        path: PathLike,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        """Stream *matrix* to *path* as JSON."""
        out_path = Path(path)
        height = matrix.height
        report_every = max(1, height // _PROGRESS_STEPS)

        try:
            with out_path.open("w", encoding="utf-8") as handle:
                handle.write("{\n")
                handle.write(f'  "width": {matrix.width},\n')
                handle.write(f'  "height": {matrix.height},\n')
                handle.write('  "pixels": [\n')

                for y, row in enumerate(matrix.rows()):
                    cells = ",".join(f"[{r},{g},{b}]" for r, g, b in row)
                    trailing = "," if y < height - 1 else ""
                    handle.write(f"    [{cells}]{trailing}\n")

                    if progress_cb is not None and y % report_every == 0:
                        progress_cb((y + 1) / height if height else 1.0)

                handle.write("  ]\n}\n")

            if progress_cb is not None:
                progress_cb(1.0)
        except OSError as exc:
            raise ExportError(
                f"Could not write the JSON file.\n\nDetails: {exc}"
            ) from exc
