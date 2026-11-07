"""Plain data structures shared across the core layer.

These objects are deliberately free of any Qt or UI dependency so they can be
created, inspected and tested in isolation.  They also decouple the *exporters*
from Pillow: an exporter only ever sees a :class:`PixelMatrix`, never a PIL
image, which is what allows brand-new export formats to be added without
touching the image pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from PIL import Image

RGB = Tuple[int, int, int]


class ResizeAlgorithm(Enum):
    """Supported resampling algorithms, mapped to Pillow filters.

    The value is the human-readable label shown in the UI.
    """

    NEAREST = "Nearest Neighbor"
    BILINEAR = "Bilinear"
    BICUBIC = "Bicubic"
    LANCZOS = "Lanczos"

    def to_pil(self) -> "Image.Resampling":
        """Return the Pillow resampling filter for this algorithm."""
        return {
            ResizeAlgorithm.NEAREST: Image.Resampling.NEAREST,
            ResizeAlgorithm.BILINEAR: Image.Resampling.BILINEAR,
            ResizeAlgorithm.BICUBIC: Image.Resampling.BICUBIC,
            ResizeAlgorithm.LANCZOS: Image.Resampling.LANCZOS,
        }[self]

    @classmethod
    def from_label(cls, label: str) -> "ResizeAlgorithm":
        """Look up an algorithm by its human-readable label."""
        for algo in cls:
            if algo.value == label:
                return algo
        raise ValueError(f"Unknown resize algorithm: {label!r}")


@dataclass
class LoadedImage:
    """An image that has been opened from disk and validated."""

    path: Path
    pil_image: Image.Image
    width: int
    height: int
    source_format: Optional[str]
    mode: str

    @property
    def total_pixels(self) -> int:
        """Number of pixels in the original image."""
        return self.width * self.height


@dataclass
class ProcessingOptions:
    """User-selected options controlling how the image is processed.

    When :attr:`use_original` is ``True`` the image is exported at its native
    resolution and the resize fields are ignored.
    """

    use_original: bool = True
    target_width: int = 0
    target_height: int = 0
    maintain_aspect: bool = True
    algorithm: ResizeAlgorithm = ResizeAlgorithm.LANCZOS

    def final_size(self, original_width: int, original_height: int) -> Tuple[int, int]:
        """Resolve the concrete output size for a given source image.

        Width is treated as authoritative when *maintain aspect ratio* is on,
        so the height is recomputed from the original ratio.  The result is
        always clamped to at least ``1 x 1``.
        """
        if self.use_original:
            return original_width, original_height

        width = max(1, int(self.target_width))
        height = max(1, int(self.target_height))

        if self.maintain_aspect and original_width > 0 and original_height > 0:
            ratio = original_height / original_width
            height = max(1, round(width * ratio))

        return width, height


@dataclass
class ProcessedImage:
    """The image after resizing/conversion, guaranteed to be in RGB mode."""

    pil_image: Image.Image
    width: int
    height: int

    @property
    def total_pixels(self) -> int:
        """Number of pixels in the processed image (the future block count)."""
        return self.width * self.height


@dataclass
class PixelMatrix:
    """A flat, row-major grid of RGB pixels.

    This is the universal hand-off object consumed by every exporter.  Storing
    a flat list keeps memory predictable for large images while still allowing
    convenient row-by-row iteration via :meth:`rows`.
    """

    width: int
    height: int
    pixels: List[RGB] = field(default_factory=list)

    @property
    def total_pixels(self) -> int:
        """Total number of pixels in the matrix."""
        return self.width * self.height

    def rows(self) -> Iterator[List[RGB]]:
        """Yield each image row as a list of ``(r, g, b)`` tuples."""
        width = self.width
        pixels = self.pixels
        for y in range(self.height):
            start = y * width
            yield pixels[start:start + width]


@dataclass
class ExportResult:
    """Summary of a completed export, surfaced to the user."""

    output_path: Path
    exporter_name: str
    width: int
    height: int
    pixel_count: int
    file_size_bytes: int
    duration_seconds: float
