"""Image loading and validation.

The loader is the single gatekeeper for getting pixels into the application.
It rejects unsupported files early, guards against decompression bombs (huge
images) and translates every low-level Pillow failure into a friendly
:class:`~pixelcsv.core.exceptions.ImageLoadError` subclass so the UI can show a
meaningful message instead of crashing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union

from PIL import Image, UnidentifiedImageError

from .exceptions import ImageLoadError, ImageTooLargeError, UnsupportedFormatError
from .models import LoadedImage

# Raise Pillow's built-in "decompression bomb" ceiling to a deliberately large
# but bounded value.  Anything beyond this is almost certainly malicious or a
# mistake, and we surface it as a clean error rather than risking the process.
Image.MAX_IMAGE_PIXELS = 512_000_000  # ~512 megapixels

PathLike = Union[str, Path]


class ImageLoader:
    """Loads images from disk and validates them.

    Example
    -------
    >>> loader = ImageLoader()
    >>> loaded = loader.load("photo.png")
    >>> loaded.width, loaded.height
    (1920, 1080)
    """

    #: File extensions the application accepts.
    SUPPORTED_EXTENSIONS = frozenset(
        {
            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
            ".gif",
            ".tif",
            ".tiff",
            ".webp",
            ".ppm",
            ".pgm",
            ".ico",
        }
    )

    @classmethod
    def supported_extensions(cls) -> Iterable[str]:
        """Return the supported extensions, sorted for display."""
        return sorted(cls.SUPPORTED_EXTENSIONS)

    @classmethod
    def file_dialog_filter(cls) -> str:
        """Build a Qt-style ``QFileDialog`` name filter string."""
        patterns = " ".join(f"*{ext}" for ext in cls.supported_extensions())
        return f"Images ({patterns});;All files (*)"

    @classmethod
    def is_supported(cls, path: PathLike) -> bool:
        """Return ``True`` if *path* has a supported image extension."""
        return Path(path).suffix.lower() in cls.SUPPORTED_EXTENSIONS

    def load(self, path: PathLike) -> LoadedImage:
        """Open and fully decode an image, returning a :class:`LoadedImage`.

        Raises
        ------
        UnsupportedFormatError
            If the path does not exist, is not a file, or has an unsupported
            extension / unrecognised content.
        ImageTooLargeError
            If the image exceeds the safe decoding limit.
        ImageLoadError
            For any other decoding failure.
        """
        file_path = Path(path)

        if not file_path.exists():
            raise UnsupportedFormatError(f"File does not exist:\n{file_path}")
        if not file_path.is_file():
            raise UnsupportedFormatError(f"Not a file:\n{file_path}")
        if not self.is_supported(file_path):
            allowed = ", ".join(self.supported_extensions())
            raise UnsupportedFormatError(
                f"Unsupported file type: {file_path.suffix or '(none)'}\n\n"
                f"Supported types: {allowed}"
            )

        try:
            image = Image.open(file_path)
            # ``open`` is lazy; force a full decode now so any corruption or
            # size problem surfaces here where we can handle it cleanly.
            image.load()
        except Image.DecompressionBombError as exc:
            raise ImageTooLargeError(
                "This image is too large to process safely.\n\n"
                f"Details: {exc}"
            ) from exc
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageLoadError(
                f"Could not read this image. It may be corrupt or unsupported.\n\n"
                f"Details: {exc}"
            ) from exc

        return LoadedImage(
            path=file_path,
            pil_image=image,
            width=image.width,
            height=image.height,
            source_format=image.format,
            mode=image.mode,
        )
