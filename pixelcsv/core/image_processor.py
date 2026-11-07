"""Image processing: resizing and pixel extraction.

This module is intentionally tiny and pure: it turns a :class:`LoadedImage`
plus :class:`ProcessingOptions` into a :class:`ProcessedImage`, and a
:class:`ProcessedImage` into a :class:`PixelMatrix`.  Nothing here knows about
files, exporters or the UI, which keeps the pipeline easy to reason about.
"""

from __future__ import annotations

from typing import Callable, Optional

from PIL import Image

from .exceptions import ProcessingError
from .models import LoadedImage, PixelMatrix, ProcessedImage, ProcessingOptions

#: A progress callback receives a fraction in the range ``0.0 .. 1.0``.
ProgressCallback = Callable[[float], None]


class ImageProcessor:
    """Resizes images and extracts their RGB pixel data.

    The two responsibilities are split into :meth:`process` (produce the final
    RGB image) and :meth:`extract_matrix` (read the pixels) so the UI can do a
    cheap resize for the live preview without paying for full pixel extraction.
    """

    def process(self, loaded: LoadedImage, options: ProcessingOptions) -> ProcessedImage:
        """Apply resize options and guarantee an RGB result.

        The image is converted to RGB *before* resizing so that resampling is
        always performed on true colour data (important for palette/animated
        sources), preserving the original RGB values as faithfully as possible.
        """
        try:
            image = loaded.pil_image

            # Convert first so resampling operates on real RGB data.
            if image.mode != "RGB":
                image = image.convert("RGB")

            target_width, target_height = options.final_size(
                loaded.width, loaded.height
            )

            if (target_width, target_height) != (image.width, image.height):
                image = image.resize(
                    (target_width, target_height), options.algorithm.to_pil()
                )

            return ProcessedImage(
                pil_image=image,
                width=image.width,
                height=image.height,
            )
        except ProcessingError:
            raise
        except (OSError, ValueError, MemoryError) as exc:
            raise ProcessingError(f"Failed to process the image.\n\nDetails: {exc}") from exc

    def extract_matrix(
        self,
        processed: ProcessedImage,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> PixelMatrix:
        """Read every pixel of *processed* into a :class:`PixelMatrix`.

        ``progress_cb`` (if supplied) is called periodically with the fraction
        of work completed, so a long extraction can drive a progress bar.
        """
        try:
            image = processed.pil_image
            if image.mode != "RGB":
                image = image.convert("RGB")

            if progress_cb is not None:
                progress_cb(0.0)

            # ``getdata`` returns a flat, row-major sequence of (r, g, b) tuples
            # for an RGB image — exactly the layout PixelMatrix expects.
            pixels = list(image.getdata())

            if progress_cb is not None:
                progress_cb(1.0)

            return PixelMatrix(
                width=processed.width,
                height=processed.height,
                pixels=pixels,
            )
        except (OSError, ValueError, MemoryError) as exc:
            raise ProcessingError(
                f"Failed to read pixels from the image.\n\nDetails: {exc}"
            ) from exc
