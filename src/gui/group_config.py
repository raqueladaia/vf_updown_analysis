"""Step 2: Groups, panel factors, and timepoint configuration."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ..core.data_loader import (
    detect_facet_factor_candidates,
    detect_timepoint_type,
    get_comparison_group_candidates,
    get_group_combinations,
    validate_facet_selection,
    validate_facet_slices,
)
from .state import AnalysisState


class GroupConfigPanel(QWidget):
    """Step 2: Group assignment, panel factors, and timepoint configuration."""

    config_ready = pyqtSignal()

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._group_checkboxes: list[tuple[QCheckBox, str]] = []
        self._tp_checkboxes: list[tuple[QCheckBox, str]] = []
        self._facet_widgets: dict[str, tuple[QCheckBox, QCheckBox, list[tuple[QCheckBox, str]], QWidget]] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Panel factors (pre-post only) ────────────────────────────────
        self.facet_box = QGroupBox("Separate figures by (panel factors)")
        self.facet_layout = QVBoxLayout(self.facet_box)
        self.facet_info_label = QLabel(
            "Load data first. Shown when ≤2 active timepoints.\n"
            "Choose columns to split into separate figures. Check All for every "
            "level, or pick specific values. Multiple panel factors create all "
            "combinations (e.g. light+dark × acute+chronic = 4 figures)."
        )
        self.facet_layout.addWidget(self.facet_info_label)
        self.facet_status_label = QLabel("")
        self.facet_layout.addWidget(self.facet_status_label)
        layout.addWidget(self.facet_box)

        # ── Compare within each figure ───────────────────────────────────
        self.group_box = QGroupBox("Compare within each figure (metadata and/or data file)")
        self.group_layout = QVBoxLayout(self.group_box)
        self.group_info_label = QLabel("Load data first to see available columns.")
        self.group_layout.addWidget(self.group_info_label)
        layout.addWidget(self.group_box)

        self.conditions_label = QLabel("")
        layout.addWidget(self.conditions_label)

        # ── Timepoints ───────────────────────────────────────────────────
        self.tp_group = QGroupBox("Timepoints")
        tp_layout = QVBoxLayout(self.tp_group)

        self.tp_detected_label = QLabel("Detected timepoints: (none)")
        tp_layout.addWidget(self.tp_detected_label)

        tp_type_row = QHBoxLayout()
        tp_type_row.addWidget(QLabel("Timepoint type:"))
        self.tp_numeric_radio = QRadioButton("Numeric")
        self.tp_categorical_radio = QRadioButton("Categorical")
        self.tp_numeric_radio.setChecked(True)
        tp_type_row.addWidget(self.tp_numeric_radio)
        tp_type_row.addWidget(self.tp_categorical_radio)
        tp_type_row.addStretch()
        tp_layout.addLayout(tp_type_row)

        tp_layout.addWidget(QLabel("Exclude timepoints:"))
        self.tp_exclude_layout = QHBoxLayout()
        tp_layout.addLayout(self.tp_exclude_layout)

        tp_layout.addWidget(QLabel("Reorder (drag to reorder):"))
        self.tp_order_list = QListWidget()
        self.tp_order_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.tp_order_list.setMaximumHeight(150)
        tp_layout.addWidget(self.tp_order_list)

        self.intervention_row = QWidget()
        intervention_row = QHBoxLayout(self.intervention_row)
        intervention_row.setContentsMargins(0, 0, 0, 0)
        intervention_row.addWidget(QLabel("Intervention marker at x ="))
        self.intervention_edit = QLineEdit()
        self.intervention_edit.setPlaceholderText("e.g. 0  (leave blank for none)")
        self.intervention_edit.setMaximumWidth(160)
        intervention_row.addWidget(self.intervention_edit)
        intervention_row.addStretch()
        tp_layout.addWidget(self.intervention_row)

        layout.addWidget(self.tp_group)
        layout.addStretch()

    def refresh(self) -> None:
        """Refresh panel contents based on current state data."""
        if self.state._merged_df is None:
            return

        merged_df = self.state._merged_df
        data_df = self.state._data_df if self.state._data_df is not None else merged_df

        self._rebuild_facet_ui(data_df)
        self._rebuild_group_checkboxes(data_df)
        self._rebuild_timepoints(merged_df)
        self._update_design_mode_ui()
        self._update_facet_status()
        self._update_conditions()

    def _rebuild_facet_ui(self, data_df) -> None:
        """Rebuild panel-factor checkboxes from data columns."""
        for _col, (col_cb, all_cb, value_cbs, value_container) in list(
            self._facet_widgets.items()
        ):
            col_cb.blockSignals(True)
            all_cb.blockSignals(True)
            for vcb, _ in value_cbs:
                vcb.blockSignals(True)
            self.facet_layout.removeWidget(col_cb)
            self.facet_layout.removeWidget(value_container)
            col_cb.deleteLater()
            value_container.deleteLater()
        self._facet_widgets.clear()

        candidates = detect_facet_factor_candidates(
            data_df,
            mouse_col=self.state.mouse_col,
            timepoint_col=self.state.timepoint_col,
            series_col=self.state.series_col,
            filament_col=self.state.filament_col,
        )

        if not candidates:
            self.facet_info_label.setText(
                "No panel-factor columns detected (one row per mouse per timepoint)."
            )
            return

        self.facet_info_label.setText(
            "Select columns to split figures. Check All for every level, or pick values:"
        )

        for col in candidates:
            unique_vals = sorted(data_df[col].dropna().unique(), key=str)
            col_cb = QCheckBox(col)
            col_cb.setProperty("col_name", col)

            value_cbs: list[tuple[QCheckBox, str]] = []
            value_row = QHBoxLayout()
            value_row.addSpacing(20)

            all_cb = QCheckBox("All")
            value_row.addWidget(all_cb)

            saved = self.state.facet_values.get(col)
            use_all = col not in self.state.facet_cols or saved is None or saved == []

            for val in unique_vals:
                val_str = str(val)
                vcb = QCheckBox(val_str)
                vcb.setEnabled(not use_all)
                value_row.addWidget(vcb)
                value_cbs.append((vcb, val_str))

            value_container = QWidget()
            value_container.setLayout(value_row)
            self._facet_widgets[col] = (col_cb, all_cb, value_cbs, value_container)

            col_cb.blockSignals(True)
            all_cb.blockSignals(True)
            for vcb, val_str in value_cbs:
                vcb.blockSignals(True)
                if not use_all and val_str in (saved or []):
                    vcb.setChecked(True)
            all_cb.setChecked(use_all)
            if col in self.state.facet_cols:
                col_cb.setChecked(True)
            for vcb, _val_str in value_cbs:
                vcb.blockSignals(False)
            all_cb.blockSignals(False)
            col_cb.blockSignals(False)

            col_cb.stateChanged.connect(self._on_facet_changed)
            all_cb.stateChanged.connect(
                lambda _state, c=col: self._on_facet_all_changed(c)
            )
            for vcb, _val_str in value_cbs:
                vcb.stateChanged.connect(
                    lambda _state, c=col: self._on_facet_value_changed(c)
                )

            self.facet_layout.addWidget(col_cb)
            self.facet_layout.addWidget(value_container)

    def _rebuild_group_checkboxes(self, data_df) -> None:
        for cb, _ in self._group_checkboxes:
            self.group_layout.removeWidget(cb)
            cb.deleteLater()
        self._group_checkboxes.clear()
        self.group_info_label.hide()

        facet_cols = self._collect_facet_cols()
        candidates = get_comparison_group_candidates(
            self.state._metadata_df,
            data_df,
            mouse_col=self.state.mouse_col,
            sex_col=self.state.sex_col,
            meta_mouse_col=self.state.meta_mouse_col,
            timepoint_col=self.state.timepoint_col,
            series_col=self.state.series_col,
            filament_col=self.state.filament_col,
            facet_cols=facet_cols,
        )

        for col in candidates:
            source_df = (
                self.state._metadata_df
                if self.state._metadata_df is not None and col in self.state._metadata_df.columns
                else data_df
            )
            unique_vals = source_df[col].dropna().unique()
            label = f"{col}    (values: {', '.join(str(v) for v in unique_vals[:6])})"
            cb = QCheckBox(label)
            cb.setProperty("col_name", col)
            if col in self.state.group_cols:
                cb.setChecked(True)
            cb.stateChanged.connect(self._update_conditions)
            self.group_layout.addWidget(cb)
            self._group_checkboxes.append((cb, col))

    def _rebuild_timepoints(self, merged_df) -> None:
        timepoints = merged_df[self.state.timepoint_col].unique()

        tp_type = detect_timepoint_type(merged_df[self.state.timepoint_col])
        if tp_type == "numeric":
            self.tp_numeric_radio.setChecked(True)
            timepoints = sorted(timepoints, key=lambda x: float(x))
        else:
            self.tp_categorical_radio.setChecked(True)

        self.state.timepoint_type = tp_type
        tp_strs = [str(tp) for tp in timepoints]
        self.tp_detected_label.setText(f"Detected timepoints: {tp_strs}")

        for cb, _ in self._tp_checkboxes:
            self.tp_exclude_layout.removeWidget(cb)
            cb.deleteLater()
        self._tp_checkboxes.clear()

        for tp in tp_strs:
            cb = QCheckBox(tp)
            if tp in self.state.excluded_timepoints:
                cb.setChecked(True)
            cb.stateChanged.connect(self._on_timepoint_changed)
            self.tp_exclude_layout.addWidget(cb)
            self._tp_checkboxes.append((cb, tp))

        self.tp_order_list.clear()
        order = self.state.timepoint_order or tp_strs
        for tp in order:
            if tp in tp_strs:
                item = QListWidgetItem(tp)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                self.tp_order_list.addItem(item)
        for tp in tp_strs:
            if tp not in order:
                item = QListWidgetItem(tp)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                self.tp_order_list.addItem(item)

        if not self.state.timepoint_order:
            self.state.timepoint_order = tp_strs

    def _collect_facet_cols(self) -> list[str]:
        cols: list[str] = []
        for col, (col_cb, _all_cb, _value_cbs, _container) in self._facet_widgets.items():
            if col_cb.isChecked():
                cols.append(col)
        return cols

    def _sync_facet_to_state(self) -> None:
        cols: list[str] = []
        values: dict[str, list[str]] = {}
        for col, (col_cb, all_cb, value_cbs, _container) in self._facet_widgets.items():
            if col_cb.isChecked():
                cols.append(col)
                if all_cb.isChecked():
                    values[col] = []
                else:
                    selected = [v for vcb, v in value_cbs if vcb.isChecked()]
                    values[col] = selected
        self.state.facet_cols = cols
        self.state.facet_values = values
        self.state.invalidate_facet_slices()

    def _on_facet_all_changed(self, col: str) -> None:
        if col not in self._facet_widgets:
            return
        _col_cb, all_cb, value_cbs, _container = self._facet_widgets[col]
        use_all = all_cb.isChecked()
        for vcb, _val in value_cbs:
            vcb.blockSignals(True)
            vcb.setEnabled(not use_all)
            if use_all:
                vcb.setChecked(False)
            vcb.blockSignals(False)
        self._on_facet_changed()

    def _on_facet_value_changed(self, col: str) -> None:
        if col not in self._facet_widgets:
            return
        _col_cb, all_cb, value_cbs, _container = self._facet_widgets[col]
        any_checked = any(vcb.isChecked() for vcb, _ in value_cbs)
        if any_checked and all_cb.isChecked():
            all_cb.blockSignals(True)
            all_cb.setChecked(False)
            all_cb.blockSignals(False)
            for vcb, _ in value_cbs:
                vcb.setEnabled(True)
        self._on_facet_changed()

    def _on_facet_changed(self) -> None:
        self._sync_facet_to_state()
        self._rebuild_group_checkboxes(
            self.state._data_df if self.state._data_df is not None else self.state._merged_df
        )
        self._update_facet_status()
        self._update_conditions()

    def _on_timepoint_changed(self) -> None:
        self.state.excluded_timepoints = [tp for cb, tp in self._tp_checkboxes if cb.isChecked()]
        self.state.invalidate_facet_slices()
        self._update_design_mode_ui()
        self._update_facet_status()
        self._update_conditions()
        if len(self.active_timepoints()) == 2:
            self.state.auto_assign_pre_post_labels()

    def active_timepoints(self) -> list[str]:
        order = []
        for i in range(self.tp_order_list.count()):
            order.append(self.tp_order_list.item(i).text())
        if not order:
            order = self.state.timepoint_order
        excluded = set(tp for cb, tp in self._tp_checkboxes if cb.isChecked())
        return [tp for tp in order if tp not in excluded]

    def _update_design_mode_ui(self) -> None:
        pre_post = len(self.active_timepoints()) <= 2
        self.facet_box.setVisible(pre_post)
        self.intervention_row.setVisible(not pre_post)

    def _update_facet_status(self) -> None:
        if len(self.active_timepoints()) > 2:
            self.facet_status_label.setText("")
            return

        self.state.compute_facet_slices()
        slices = self.state.get_facet_slices()

        if not slices:
            self.facet_status_label.setText("No data after filters.")
            self.facet_status_label.setStyleSheet("color: red;")
            return

        n_panels = len(slices)
        panel_note = f"{n_panels} figure{'s' if n_panels != 1 else ''}"
        if n_panels > 1:
            labels = [sl.label for sl in slices[:4]]
            if n_panels > 4:
                panel_note += f": {', '.join(labels)}, …"
            else:
                panel_note += f": {', '.join(labels)}"

        df = self.state.get_analysis_df()
        if df is None or df.empty:
            self.facet_status_label.setText(f"{panel_note} — no data in active panel.")
            self.facet_status_label.setStyleSheet("color: #b8860b;")
            return

        factor_candidates = self.state.get_factor_candidates()
        self.state.refresh_pairing_columns()

        errors, _warnings = validate_facet_slices(
            slices,
            self.state.mouse_col,
            self.state.timepoint_col,
            self.active_timepoints(),
            self.state.pre_label,
            self.state.post_label,
            self.state.group_cols,
            self.state.facet_cols,
            factor_candidates,
        )

        if errors:
            self.facet_status_label.setText(f"⚠ {errors[0]}")
            self.facet_status_label.setStyleSheet("color: #b8860b;")
        else:
            n_mice = df[self.state.mouse_col].nunique()
            pair_note = ""
            if self.state.pairing_cols:
                pair_note = f" | paired by {', '.join(self.state.pairing_cols)}"
            self.facet_status_label.setText(
                f"✓ {panel_note} | {n_mice} mice per panel{pair_note}"
            )
            self.facet_status_label.setStyleSheet("color: green;")

    def _update_conditions(self) -> None:
        selected_cols = [col for cb, col in self._group_checkboxes if cb.isChecked()]
        self.state.group_cols = selected_cols
        self.state.invalidate_facet_slices()

        if not selected_cols:
            self.conditions_label.setText("")
            return

        df = self.state.get_analysis_df()
        if df is None:
            self.conditions_label.setText("")
            return

        try:
            per_mouse = get_group_combinations(df, selected_cols, mouse_col=self.state.mouse_col)
            lines = [f"Per figure, this creates {len(per_mouse)} conditions:"]
            for i, row in per_mouse.iterrows():
                parts = [f"{col}={row[col]}" for col in selected_cols]
                lines.append(f"  {i+1}. {' x '.join(parts)} (n={row['n']})")
                if row["n"] < 3:
                    lines[-1] += " ⚠️ WARNING: n < 3"
            self.conditions_label.setText("\n".join(lines))
        except Exception as e:
            self.conditions_label.setText(f"Error computing conditions: {e}")

    def get_config(self) -> bool:
        """Collect configuration from UI into state. Returns False if invalid."""
        self.state.group_cols = [col for cb, col in self._group_checkboxes if cb.isChecked()]
        self.state.excluded_timepoints = [tp for cb, tp in self._tp_checkboxes if cb.isChecked()]
        self.state.timepoint_type = "numeric" if self.tp_numeric_radio.isChecked() else "categorical"

        order = []
        for i in range(self.tp_order_list.count()):
            order.append(self.tp_order_list.item(i).text())
        self.state.timepoint_order = order

        self._sync_facet_to_state()

        if len(self.state.active_timepoints()) <= 2:
            self.state.intervention_timepoint = None
            self.state.auto_assign_pre_post_labels()

            facet_errors = validate_facet_selection(
                self.state.facet_cols,
                self.state.facet_values,
                self.state.group_cols,
            )
            if facet_errors:
                QMessageBox.warning(
                    self,
                    "Panel factor configuration",
                    "\n".join(facet_errors),
                )
                return False

            for col in self.state.facet_cols:
                selected = self.state.facet_values.get(col)
                if selected is not None and len(selected) == 0:
                    continue
                if not selected:
                    QMessageBox.warning(
                        self,
                        "Panel factor configuration",
                        f"Panel factor '{col}' is enabled but no values are selected. "
                        f"Check All or select specific values.",
                    )
                    return False

            slices = self.state.compute_facet_slices()
            if not slices:
                QMessageBox.warning(
                    self,
                    "Invalid configuration",
                    "No data remains after timepoint filters.",
                )
                return False

            factor_candidates = self.state.get_factor_candidates()
            errors, warnings = validate_facet_slices(
                slices,
                self.state.mouse_col,
                self.state.timepoint_col,
                self.state.active_timepoints(),
                self.state.pre_label,
                self.state.post_label,
                self.state.group_cols,
                self.state.facet_cols,
                factor_candidates,
            )
            for w in warnings:
                self.statusBar_message(w)

            if errors:
                QMessageBox.warning(
                    self,
                    "Pre-post validation failed",
                    "\n".join(errors),
                )
                return False
        else:
            intervention_text = self.intervention_edit.text().strip()
            if intervention_text:
                try:
                    float(intervention_text)
                    self.state.intervention_timepoint = intervention_text
                except ValueError:
                    self.state.intervention_timepoint = None
            else:
                self.state.intervention_timepoint = None

        self.config_ready.emit()
        return True

    def statusBar_message(self, message: str) -> None:
        """Show non-blocking warning via parent window status bar if available."""
        window = self.window()
        if window is not None and hasattr(window, "statusBar"):
            window.statusBar().showMessage(message)
