"""Exception hierarchy used across the core layer.

Having dedicated exception types lets the UI present meaningful, user-friendly
error messages while still catching everything under a single base class so the
application *never crashes* on bad input.
"""

from __future__ import annotations


class PixelCsvError(Exception):
    """Base class for every error raised by the PixelCSV core."""


class ImageLoadError(PixelCsvError):
    """Raised when an image cannot be opened or decoded."""


class UnsupportedFormatError(ImageLoadError):
    """Raised when the file extension/type is not a supported image format."""


class ImageTooLargeError(ImageLoadError):
    """Raised when an image exceeds the safe decoding limit (bomb protection)."""


class ProcessingError(PixelCsvError):
    """Raised when resizing or pixel extraction fails."""


class ExportError(PixelCsvError):
    """Raised when an exporter fails to write its output file."""
