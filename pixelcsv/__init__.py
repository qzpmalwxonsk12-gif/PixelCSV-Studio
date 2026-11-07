"""PixelCSV — accurately convert images into RGB data files.

This package is split into clearly separated layers so it stays easy to read,
test and extend:

* :mod:`pixelcsv.core`   — image loading, processing and the pluggable exporters
* :mod:`pixelcsv.config` — persistent user settings (remembered folders, theme…)
* :mod:`pixelcsv.ui`     — the PySide6 desktop interface

The UI never touches the image-processing code directly; it always goes through
the :mod:`pixelcsv.core` objects.  That separation is what makes new export
formats (Excel, JSON, binary, …) or new input types (OBJ, video, …) easy to add
without rewriting the application.
"""

from __future__ import annotations

__all__ = ["__version__", "APP_NAME", "ORG_NAME"]

__version__ = "1.0.0"
APP_NAME = "PixelCSV"
ORG_NAME = "PixelCSV"
