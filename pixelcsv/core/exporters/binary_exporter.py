"""Binary exporter — a compact, fast-to-parse raw-RGB container.

File layout (all integers little-endian)::

    offset  size  field
    0       8     magic  = b"PXRGB1\\0\\0"
    8       4     uint32 width
    12      4     uint32 height
    16      ...   width*height*3 bytes of raw R,G,B data (row-major)

This is the kind of format a performance-sensitive consumer (such as a mod
loading thousands of blocks) might prefer.  It exists here mainly to prove the
exporter architecture supports binary as easily as text.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Optional

from ..exceptions import ExportError
from ..models import PixelMatrix
from .base import Exporter, PathLike, ProgressCallback

#: 8-byte file signature.
MAGIC = b"PXRGB1\x00\x00"

_PROGRESS_STEPS = 100


class BinaryExporter(Exporter):
    """Writes a pixel matrix as a compact raw-RGB binary file."""

    key = "binary"
    name = "Binary (raw RGB .pxrgb)"
    extension = ".pxrgb"
    description = "8-byte header + width/height + raw RGB bytes; compact & fast."

    def export(
        self,
        matrix: PixelMatrix,
        path: PathLike,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        """Stream *matrix* to *path* as binary RGB data."""
        out_path = Path(path)
        height = matrix.height
        width = matrix.width
        report_every = max(1, height // _PROGRESS_STEPS)

        try:
            with out_path.open("wb") as handle:
                handle.write(MAGIC)
                handle.write(struct.pack("<II", width, height))

                for y, row in enumerate(matrix.rows()):
                    chunk = bytearray()
                    for r, g, b in row:
                        chunk += bytes((r & 0xFF, g & 0xFF, b & 0xFF))
                    handle.write(chunk)

                    if progress_cb is not None and y % report_every == 0:
                        progress_cb((y + 1) / height if height else 1.0)

            if progress_cb is not None:
                progress_cb(1.0)
        except OSError as exc:
            raise ExportError(
                f"Could not write the binary file.\n\nDetails: {exc}"
            ) from exc
