"""Head-less tests for the core pipeline.

These run without Qt or a display, which is exactly the point of keeping the
core decoupled from the UI.  Run with::

    python -m pytest        # if pytest is installed
    python tests/test_core_pipeline.py   # plain-Python fallback
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image

# Make the project importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pixelcsv.core.exporters import build_default_registry  # noqa: E402
from pixelcsv.core.image_loader import ImageLoader  # noqa: E402
from pixelcsv.core.image_processor import ImageProcessor  # noqa: E402
from pixelcsv.core.models import ProcessingOptions, ResizeAlgorithm  # noqa: E402


def _make_sample(path: Path) -> None:
    """Create the 2x2 reference image: red, green / blue, white."""
    image = Image.new("RGB", (2, 2))
    image.putpixel((0, 0), (255, 0, 0))
    image.putpixel((1, 0), (0, 255, 0))
    image.putpixel((0, 1), (0, 0, 255))
    image.putpixel((1, 1), (255, 255, 255))
    image.save(path)


def test_csv_roundtrip_matches_spec() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "sample.png"
        _make_sample(src)

        loaded = ImageLoader().load(src)
        assert (loaded.width, loaded.height) == (2, 2)

        processor = ImageProcessor()
        processed = processor.process(loaded, ProcessingOptions(use_original=True))
        matrix = processor.extract_matrix(processed)
        assert matrix.total_pixels == 4

        out = tmp_path / "out.csv"
        build_default_registry().get("csv").export(matrix, out)

        text = out.read_text(encoding="utf-8").strip()
        assert text == '"255, 0, 0","0, 255, 0"\n"0, 0, 255","255, 255, 255"'


def test_resize_with_aspect_ratio() -> None:
    options = ProcessingOptions(
        use_original=False,
        target_width=100,
        target_height=999,  # ignored when aspect is maintained
        maintain_aspect=True,
        algorithm=ResizeAlgorithm.LANCZOS,
    )
    # 200x100 source -> ratio 0.5 -> height should follow width.
    assert options.final_size(200, 100) == (100, 50)


def test_unsupported_format_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bogus = Path(tmp) / "notes.txt"
        bogus.write_text("not an image")
        try:
            ImageLoader().load(bogus)
        except Exception as exc:  # noqa: BLE001 - we assert the type below
            assert "Unsupported" in type(exc).__name__ or "unsupported" in str(exc).lower()
        else:  # pragma: no cover
            raise AssertionError("Expected an error for unsupported file")


if __name__ == "__main__":
    test_csv_roundtrip_matches_spec()
    test_resize_with_aspect_ratio()
    test_unsupported_format_is_rejected()
    print("All core pipeline tests passed.")
