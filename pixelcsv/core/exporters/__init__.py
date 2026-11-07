"""Pluggable exporters.

An *exporter* turns a :class:`~pixelcsv.core.models.PixelMatrix` into a file on
disk.  Because every exporter consumes the same matrix and implements the same
:class:`~pixelcsv.core.exporters.base.Exporter` interface, new output formats
can be dropped in without changing the image pipeline or the UI:

* register a new subclass in :func:`build_default_registry`
* it instantly appears in the format selector

Bundled formats:

* :class:`CsvExporter`    — ``R,G,B`` per cell (the primary format)
* :class:`JsonExporter`   — nested JSON arrays
* :class:`BinaryExporter` — compact raw-RGB ``.pxrgb`` container
"""

from __future__ import annotations

from .base import Exporter, ProgressCallback
from .binary_exporter import BinaryExporter
from .csv_exporter import CsvExporter
from .json_exporter import JsonExporter
from .registry import ExporterRegistry, build_default_registry

__all__ = [
    "Exporter",
    "ProgressCallback",
    "CsvExporter",
    "JsonExporter",
    "BinaryExporter",
    "ExporterRegistry",
    "build_default_registry",
]
