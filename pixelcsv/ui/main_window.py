"""The application's main window.

This module is purely *presentation and orchestration*: it collects user
choices, hands them to the core pipeline (via a background worker) and displays
the results.  It never reads or writes pixels itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__
from ..config.settings import AppSettings
from ..core.exceptions import ImageLoadError, PixelCsvError
from ..core.exporters import ExporterRegistry, build_default_registry
from ..core.image_loader import ImageLoader
from ..core.image_processor import ImageProcessor
from ..core.models import ExportResult, ProcessingOptions, ResizeAlgorithm
from ..utils import format_duration, format_file_size, format_int
from .image_utils import make_preview_pixmap
from .theme import apply_theme
from .widgets import ImageDropArea, ImagePreview
from .worker import ConversionWorker

# Above this processed size we only thumbnail the original for the live preview
# (resizing the full image every keystroke would be wasteful).
_PREVIEW_PIXEL_CAP = 4_000_000
# Above this processed size we ask the user to confirm before converting.
_HUGE_PIXEL_WARNING = 12_000_000
_PREVIEW_DEBOUNCE_MS = 250


class MainWindow(QMainWindow):
    """Top-level window wiring the UI to the conversion pipeline."""

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.loader = ImageLoader()
        self.processor = ImageProcessor()
        self.registry: ExporterRegistry = build_default_registry()

        self.loaded_image = None  # type: Optional[object]
        self._aspect_ratio = 1.0  # original height / width
        self._syncing = False  # guards width<->height aspect linking
        self._worker: Optional[ConversionWorker] = None
        self._last_output: Optional[Path] = None

        self.setWindowTitle(f"{APP_NAME} — Image → RGB CSV Converter")
        self.setMinimumSize(1040, 680)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(_PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._update_processed_preview)

        self._build_menu()
        self._build_central()
        self._build_statusbar()
        self._restore_geometry()
        self._refresh_recent_menu()
        self._set_controls_enabled(False)

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open Image…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_action)

        self._recent_menu = file_menu.addMenu("Open &Recent")

        file_menu.addSeparator()
        folder_action = QAction("Set Output &Folder…", self)
        folder_action.triggered.connect(self._browse_output_folder)
        file_menu.addAction(folder_action)

        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("&View")
        self._dark_action = QAction("&Dark Mode", self, checkable=True)
        self._dark_action.setChecked(self.settings.dark_mode)
        self._dark_action.toggled.connect(self._on_dark_toggled)
        view_menu.addAction(self._dark_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 7, 14)

        self._preview_tabs = QTabWidget()
        self.original_preview = ImageDropArea("Drag & drop an image here\n\nor use “Open Image”")
        self.original_preview.imageDropped.connect(self._load_path)
        self.processed_preview = ImagePreview("Processed preview appears here")
        self._preview_tabs.addTab(self.original_preview, "Original")
        self._preview_tabs.addTab(self.processed_preview, "Processed")
        layout.addWidget(self._preview_tabs, stretch=1)

        open_button = QPushButton("Open Image…")
        open_button.clicked.connect(self._open_file_dialog)
        layout.addWidget(open_button)

        return panel

    def _build_right_panel(self) -> QWidget:
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(7, 14, 14, 14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(12)

        layout.addWidget(self._build_info_group())
        layout.addWidget(self._build_resolution_group())
        layout.addWidget(self._build_algorithm_group())
        layout.addWidget(self._build_output_group())
        layout.addWidget(self._build_estimate_group())
        layout.addWidget(self._build_results_group())
        layout.addStretch(1)

        scroll.setWidget(inner)
        outer.addWidget(scroll, stretch=1)

        self.convert_button = QPushButton("Convert →")
        self.convert_button.setObjectName("Primary")
        self.convert_button.clicked.connect(self._convert)
        outer.addWidget(self.convert_button)

        return container

    def _build_info_group(self) -> QGroupBox:
        group = QGroupBox("Image Information")
        form = QFormLayout(group)
        self.info_width = self._stat_value()
        self.info_height = self._stat_value()
        self.info_pixels = self._stat_value()
        form.addRow(self._stat_key("Width:"), self.info_width)
        form.addRow(self._stat_key("Height:"), self.info_height)
        form.addRow(self._stat_key("Total Pixels:"), self.info_pixels)
        return group

    def _build_resolution_group(self) -> QGroupBox:
        group = QGroupBox("Resolution")
        layout = QVBoxLayout(group)

        self.radio_original = QRadioButton("Original Resolution")
        self.radio_resize = QRadioButton("Resize Image")
        self.radio_original.setChecked(True)
        res_group = QButtonGroup(self)
        res_group.addButton(self.radio_original)
        res_group.addButton(self.radio_resize)
        self.radio_original.toggled.connect(self._on_resolution_changed)
        layout.addWidget(self.radio_original)
        layout.addWidget(self.radio_resize)

        self._resize_box = QWidget()
        form = QFormLayout(self._resize_box)
        form.setContentsMargins(18, 4, 0, 0)
        self.width_spin = QSpinBox()
        self.height_spin = QSpinBox()
        for spin in (self.width_spin, self.height_spin):
            spin.setRange(1, 100_000)
            spin.setValue(256)
        self.width_spin.valueChanged.connect(self._on_width_changed)
        self.height_spin.valueChanged.connect(self._on_height_changed)
        self.aspect_check = QCheckBox("Maintain aspect ratio")
        self.aspect_check.setChecked(True)
        self.aspect_check.toggled.connect(self._on_aspect_toggled)
        form.addRow("Width:", self.width_spin)
        form.addRow("Height:", self.height_spin)
        form.addRow("", self.aspect_check)
        layout.addWidget(self._resize_box)

        self._resize_box.setEnabled(False)
        return group

    def _build_algorithm_group(self) -> QGroupBox:
        group = QGroupBox("Resize Algorithm")
        layout = QVBoxLayout(group)
        self.algo_combo = QComboBox()
        for algo in ResizeAlgorithm:
            self.algo_combo.addItem(algo.value, algo)
        # Restore the remembered choice, defaulting to Lanczos.
        index = self.algo_combo.findText(self.settings.last_algorithm)
        if index < 0:
            index = self.algo_combo.findText(ResizeAlgorithm.LANCZOS.value)
        self.algo_combo.setCurrentIndex(max(0, index))
        self.algo_combo.currentIndexChanged.connect(self._on_algorithm_changed)
        layout.addWidget(self.algo_combo)
        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("Output")
        form = QFormLayout(group)

        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("output.csv")
        form.addRow("Filename:", self.filename_edit)

        self.format_combo = QComboBox()
        for exporter in self.registry.all():
            self.format_combo.addItem(exporter.name, exporter.key)
            self.format_combo.setItemData(
                self.format_combo.count() - 1, exporter.description, Qt.ItemDataRole.ToolTipRole
            )
        index = self.format_combo.findData(self.settings.last_format)
        self.format_combo.setCurrentIndex(max(0, index))
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        form.addRow("Format:", self.format_combo)

        folder_row = QWidget()
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setText(self.settings.output_dir or str(Path.home()))
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._browse_output_folder)
        folder_layout.addWidget(self.folder_edit, stretch=1)
        folder_layout.addWidget(browse_button)
        form.addRow("Folder:", folder_row)

        return group

    def _build_estimate_group(self) -> QGroupBox:
        group = QGroupBox("Output Estimate")
        form = QFormLayout(group)
        self.estimate_size = self._stat_value("—")
        self.estimate_blocks = self._stat_value("—")
        form.addRow(self._stat_key("Processed size:"), self.estimate_size)
        form.addRow(self._stat_key("Block count:"), self.estimate_blocks)
        return group

    def _build_results_group(self) -> QGroupBox:
        group = QGroupBox("Last Conversion")
        form = QFormLayout(group)
        self.result_time = self._stat_value("—")
        self.result_filesize = self._stat_value("—")
        form.addRow(self._stat_key("Time:"), self.result_time)
        form.addRow(self._stat_key("File size:"), self.result_filesize)
        self.open_folder_button = QPushButton("Open Output Folder")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self._open_output_folder)
        form.addRow("", self.open_folder_button)
        return group

    def _build_statusbar(self) -> None:
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setMaximumWidth(240)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().showMessage("Open an image to begin.")

    # ------------------------------------------------------------------ #
    # Small widget factories
    # ------------------------------------------------------------------ #
    @staticmethod
    def _stat_key(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("StatLabel")
        return label

    @staticmethod
    def _stat_value(text: str = "—") -> QLabel:
        label = QLabel(text)
        label.setObjectName("StatValue")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    # ------------------------------------------------------------------ #
    # Loading images
    # ------------------------------------------------------------------ #
    def _open_file_dialog(self) -> None:
        start_dir = self.settings.output_dir or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", start_dir, self.loader.file_dialog_filter()
        )
        if path:
            self._load_path(path)

    def _load_path(self, path: str) -> None:
        """Load an image from *path*, updating the whole UI or showing an error."""
        try:
            loaded = self.loader.load(path)
        except ImageLoadError as exc:
            self._error("Could not open image", str(exc))
            return
        except PixelCsvError as exc:  # pragma: no cover - defensive
            self._error("Could not open image", str(exc))
            return

        self.loaded_image = loaded
        self._aspect_ratio = (loaded.height / loaded.width) if loaded.width else 1.0

        # Populate image information.
        self.info_width.setText(f"{format_int(loaded.width)} px")
        self.info_height.setText(f"{format_int(loaded.height)} px")
        self.info_pixels.setText(format_int(loaded.total_pixels))

        # Seed resize fields with the native size (without firing aspect sync).
        self._syncing = True
        self.width_spin.setValue(loaded.width)
        self.height_spin.setValue(loaded.height)
        self._syncing = False

        # Default the output filename from the image name + current format.
        exporter = self._current_exporter()
        self.filename_edit.setText(loaded.path.stem + exporter.extension)

        # Show the original preview.
        try:
            self.original_preview.set_pixmap(make_preview_pixmap(loaded.pil_image))
        except Exception:  # pragma: no cover - preview is non-critical
            self.original_preview.clear_image()

        self.settings.add_recent_file(str(loaded.path))
        self._refresh_recent_menu()
        self._set_controls_enabled(True)
        self.statusBar().showMessage(
            f"Loaded {loaded.path.name}  ·  {loaded.source_format or '?'}  ·  "
            f"{format_int(loaded.total_pixels)} pixels"
        )
        self._update_estimate()
        self._update_processed_preview()

    # ------------------------------------------------------------------ #
    # Resolution / aspect handling
    # ------------------------------------------------------------------ #
    def _on_resolution_changed(self) -> None:
        self._resize_box.setEnabled(self.radio_resize.isChecked())
        self._update_estimate()
        self._schedule_preview()

    def _on_aspect_toggled(self, checked: bool) -> None:
        if checked:
            self._sync_height_from_width()
        self._update_estimate()
        self._schedule_preview()

    def _on_width_changed(self, value: int) -> None:
        if not self._syncing and self.aspect_check.isChecked():
            self._sync_height_from_width()
        self._update_estimate()
        self._schedule_preview()

    def _on_height_changed(self, value: int) -> None:
        if not self._syncing and self.aspect_check.isChecked():
            self._sync_width_from_height()
        self._update_estimate()
        self._schedule_preview()

    def _sync_height_from_width(self) -> None:
        self._syncing = True
        height = max(1, round(self.width_spin.value() * self._aspect_ratio))
        self.height_spin.setValue(height)
        self._syncing = False

    def _sync_width_from_height(self) -> None:
        self._syncing = True
        ratio = self._aspect_ratio if self._aspect_ratio else 1.0
        width = max(1, round(self.height_spin.value() / ratio))
        self.width_spin.setValue(width)
        self._syncing = False

    def _on_algorithm_changed(self) -> None:
        self.settings.last_algorithm = self.algo_combo.currentText()
        self._schedule_preview()

    def _on_format_changed(self) -> None:
        exporter = self._current_exporter()
        self.settings.last_format = exporter.key
        # Keep the filename's extension in sync with the chosen format.
        current = self.filename_edit.text().strip()
        if current:
            self.filename_edit.setText(str(Path(current).with_suffix(exporter.extension)))

    # ------------------------------------------------------------------ #
    # Estimate + processed preview
    # ------------------------------------------------------------------ #
    def _current_options(self) -> ProcessingOptions:
        return ProcessingOptions(
            use_original=self.radio_original.isChecked(),
            target_width=self.width_spin.value(),
            target_height=self.height_spin.value(),
            maintain_aspect=self.aspect_check.isChecked(),
            algorithm=self.algo_combo.currentData(),
        )

    def _current_exporter(self):
        return self.registry.get(self.format_combo.currentData())

    def _update_estimate(self) -> None:
        if self.loaded_image is None:
            self.estimate_size.setText("—")
            self.estimate_blocks.setText("—")
            return
        options = self._current_options()
        width, height = options.final_size(
            self.loaded_image.width, self.loaded_image.height
        )
        self.estimate_size.setText(f"{format_int(width)} × {format_int(height)}")
        self.estimate_blocks.setText(f"{format_int(width * height)} blocks")

    def _schedule_preview(self) -> None:
        # Skip while a conversion is running so we never touch the shared PIL
        # image from two threads at once.
        if self.loaded_image is not None and self._worker is None:
            self._preview_timer.start()

    def _update_processed_preview(self) -> None:
        if self.loaded_image is None or self._worker is not None:
            return
        options = self._current_options()
        width, height = options.final_size(
            self.loaded_image.width, self.loaded_image.height
        )
        try:
            if width * height <= _PREVIEW_PIXEL_CAP:
                processed = self.processor.process(self.loaded_image, options)
                pixmap = make_preview_pixmap(processed.pil_image)
            else:
                # Too large to resize on every change — show the original.
                pixmap = make_preview_pixmap(self.loaded_image.pil_image)
            self.processed_preview.set_pixmap(pixmap)
        except Exception:  # pragma: no cover - preview must never crash the app
            self.processed_preview.set_placeholder("Preview unavailable")
            self.processed_preview.clear_image()

    # ------------------------------------------------------------------ #
    # Output folder
    # ------------------------------------------------------------------ #
    def _browse_output_folder(self) -> None:
        start = self.folder_edit.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", start)
        if folder:
            self.folder_edit.setText(folder)
            self.settings.output_dir = folder

    # ------------------------------------------------------------------ #
    # Conversion
    # ------------------------------------------------------------------ #
    def _convert(self) -> None:
        if self.loaded_image is None:
            self._error("No image", "Please open an image before converting.")
            return

        options = self._current_options()
        width, height = options.final_size(
            self.loaded_image.width, self.loaded_image.height
        )
        if width < 1 or height < 1:
            self._error("Invalid size", "Width and height must be at least 1 pixel.")
            return

        folder_text = self.folder_edit.text().strip()
        if not folder_text or not Path(folder_text).is_dir():
            self._error("Invalid folder", "Please choose a valid output folder.")
            return

        filename = self.filename_edit.text().strip()
        if not filename:
            self._error("Missing filename", "Please enter an output filename.")
            return

        exporter = self._current_exporter()
        output_path = exporter.ensure_extension(Path(folder_text) / filename)

        if output_path.exists():
            reply = QMessageBox.question(
                self,
                "Overwrite file?",
                f"“{output_path.name}” already exists.\n\nOverwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if width * height > _HUGE_PIXEL_WARNING:
            reply = QMessageBox.question(
                self,
                "Large conversion",
                f"This will write {format_int(width * height)} pixels and may take a "
                "while and produce a large file.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._start_worker(options, exporter, output_path)

    def _start_worker(self, options, exporter, output_path: Path) -> None:
        self._set_busy(True)
        self.statusBar().showMessage(f"Converting → {output_path.name} …")

        worker = ConversionWorker(self.loaded_image, options, exporter, output_path)
        worker.progress.connect(self.progress_bar.setValue)
        worker.succeeded.connect(self._on_conversion_succeeded)
        worker.failed.connect(self._on_conversion_failed)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker
        worker.start()

    def _on_conversion_succeeded(self, result: ExportResult) -> None:
        self._last_output = result.output_path
        self.settings.output_dir = str(result.output_path.parent)
        self.result_time.setText(format_duration(result.duration_seconds))
        self.result_filesize.setText(format_file_size(result.file_size_bytes))
        self.open_folder_button.setEnabled(True)
        self.statusBar().showMessage(
            f"Saved {result.output_path.name}  ·  "
            f"{format_int(result.pixel_count)} pixels  ·  "
            f"{format_file_size(result.file_size_bytes)}  ·  "
            f"{format_duration(result.duration_seconds)}"
        )

    def _on_conversion_failed(self, message: str) -> None:
        self._error("Conversion failed", message)
        self.statusBar().showMessage("Conversion failed.")

    def _on_worker_finished(self) -> None:
        self._set_busy(False)
        self._worker = None

    # ------------------------------------------------------------------ #
    # Misc actions
    # ------------------------------------------------------------------ #
    def _open_output_folder(self) -> None:
        if self._last_output is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output.parent)))

    def _on_dark_toggled(self, checked: bool) -> None:
        self.settings.dark_mode = checked
        apply_theme(QApplication.instance(), checked)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h3>{APP_NAME} {__version__}</h3>"
            "<p>Convert images into exact RGB data files.</p>"
            "<p>Each output cell stores a pixel's <b>R,G,B</b> values with no "
            "approximation — ready to be read by a custom Minecraft builder mod.</p>"
            "<p>Built with PySide6 &amp; Pillow.</p>",
        )

    def _refresh_recent_menu(self) -> None:
        self._recent_menu.clear()
        recents = self.settings.recent_files
        if not recents:
            empty = QAction("(none)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
            return
        for path in recents:
            action = QAction(path, self)
            action.triggered.connect(lambda _=False, p=path: self._load_path(p))
            self._recent_menu.addAction(action)
        self._recent_menu.addSeparator()
        clear = QAction("Clear Recent Files", self)
        clear.triggered.connect(self._clear_recent)
        self._recent_menu.addAction(clear)

    def _clear_recent(self) -> None:
        self.settings.clear_recent_files()
        self._refresh_recent_menu()

    # ------------------------------------------------------------------ #
    # Enable / disable + window state
    # ------------------------------------------------------------------ #
    def _set_controls_enabled(self, enabled: bool) -> None:
        self.convert_button.setEnabled(enabled)

    def _set_busy(self, busy: bool) -> None:
        self.progress_bar.setVisible(busy)
        self.progress_bar.setValue(0)
        self.convert_button.setEnabled(not busy)
        self.convert_button.setText("Converting…" if busy else "Convert →")

    def _error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def _restore_geometry(self) -> None:
        geometry = self.settings.window_geometry
        if geometry is not None:
            self.restoreGeometry(geometry)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.settings.window_geometry = self.saveGeometry()
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(2000)
        super().closeEvent(event)
