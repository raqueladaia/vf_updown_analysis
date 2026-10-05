"""Step 1: Data Loading panel for the GUI.

Handles loading filament reference, von Frey data, and metadata files.
Provides column mapping dropdowns and threshold computation.
"""

from __future__ import annotations

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
    get_mice_not_accepted,
    load_excel_or_csv,
    merge_metadata,
    validate_data_columns,
    validate_metadata_columns,
)
from ..core.vf_threshold import (
    compute_threshold_report, get_delta, load_filament_reference, spacing_warning, boundary_summary,
)
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
        boundary_policy: str = "flag",
    ):
        super().__init__()
        self.df = df
        self.filament_info = filament_info
        self.series_stats = series_stats
        self.series_col = series_col
        self.filament_col = filament_col
        self.log_column = log_column
        self.boundary_policy = boundary_policy

    def run(self) -> None:
        try:
            self.df = compute_threshold_report(
                self.df,
                self.filament_info,
                self.series_stats,
                series_col=self.series_col,
                filament_col=self.filament_col,
                log_column=self.log_column,
                boundary_policy=self.boundary_policy,
            )
            self.finished.emit(self.df)
        except Exception as e:
            self.error.emit(str(e))


class DataInputPanel(QWidget):
    """Step 1: Data loading and column mapping panel."""

    data_ready = pyqtSignal()  # emitted when thresholds are computed
    data_invalidated = pyqtSignal()

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._worker: ThresholdWorker | None = None
        self._revision = 0
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Filament reference file ──────────────────────────────────────
        filament_group = QGroupBox("Species and filament calculation")
        fg_layout = QVBoxLayout(filament_group)

        set_row = QHBoxLayout()
        set_row.addWidget(QLabel("Filament set:"))
        self.filament_set_combo = QComboBox()
        self.filament_set_combo.addItem("Legacy mouse (unchanged)", "legacy")
        self.filament_set_combo.addItem("Rat — calculated from target forces (0.4–15 g)", "rat")
        self.filament_set_combo.addItem("Custom calibrated ladder (CSV)", "custom")
        set_row.addWidget(self.filament_set_combo)
        fg_layout.addLayout(set_row)

        custom_row = QHBoxLayout()
        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setReadOnly(True)
        self.custom_path_edit.setPlaceholderText("CSV: Filament_number, Force (g), optional Log")
        self.custom_browse_btn = QPushButton("Browse ladder...")
        self.custom_browse_btn.clicked.connect(self._browse_custom_filaments)
        custom_row.addWidget(self.custom_path_edit)
        custom_row.addWidget(self.custom_browse_btn)
        fg_layout.addLayout(custom_row)
        self.ladder_note = QLabel(
            "Use the complete ladder used in the experiment; IDs must match last_filament. "
            "Rat/custom sets use a mean-spacing Dixon approximation. See docs/filament_sets.md."
        )
        self.ladder_note.setWordWrap(True)
        fg_layout.addWidget(self.ladder_note)
        self.spacing_note = QLabel("")
        self.spacing_note.setWordWrap(True)
        self.spacing_note.setStyleSheet("color: #9a5300;")
        fg_layout.addWidget(self.spacing_note)

        row = QHBoxLayout()
        self.filament_path_edit = QLineEdit()
        self.filament_path_edit.setReadOnly(True)
        self.filament_path_edit.setPlaceholderText("Select VF_Calculator_Up-down.xlsx")
        self.reference_browse_btn = QPushButton("Browse mouse master...")
        self.reference_browse_btn.clicked.connect(self._browse_filament_ref)
        row.addWidget(self.filament_path_edit, stretch=1)
        row.addWidget(self.reference_browse_btn)
        fg_layout.addLayout(row)

        self.filament_status = QLabel("")
        fg_layout.addWidget(self.filament_status)

        # Log column selection
        log_row = QHBoxLayout()
        log_row.addWidget(QLabel("Log column:"))
        self.log_new_radio = QRadioButton("Log_new (computed)")
        self.log_old_radio = QRadioButton("Log (master/reference values)")
        self.log_new_radio.setChecked(True)
        self.log_new_radio.setToolTip("Use log values computed from force: log10(10 * force_g * 1000)")
        self.log_old_radio.setToolTip("Use reference Log values from the workbook or selected ladder")
        log_row.addWidget(self.log_new_radio)
        log_row.addWidget(self.log_old_radio)
        log_row.addStretch()
        fg_layout.addLayout(log_row)
        boundary_row = QHBoxLayout()
        boundary_row.addWidget(QLabel("Boundary observations:"))
        self.boundary_combo = QComboBox()
        self.boundary_combo.addItem("Flag for review before statistics (default)", "flag")
        self.boundary_combo.addItem("Use tested endpoints as numerical substitutes", "endpoints")
        self.boundary_combo.addItem("Explicitly exclude from numerical analysis", "exclude")
        self.boundary_combo.setToolTip(
            "All X at the lowest force or all O at the highest force are censored observations, "
            "not exact thresholds. Choose your predefined protocol; see docs/boundary_handling.md."
        )
        boundary_row.addWidget(self.boundary_combo)
        fg_layout.addLayout(boundary_row)

        layout.addWidget(filament_group)

        # ── Data file ────────────────────────────────────────────────────
        data_group = QGroupBox("Von Frey Data File")
        dg_layout = QVBoxLayout(data_group)
        example_note = QLabel(
            "Bundled Excel measurements and metadata are MOUSE examples. "
            "Use Mouse with those files; import your own measurements for rats."
        )
        example_note.setWordWrap(True)
        dg_layout.addWidget(example_note)

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
        self.mouse_combo = self._make_combo("Animal ID column:", mapping_layout)
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

        sex_row = QHBoxLayout()
        sex_row.addWidget(QLabel("Sex column:"))
        self.sex_combo = QComboBox()
        self.sex_combo.setMinimumWidth(150)
        sex_row.addWidget(self.sex_combo)
        sex_row.addWidget(QLabel("Animal ID column:"))
        self.meta_mouse_combo = QComboBox()
        self.meta_mouse_combo.setMinimumWidth(150)
        sex_row.addWidget(self.meta_mouse_combo)
        sex_row.addStretch()
        mg_layout.addLayout(sex_row)

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

        self.filament_set_combo.currentIndexChanged.connect(self._filament_set_changed)
        self.log_new_radio.toggled.connect(self._log_changed)
        self.boundary_combo.currentIndexChanged.connect(self._boundary_changed)
        self.restore_filament_settings()

    def restore_filament_settings(self) -> None:
        """Restore profile controls and reference after loading a session."""
        self.filament_set_combo.blockSignals(True)
        self.filament_set_combo.setCurrentIndex(
            self.filament_set_combo.findData(self.state.filament_set)
        )
        self.filament_set_combo.blockSignals(False)
        self.custom_path_edit.setText(self.state.custom_filaments_path)
        self.boundary_combo.blockSignals(True)
        self.boundary_combo.setCurrentIndex(self.boundary_combo.findData(self.state.boundary_policy))
        self.boundary_combo.blockSignals(False)
        self.log_new_radio.blockSignals(True)
        self.log_new_radio.setChecked(self.state.log_column == "Log_new")
        self.log_old_radio.setChecked(self.state.log_column == "Log")
        self.log_new_radio.blockSignals(False)
        self._filament_set_changed()

    def _filament_set_changed(self) -> None:
        previous = self.state.filament_set
        self.state.filament_set = self.filament_set_combo.currentData()
        if previous != self.state.filament_set:
            self.state.y_max = 10.0 if self.state.filament_set == "legacy" else 20.0
        rat = self.state.filament_set == "rat"
        self.log_old_radio.setEnabled(not rat)
        if rat:
            self.log_new_radio.setChecked(True)
            self.state.log_column = "Log_new"
        legacy = self.state.filament_set == "legacy"
        self.filament_path_edit.setEnabled(legacy)
        self.reference_browse_btn.setEnabled(legacy)
        self.filament_path_edit.setVisible(legacy)
        self.reference_browse_btn.setVisible(legacy)
        self.ladder_note.setText(
            "Mouse: choose calculated logs or stored logs from the mouse master. "
            "Verify the known force/log discrepancies; see docs/filament_sets.md."
            if legacy else
            "No Excel master is needed. Rat logs are calculated from target forces; "
            "custom ladders use the selected convention. Use the experimental ladder and matching IDs."
        )
        custom = self.state.filament_set == "custom"
        self.custom_path_edit.setEnabled(custom)
        self.custom_browse_btn.setEnabled(custom)
        self._load_filament_ref(
            self.state.filament_ref_path or "data/VF_Calculator_Up-down.xlsx"
        )

    def _invalidate_results(self) -> None:
        self._revision += 1
        self.state.invalidate_results()
        self.preview_table.setRowCount(0)
        self.data_status.setText("Inputs changed. Recompute thresholds before plotting or analysis.")
        self.data_invalidated.emit()

    def _log_changed(self) -> None:
        self._invalidate_results()
        self._update_filament_status()

    def _boundary_changed(self) -> None:
        self.state.boundary_policy = self.boundary_combo.currentData()
        self._invalidate_results()

    def _browse_custom_filaments(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Filament Ladder", "", "CSV Files (*.csv)")
        if path:
            self.state.custom_filaments_path = path
            self.custom_path_edit.setText(path)
            self._filament_set_changed()

    def _update_filament_status(self) -> None:
        info = self.state._filament_info
        if info is not None:
            self.state.log_column = "Log_new" if self.log_new_radio.isChecked() else "Log"
            delta = get_delta(info, self.state.log_column)
            self.filament_status.setText(
                f"Loaded ({len(info)} filaments, {len(self.state._series_stats)} series patterns); "
                f"delta = {delta:.9f}"
            )
            self.spacing_note.setText(spacing_warning(info, self.state.log_column))

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
        self._invalidate_results()
        self.state.filament_ref_path = path
        self.filament_path_edit.setText(path)
        self.state._filament_info = None
        self.state._series_stats = None
        self.spacing_note.clear()
        try:
            info, stats = load_filament_reference(
                path, filament_set=self.state.filament_set,
                custom_filaments=(self.state.custom_filaments_path
                                  if self.state.filament_set == "custom" else None),
            )
            self.state._filament_info = info
            self.state._series_stats = stats
            self._update_filament_status()
            self.filament_status.setStyleSheet("color: green;")
        except Exception as e:
            self.filament_status.setText(f"Error: {e}")
            self.filament_status.setStyleSheet("color: red;")
        self._check_ready()

    def _browse_data_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Von Frey Data File", "",
            "Excel/CSV Files (*.xlsx *.xls *.csv);;All Files (*)"
        )
        if path:
            self._load_data_file(path)

    def _load_data_file(self, path: str) -> None:
        self._invalidate_results()
        self.state._data_df = None
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
        self._invalidate_results()
        self.state._metadata_df = None
        try:
            df = load_excel_or_csv(path)
            self.state._metadata_df = df
            self.state.metadata_file_path = path
            self.meta_path_edit.setText(path)

            n_mice = df[df.columns[0]].nunique() if len(df.columns) > 0 else len(df)
            self.meta_status.setText(f"Loaded ({n_mice} animals)")
            self.meta_status.setStyleSheet("color: green;")

            # Populate sex and mouse ID column dropdowns
            candidates = detect_column_candidates(df)
            cols = list(df.columns)
            self.sex_combo.clear()
            self.sex_combo.addItems(cols)
            if "sex" in cols:
                self.sex_combo.setCurrentIndex(cols.index("sex"))
            elif candidates.get("sex"):
                self.sex_combo.setCurrentIndex(cols.index(candidates["sex"][0]))

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
        )
        self.compute_btn.setEnabled(ready)

    def _compute_thresholds(self) -> None:
        # Save column mappings to state
        self.state.mouse_col = self.mouse_combo.currentText()
        self.state.timepoint_col = self.timepoint_combo.currentText()
        self.state.series_col = self.series_combo.currentText()
        self.state.filament_col = self.filament_combo.currentText()
        self.state.sex_col = self.sex_combo.currentText()
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
            self.state.sex_col,
            meta_mouse_col=self.state.meta_mouse_col,
        ) if self.state._metadata_df is not None else []
        if meta_errors:
            QMessageBox.warning(self, "Metadata Warnings", "\n".join(meta_errors))

        # Check mouse ID match
        match_warnings = check_mouse_id_match(
            self.state._data_df, self.state._metadata_df, self.state.mouse_col,
            meta_mouse_col=self.state.meta_mouse_col,
        ) if self.state._metadata_df is not None and not meta_errors else []
        if match_warnings:
            QMessageBox.information(self, "Mouse ID Mismatch", "\n".join(match_warnings))

        # Run threshold computation in worker thread
        self.compute_btn.setEnabled(False)
        self.compute_btn.setText("Computing...")
        self._invalidate_results()
        self._worker_revision = self._revision
        self.setEnabled(False)

        self._worker = ThresholdWorker(
            self.state._data_df.copy(),
            self.state._filament_info,
            self.state._series_stats,
            self.state.series_col,
            self.state.filament_col,
            self.state.log_column,
            self.state.boundary_policy,
        )
        self._worker.finished.connect(self._on_threshold_done)
        self._worker.error.connect(self._on_threshold_error)
        self._worker.start()

    def _on_threshold_done(self, df: object) -> None:
        self.setEnabled(True)
        self.compute_btn.setText("Compute Thresholds")
        self._check_ready()
        if getattr(self, "_worker_revision", self._revision) != self._revision:
            return  # A session/input changed while the worker was computing.
        self.state._data_df = df

        if self.state._metadata_df is not None:
            self.state._merged_df = merge_metadata(
                df,
                self.state._metadata_df,
                mouse_col=self.state.mouse_col,
                sex_col=self.state.sex_col,
                meta_mouse_col=self.state.meta_mouse_col,
            )
            self.state.excluded_animals = get_mice_not_accepted(
                self.state._metadata_df,
                self.state.meta_mouse_col or self.state.mouse_col,
            )
        else:
            self.state._merged_df = df
            self.state.excluded_animals = []

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
        details = boundary_summary(self.state._merged_df)
        if details:
            status += "\n" + details
        self.data_status.setWordWrap(True)
        self.data_status.setText(status)

        self.compute_btn.setText("Compute Thresholds")
        self.compute_btn.setEnabled(True)

        self.data_ready.emit()

    def _on_threshold_error(self, error_msg: str) -> None:
        self.setEnabled(True)
        self.compute_btn.setText("Compute Thresholds")
        self.compute_btn.setEnabled(True)
        QMessageBox.critical(self, "Computation Error", error_msg)
