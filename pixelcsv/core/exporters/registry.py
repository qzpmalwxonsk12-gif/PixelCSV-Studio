"""Registry that holds the available exporters.

The UI asks the registry which formats exist and looks them up by key.  To add
a format application-wide, implement an :class:`Exporter` subclass and register
it in :func:`build_default_registry` — nothing else needs to change.
"""

from __future__ import annotations

from typing import Dict, List

from .base import Exporter
from .binary_exporter import BinaryExporter
from .csv_exporter import CsvExporter
from .json_exporter import JsonExporter


class ExporterRegistry:
    """An ordered collection of exporters keyed by their ``key``."""

    def __init__(self) -> None:
        self._exporters: Dict[str, Exporter] = {}

    def register(self, exporter: Exporter) -> None:
        """Add (or replace) an exporter in the registry."""
        if not exporter.key:
            raise ValueError(f"{type(exporter).__name__} has no key")
        self._exporters[exporter.key] = exporter

    def get(self, key: str) -> Exporter:
        """Return the exporter registered under *key*."""
        try:
            return self._exporters[key]
        except KeyError as exc:
            raise KeyError(f"No exporter registered for key {key!r}") from exc

    def all(self) -> List[Exporter]:
        """Return every registered exporter, in registration order."""
        return list(self._exporters.values())

    def __contains__(self, key: object) -> bool:
        return key in self._exporters

    def __len__(self) -> int:
        return len(self._exporters)


def build_default_registry() -> ExporterRegistry:
    """Create a registry pre-loaded with the bundled exporters.

    CSV is registered first so it is the default selection in the UI.
    """
    registry = ExporterRegistry()
    registry.register(CsvExporter())
    registry.register(JsonExporter())
    registry.register(BinaryExporter())
    return registry
