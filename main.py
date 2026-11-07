"""PixelCSV launcher.

Run the application with::

    python main.py
"""

from __future__ import annotations

import sys

from pixelcsv.app import run

if __name__ == "__main__":
    sys.exit(run())
