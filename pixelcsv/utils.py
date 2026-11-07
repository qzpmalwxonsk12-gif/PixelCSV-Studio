"""Small, dependency-free formatting helpers used by the UI."""

from __future__ import annotations


def format_int(value: int) -> str:
    """Format an integer with thousands separators (e.g. ``65,536``)."""
    return f"{value:,}"


def format_file_size(num_bytes: int) -> str:
    """Return a human-readable file size such as ``1.2 MB``."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def format_duration(seconds: float) -> str:
    """Return a compact human-readable duration such as ``1.4 s`` or ``320 ms``."""
    if seconds < 1.0:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60.0:
        return f"{seconds:.2f} s"
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)} min {secs:.0f} s"
