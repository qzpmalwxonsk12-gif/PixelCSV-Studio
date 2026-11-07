# PixelCSV — Image → RGB CSV Converter

## Repository guide

PixelCSV is a desktop image-to-data tool, built with **Python, PySide6 and Pillow**. It lets you inspect/transform an image and export its pixel data through the available CSV/JSON/binary exporters. It produces data for other workflows; it does not itself install a Minecraft mod or place blocks in a running world.

Use a Python environment compatible with `requirements.txt`. A typical Windows source setup is:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

The UI lives under `pixelcsv/ui/`, the transformation/export pipeline under `pixelcsv/core/`, and settings/support code under `pixelcsv/config/`. Tests are in `tests/`. Generated artwork collections and old exported copies are not separate application dependencies.

Check output dimensions, colour representation and the destination tool's CSV conventions before a large export. “RGB CSV” and “Minecraft block-name blueprint CSV” are different formats; use the consumer's documented format rather than assuming every CSV is interchangeable. The detailed export/extension guide follows.

A clean, modern desktop utility that converts images into files where **every
cell holds one pixel's exact `R,G,B` value**. It was built to feed a custom
Minecraft *builder* mod that places blocks whose colour is set from the data —
but the converter itself contains **no Minecraft-specific logic**. Its only job
is to preserve an image's RGB information as accurately as possible.

> No hex. No compression. No approximation. The values written are exactly the
> RGB values of the processed image.

Built with **Python + PySide6 (Qt)** and **Pillow**.

---

## Features

- **Drag & drop** an image, or use the **Open Image** button / `Ctrl+O`
- Live **original** and **processed** previews
- Image information: width, height, total pixels
- **Resolution options**: keep original, or resize to a target width/height
  with an optional **Maintain aspect ratio** lock
- **Resize algorithms**: Nearest Neighbor, Bilinear, Bicubic, **Lanczos**
  (default)
- **Output estimate**: processed size and estimated block count
  (e.g. `256 × 256` → `65,536 blocks`)
- Background conversion that keeps the UI responsive, with a progress bar
- Robust **validation**: rejects unsupported files, guards against huge
  images, and surfaces friendly errors — it never crashes on bad input
- Reports **conversion time** and **output file size**
- **Remembers** your last output folder, theme, algorithm and format
- **Recent files** list and a **dark mode** toggle

### Export formats

The exporter layer is fully pluggable. Three formats ship today:

| Format | Extension | Description |
| ------ | --------- | ----------- |
| **CSV** (default) | `.csv` | One row per image row; each cell is a quoted `"R, G, B"` pixel |
| JSON | `.json` | `{ "width", "height", "pixels": [[[r,g,b], …], …] }` |
| Binary | `.pxrgb` | 8-byte header + width/height + raw RGB bytes |

#### CSV layout

For a 2×2 image:

```
Red   Green
Blue  White
```

PixelCSV writes:

```
"255, 0, 0","0, 255, 0"
"0, 0, 255","255, 255, 255"
```

Each pixel is one cell containing its `R, G, B` value. Two details make this
behave in spreadsheets:

* the cell is **quoted** so the commas stay *inside* the cell — the comma can
  then act as the column separator between pixels, and Excel / Sheets puts each
  pixel in its own cell (`A1` shows `255, 0, 0`)
* a **space follows each component** so the cell is treated as text rather than
  parsed as one large number (which otherwise displayed as `#####`)

Any RFC-4180 CSV reader handles the quoting automatically; when parsing a cell,
split on `,` and call `int()` on each part (`int(" 34")` ignores the space).

---

## Getting started

Requires **Python 3.9+**.

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. install dependencies
pip install -r requirements.txt

# 3. run
python main.py
```

---

## Project structure

```
newproject3/
├── main.py                     # launcher
├── requirements.txt
├── README.md
└── pixelcsv/
    ├── __init__.py             # app metadata
    ├── app.py                  # QApplication bootstrap
    ├── utils.py                # formatting helpers
    ├── config/
    │   └── settings.py         # persistent QSettings wrapper
    ├── core/                   # UI-independent pipeline (runs head-less)
    │   ├── exceptions.py       # typed error hierarchy
    │   ├── models.py           # LoadedImage, PixelMatrix, options, …
    │   ├── image_loader.py     # open + validate images
    │   ├── image_processor.py  # resize + extract pixels
    │   └── exporters/          # pluggable output formats
    │       ├── base.py         # Exporter interface
    │       ├── registry.py     # format registry
    │       ├── csv_exporter.py
    │       ├── json_exporter.py
    │       └── binary_exporter.py
    └── ui/                     # PySide6 presentation layer
        ├── main_window.py
        ├── theme.py            # light / dark styling
        ├── worker.py           # background conversion thread
        ├── image_utils.py      # Pillow → QPixmap bridge
        └── widgets/
            └── preview.py      # preview + drag-and-drop surface
```

### Architecture principles

- **The UI never manipulates image data directly.** It only constructs
  `core` objects and hands them to a background `ConversionWorker`.
- **The pipeline is linear and pure:**
  `ImageLoader` → `ImageProcessor` → `PixelMatrix` → `Exporter`.
- **Exporters are decoupled from Pillow.** They only ever see a `PixelMatrix`,
  which is what makes new formats trivial to add.

---

## Adding a new export format

1. Create a subclass of `Exporter` in `pixelcsv/core/exporters/`:

   ```python
   from .base import Exporter

   class XlsxExporter(Exporter):
       key = "xlsx"
       name = "Excel Spreadsheet"
       extension = ".xlsx"
       description = "One worksheet cell per pixel."

       def export(self, matrix, path, progress_cb=None):
           ...  # write the file, optionally calling progress_cb(fraction)
   ```

2. Register it in `build_default_registry()` in `registry.py`.

That's it — it instantly appears in the format selector. The same pattern
supports future input types (e.g. an `ObjLoader` or `VideoLoader` feeding the
exact same `PixelMatrix` → exporter path) without touching the image pipeline.

---

## Notes on accuracy

- Images are converted to RGB **before** resizing, so resampling always
  operates on true colour data (important for palette/animated sources).
- The exported values are read straight from the processed image with
  `Image.getdata()` — no rounding or remapping is applied beyond the chosen
  resize algorithm.
- Alpha is dropped (RGB only) by design, since the target consumer stores RGB.

---

## License

Provided as-is for use with your custom Minecraft builder mod.


## Source snapshot and validation

See [BACKUP_NOTES.md](BACKUP_NOTES.md) for the omitted build outputs, local settings, credentials and runtime data. Build generated binaries locally using the instructions above; a source checkout is not an installed application. Earlier validation figures in this guide describe their original development runs. This documentation update checks source references and instructions; it does not claim a fresh application, device or gameplay test.
