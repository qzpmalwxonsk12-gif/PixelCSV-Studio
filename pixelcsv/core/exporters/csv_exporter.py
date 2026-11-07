"""CSV exporter — the primary output format.

Layout (one pixel per spreadsheet cell):

* one CSV row per image row
* one cell per pixel
* each cell holds the exact ``R, G, B`` values, e.g. ``232, 34, 64``
* because those values contain commas, every cell is wrapped in quotes so the
  comma is the column separator *between* pixels, not *inside* one
* a space follows each component (``R, G, B``) so spreadsheets keep the cell as
  text instead of parsing it as one giant number (which showed up as ``#####``)

Example for a 2x2 image::

    "255, 0, 0","0, 255, 0"
    "0, 0, 255","255, 255, 255"

Opened in Excel / Sheets this puts each pixel in its own cell (``A1`` shows
``255, 0, 0``).  No hex, no compression, no approximation — the values written
are exactly the RGB values of the processed image.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from ..exceptions import ExportError
from ..models import PixelMatrix
from .base import Exporter, PathLike, ProgressCallback

# Emit progress at most this many times to avoid flooding the UI with signals.
_PROGRESS_STEPS = 100


class CsvExporter(Exporter):
    """Writes a pixel matrix as a quoted ``R,G,B``-per-cell spreadsheet."""

    key = "csv"
    name = "CSV (R, G, B per cell)"
    extension = ".csv"
    description = 'Each cell is a quoted "R, G, B" pixel; opens cleanly in Excel.'

    def __init__(self, component_delimiter: str = ", ") -> None:
        """Create a CSV exporter.

        Parameters
        ----------
        component_delimiter:
            Text separating the R, G and B components *inside* a cell (default
            ``", "`` — a comma followed by a space).  The trailing space keeps
            spreadsheets from interpreting the cell as a number.  Cells are
            always quoted and separated by commas so each pixel lands in its
            own spreadsheet column.
        """
        self.component_delimiter = component_delimiter

    def export(
        self,
        matrix: PixelMatrix,
        path: PathLike,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        """Stream *matrix* to *path* as quoted RGB CSV text."""
        out_path = Path(path)
        height = matrix.height
        comp = self.component_delimiter
        report_every = max(1, height // _PROGRESS_STEPS)

        try:
            # newline="" is required so the csv module controls line endings.
            with out_path.open("w", encoding="utf-8", newline="") as handle:
                # QUOTE_ALL wraps every cell in quotes, so the commas inside a
                # pixel never get mistaken for column separators.
                writer = csv.writer(handle, quoting=csv.QUOTE_ALL, lineterminator="\n")
                for y, row in enumerate(matrix.rows()):
                    writer.writerow(
                        [f"{r}{comp}{g}{comp}{b}" for r, g, b in row]
                    )

                    if progress_cb is not None and y % report_every == 0:
                        progress_cb((y + 1) / height if height else 1.0)

            if progress_cb is not None:
                progress_cb(1.0)
        except OSError as exc:
            raise ExportError(
                f"Could not write the CSV file.\n\nDetails: {exc}"
            ) from exc
