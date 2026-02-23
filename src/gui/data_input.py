"""Step 1: Data Loading panel for the GUI.

Handles loading filament reference, von Frey data, and metadata files.
Provides column mapping dropdowns and threshold computation.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.data_loader import (
    check_mouse_id_match,
    detect_column_candidates,
    load_excel_or_csv,
    merge_metadata,
    validate_data_columns,
    validate_metadata_columns,
)
from ..core.vf_threshold import compute_thresholds_batch, load_filament_reference
from .state import AnalysisState


class ThresholdWorker(QThread):
    """Worker thread for computing thresholds without blocking the GUI."""

    finished = pyqtSignal(object)  # emits the updated DataFrame
    error = pyqtSignal(str)

    def __init__(
        self,
        df: object,
        filament_info: object,
        series_stats: dict,
        series_col: str,
        filament_col: str,
        log_column: str,
    ):
        super().__init__()
        self.df = df
        self.filament_info = filament_info
        self.series_stats = series_stats
        self.series_col = series_col
        self.filament_col = filament_col
        self.log_column = log_column

    def run(self) -> None:
        try:
            self.df["threshold_50"] = compute_thresholds_batch(
                self.df,
                self.filament_info,
                self.series_stats,
                series_col=self.series_col,
                filament_col=self.filament_col,
                log_column=self.log_column,
            )
            self.finished.emit(self.df)
        except Exception as e:
            self.error.emit(str(e))


class DataInputPanel(QWidget):
    """Step 1: Data loading and column mapping panel."""

    data_ready = pyqtSignal()  # emitted when thresholds are computed

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._worker: ThresholdWorker | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Filament reference file ──────────────────────────────────────
        filament_group = QGroupBox("Filament Reference File (required)")
        fg_layout = QVBoxLayout(filament_group)

        row = QHBoxLayout()
        self.filament_path_edit = QLineEdit()
        self.filament_path_edit.setReadOnly(True)
        self.filament_path_edit.setPlaceholderText("Select VF_Calculator_Up-down.xlsx")
        btn = QPushButton("Browse...")
        btn.clicked.connect(self._browse_filament_ref)
        row.addWidget(self.filament_path_edit, stretch=1)
        row.addWidget(btn)
        fg_layout.addLayout(row)

        self.filament_status = QLabel("")
        fg_layout.addWidget(self.filament_status)

        # Log column selection
        log_row = QHBoxLayout()
        log_row.addWidget(QLabel("Log column:"))
        self.log_new_radio = QRadioButton("Log_new (computed)")
        self.log_old_radio = QRadioButton("Log (from Excel)")
        self.log_new_radio.setChecked(True)
        self.log_new_radio.setToolTip("Use log values computed from force: log10(10 * force_g * 1000)")
        self.log_old_radio.setToolTip("Use log values as stored in the Excel file")
        log_row.addWidget(self.log_new_radio)
        log_row.addWidget(self.log_old_radio)
        log_row.addStretch()
        fg_layout.addLayout(log_row)

        layout.addWidget(filament_group)

        # ── Data file ────────────────────────────────────────────────────
        data_group = QGroupBox("Von Frey Data File")
        dg_layout = QVBoxLayout(data_group)

        row = QHBoxLayout()
        self.data_path_edit = QLineEdit()
        self.data_path_edit.setReadOnly(True)
        self.data_path_edit.setPlaceholderText("Select data file (.xlsx, .csv)")
        btn = QPushButton("Browse...")
        btn.clicked.connect(self._browse_data_file)
        row.addWidget(self.data_path_edit, stretch=1)
        row.addWidget(btn)
        dg_layout.addLayout(row)

        self.data_status = QLabel("")
        dg_layout.addWidget(self.data_status)

        # Column mapping
        mapping_layout = QHBoxLayout()
        self.mouse_combo = self._make_combo("Mouse ID column:", mapping_layout)
        self.timepoint_combo = self._make_combo("Timepoint column:", mapping_layout)
        self.series_combo = self._make_combo("XO Series column:", mapping_layout)
        self.filament_combo = self._make_combo("Last Filament col:", mapping_layout)
        dg_layout.addLayout(mapping_layout)

        layout.addWidget(data_group)

        # ── Metadata file ────────────────────────────────────────────────
        meta_group = QGroupBox("Metadata File")
        mg_layout = QVBoxLayout(meta_group)

        row = QHBoxLayout()
        self.meta_path_edit = QLineEdit()
        self.meta_path_edit.setReadOnly(True)
        self.meta_path_edit.setPlaceholderText("Select metadata file (.xlsx, .csv)")
        btn = QPushButton("Browse...")
        btn.clicked.connect(self._browse_metadata_file)
        row.addWidget(self.meta_path_edit, stretch=1)
        row.addWidget(btn)
        mg_layout.addLayout(row)

        self.meta_status = QLabel("")
        mg_layout.addWidget(self.meta_status)

        gender_row = QHBoxLayout()
        gender_row.addWidget(QLabel("Gender column:"))
        self.gender_combo = QComboBox()
        self.gender_combo.setMinimumWidth(150)
        gender_row.addWidget(self.gender_combo)
        gender_row.addWidget(QLabel("Mouse ID column:"))
        self.meta_mouse_combo = QComboBox()
        self.meta_mouse_combo.setMinimumWidth(150)
        gender_row.addWidget(self.meta_mouse_combo)
        gender_row.addStretch()
        mg_layout.addLayout(gender_row)

        layout.addWidget(meta_group)

        # ── Compute button ───────────────────────────────────────────────
        self.compute_btn = QPushButton("Compute Thresholds")
        self.compute_btn.setEnabled(False)
        self.compute_btn.setStyleSheet("QPushButton { padding: 8px; font-weight: bold; }")
        self.compute_btn.clicked.connect(self._compute_thresholds)
        layout.addWidget(self.compute_btn)

        # ── Preview table ────────────────────────────────────────────────
        layout.addWidget(QLabel("Preview:"))
        self.preview_table = QTableWidget()
        self.preview_table.setMinimumHeight(150)
        layout.addWidget(self.preview_table)

        layout.addStretch()

        # Auto-load filament ref if in data/ directory
        default_ref = Path("data/VF_Calculator_Up-down.xlsx")
        if default_ref.exists():
            self._load_filament_ref(str(default_ref))

    def _make_combo(self, label: str, parent_layout: QHBoxLayout) -> QComboBox:
        parent_layout.addWidget(QLabel(label))
        combo = QComboBox()
        combo.setMinimumWidth(130)
        parent_layout.addWidget(combo)
        return combo

    def _browse_filament_ref(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Filament Reference File", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if path:
            self._load_filament_ref(path)

    def _load_filament_ref(self, path: str) -> None:
        try:
            info, stats = load_filament_reference(path)
            self.state._filament_info = info
            self.state._series_stats = stats
            self.state.filament_ref_path = path
            self.filament_path_edit.setText(path)
            n_filaments = len(info)
            n_series = len(stats)
            self.filament_status.setText(f"Loaded ({n_filaments} filaments, {n_series} series patterns)")
            self.filament_status.setStyleSheet("color: green;")
            self._check_ready()
        except Exception as e:
            self.filament_status.setText(f"Error: {e}")
            self.filament_status.setStyleSheet("color: red;")

    def _browse_data_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Von Frey Data File", "",
            "Excel/CSV Files (*.xlsx *.xls *.csv);;All Files (*)"
        )
        if path:
            self._load_data_file(path)

    def _load_data_file(self, path: str) -> None:
        try:
            df = load_excel_or_csv(path)
            self.state._data_df = df
            self.state.data_file_path = path
            self.data_path_edit.setText(path)
            self.data_status.setText(f"Loaded ({len(df)} rows, {len(df.columns)} columns)")
            self.data_status.setStyleSheet("color: green;")

            # Auto-populate column mapping dropdowns
            candidates = detect_column_candidates(df)
            cols = list(df.columns)

            for combo, field_name in [
                (self.mouse_combo, "mouse"),
                (self.timepoint_combo, "timepoint"),
                (self.series_combo, "xo_series"),
                (self.filament_combo, "last_filament"),
            ]:
                combo.clear()
                combo.addItems(cols)
                # Pre-select best candidate
                if candidates.get(field_name):
                    best = candidates[field_name][0]
                    idx = cols.index(best)
                    combo.setCurrentIndex(idx)

            self._check_ready()
        except Exception as e:
            self.data_status.setText(f"Error: {e}")
            self.data_status.setStyleSheet("color: red;")

    def _browse_metadata_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Metadata File", "",
            "Excel/CSV Files (*.xlsx *.xls *.csv);;All Files (*)"
        )
        if path:
            self._load_metadata_file(path)

    def _load_metadata_file(self, path: str) -> None:
        try:
            df = load_excel_or_csv(path)
            self.state._metadata_df = df
            self.state.metadata_file_path = path
            self.meta_path_edit.setText(path)

            n_mice = df[df.columns[0]].nunique() if len(df.columns) > 0 else len(df)
            self.meta_status.setText(f"Loaded ({n_mice} mice)")
            self.meta_status.setStyleSheet("color: green;")

            # Populate gender and mouse ID column dropdowns
            candidates = detect_column_candidates(df)
            cols = list(df.columns)
            self.gender_combo.clear()
            self.gender_combo.addItems(cols)
            if candidates.get("gender"):
                idx = cols.index(candidates["gender"][0])
                self.gender_combo.setCurrentIndex(idx)

            self.meta_mouse_combo.clear()
            self.meta_mouse_combo.addItems(cols)
            if candidates.get("mouse"):
                idx = cols.index(candidates["mouse"][0])
                self.meta_mouse_combo.setCurrentIndex(idx)

            self._check_ready()
        except Exception as e:
            self.meta_status.setText(f"Error: {e}")
            self.meta_status.setStyleSheet("color: red;")

    def _check_ready(self) -> None:
        ready = (
            self.state._filament_info is not None
            and self.state._data_df is not None
            and self.state._metadata_df is not None
        )
        self.compute_btn.setEnabled(ready)

    def _compute_thresholds(self) -> None:
        # Save column mappings to state
        self.state.mouse_col = self.mouse_combo.currentText()
        self.state.timepoint_col = self.timepoint_combo.currentText()
        self.state.series_col = self.series_combo.currentText()
        self.state.filament_col = self.filament_combo.currentText()
        self.state.gender_col = self.gender_combo.currentText()
        self.state.meta_mouse_col = self.meta_mouse_combo.currentText()
        self.state.log_column = "Log_new" if self.log_new_radio.isChecked() else "Log"

        # Validate
        errors = validate_data_columns(
            self.state._data_df,
            self.state.mouse_col,
            self.state.timepoint_col,
            self.state.series_col,
            self.state.filament_col,
        )
        if errors:
            QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
            return

        meta_errors = validate_metadata_columns(
            self.state._metadata_df,
            self.state.mouse_col,
            self.state.gender_col,
            meta_mouse_col=self.state.meta_mouse_col,
        )
        if meta_errors:
            QMessageBox.warning(self, "Metadata Warnings", "\n".join(meta_errors))

        # Check mouse ID match
        match_warnings = check_mouse_id_match(
            self.state._data_df, self.state._metadata_df, self.state.mouse_col,
            meta_mouse_col=self.state.meta_mouse_col,
        )
        if match_warnings:
            QMessageBox.information(self, "Mouse ID Mismatch", "\n".join(match_warnings))

        # Run threshold computation in worker thread
        self.compute_btn.setEnabled(False)
        self.compute_btn.setText("Computing...")

        self._worker = ThresholdWorker(
            self.state._data_df.copy(),
            self.state._filament_info,
            self.state._series_stats,
            self.state.series_col,
            self.state.filament_col,
            self.state.log_column,
        )
        self._worker.finished.connect(self._on_threshold_done)
        self._worker.error.connect(self._on_threshold_error)
        self._worker.start()

    def _on_threshold_done(self, df: object) -> None:
        self.state._data_df = df

        # Merge metadata
        self.state._merged_df = merge_metadata(
            df,
            self.state._metadata_df,
            mouse_col=self.state.mouse_col,
            gender_col=self.state.gender_col,
            meta_mouse_col=self.state.meta_mouse_col,
        )

        # Update preview table
        preview_cols = [self.state.mouse_col, self.state.timepoint_col,
                        self.state.series_col, "threshold_50"]
        preview_df = self.state._merged_df[
            [c for c in preview_cols if c in self.state._merged_df.columns]
        ].head(20)

        self.preview_table.setRowCount(len(preview_df))
        self.preview_table.setColumnCount(len(preview_df.columns))
        self.preview_table.setHorizontalHeaderLabels(list(preview_df.columns))

        for r in range(len(preview_df)):
            for c in range(len(preview_df.columns)):
                val = preview_df.iloc[r, c]
                if isinstance(val, float):
                    text = f"{val:.4f}"
                else:
                    text = str(val)
                self.preview_table.setItem(r, c, QTableWidgetItem(text))

        self.preview_table.resizeColumnsToContents()

        n_nan = self.state._merged_df["threshold_50"].isna().sum()
        status = f"Thresholds computed for {len(self.state._merged_df)} rows"
        if n_nan > 0:
            status += f" ({n_nan} NaN values)"
        self.data_status.setText(status)

        self.compute_btn.setText("Compute Thresholds")
        self.compute_btn.setEnabled(True)

        self.data_ready.emit()

    def _on_threshold_error(self, error_msg: str) -> None:
        self.compute_btn.setText("Compute Thresholds")
        self.compute_btn.setEnabled(True)
        QMessageBox.critical(self, "Computation Error", error_msg)
