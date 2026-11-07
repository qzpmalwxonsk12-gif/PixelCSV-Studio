"""The exporter interface that every output format implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional, Union

from ..models import PixelMatrix

#: A progress callback receives a fraction in the range ``0.0 .. 1.0``.
ProgressCallback = Callable[[float], None]

PathLike = Union[str, Path]


class Exporter(ABC):
    """Base class for all exporters.

    Subclasses describe themselves through four class attributes and implement
    a single :meth:`export` method.  Keeping the contract this small is what
    makes the format list trivially extensible.

    Attributes
    ----------
    key:
        Stable identifier used in settings and the registry (e.g. ``"csv"``).
    name:
        Human-readable label shown in the UI.
    extension:
        Default file extension, including the leading dot (e.g. ``".csv"``).
    description:
        One-line summary shown as a tooltip/help text.
    """

    key: str = ""
    name: str = ""
    extension: str = ""
    description: str = ""

    @abstractmethod
    def export(
        self,
        matrix: PixelMatrix,
        path: PathLike,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        """Write *matrix* to *path*.

        Implementations should stream their output (row by row) rather than
        building the whole file in memory, and should call ``progress_cb`` with
        the completed fraction periodically when it is provided.

        Raises
        ------
        ExportError
            If writing fails for any reason.
        """
        raise NotImplementedError

    def ensure_extension(self, path: PathLike) -> Path:
        """Return *path* with this exporter's extension applied if missing."""
        result = Path(path)
        if result.suffix.lower() != self.extension.lower():
            result = result.with_suffix(self.extension)
        return result
