"""Step 2: Metadata & Groups configuration panel.

Allows users to select group-defining columns, configure timepoints,
exclude timepoints, reorder categorical timepoints, and set the
intervention marker position.
"""

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

from ..core.data_loader import detect_timepoint_type, get_group_combinations
from .state import AnalysisState


class GroupConfigPanel(QWidget):
    """Step 2: Group assignment and timepoint configuration."""

    config_ready = pyqtSignal()

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._group_checkboxes: list[tuple[QCheckBox, str]] = []
        self._tp_checkboxes: list[tuple[QCheckBox, str]] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Group columns ────────────────────────────────────────────────
        self.group_box = QGroupBox("Group-defining columns from metadata")
        self.group_layout = QVBoxLayout(self.group_box)
        self.group_info_label = QLabel("Load data first to see available columns.")
        self.group_layout.addWidget(self.group_info_label)
        layout.addWidget(self.group_box)

        # Conditions summary
        self.conditions_label = QLabel("")
        layout.addWidget(self.conditions_label)

        # ── Timepoints ───────────────────────────────────────────────────
        tp_group = QGroupBox("Timepoints")
        tp_layout = QVBoxLayout(tp_group)

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

        # Intervention marker — free numeric input (not restricted to existing timepoints)
        intervention_row = QHBoxLayout()
        intervention_row.addWidget(QLabel("Intervention marker at x ="))
        self.intervention_edit = QLineEdit()
        self.intervention_edit.setPlaceholderText("e.g. 0  (leave blank for none)")
        self.intervention_edit.setMaximumWidth(160)
        intervention_row.addWidget(self.intervention_edit)
        intervention_row.addStretch()
        tp_layout.addLayout(intervention_row)

        layout.addWidget(tp_group)
        layout.addStretch()

    def refresh(self) -> None:
        """Refresh panel contents based on current state data."""
        if self.state._metadata_df is None or self.state._merged_df is None:
            return

        meta_df = self.state._metadata_df
        merged_df = self.state._merged_df

        # ── Populate group column checkboxes ─────────────────────────────
        # Clear existing checkboxes
        for cb, _ in self._group_checkboxes:
            self.group_layout.removeWidget(cb)
            cb.deleteLater()
        self._group_checkboxes.clear()
        self.group_info_label.hide()

        # Identify potential group columns (exclude mouse, gender, data columns)
        exclude_cols = {
            self.state.mouse_col, self.state.gender_col,
            self.state.meta_mouse_col,
            self.state.timepoint_col, self.state.series_col,
            self.state.filament_col, "threshold_50",
        }
        potential_group_cols = [c for c in meta_df.columns if c not in exclude_cols]

        for col in potential_group_cols:
            unique_vals = meta_df[col].dropna().unique()
            label = f"{col}    (values: {', '.join(str(v) for v in unique_vals[:6])})"
            cb = QCheckBox(label)
            cb.setProperty("col_name", col)
            cb.stateChanged.connect(self._update_conditions)
            self.group_layout.addWidget(cb)
            self._group_checkboxes.append((cb, col))

        # ── Populate timepoints ──────────────────────────────────────────
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

        # Clear and rebuild exclude checkboxes
        for cb, _ in self._tp_checkboxes:
            self.tp_exclude_layout.removeWidget(cb)
            cb.deleteLater()
        self._tp_checkboxes.clear()

        for tp in tp_strs:
            cb = QCheckBox(tp)
            cb.stateChanged.connect(self._update_timepoint_order)
            self.tp_exclude_layout.addWidget(cb)
            self._tp_checkboxes.append((cb, tp))

        # Populate order list
        self.tp_order_list.clear()
        for tp in tp_strs:
            item = QListWidgetItem(tp)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
            self.tp_order_list.addItem(item)

        self.state.timepoint_order = tp_strs

    def _update_conditions(self) -> None:
        """Update conditions summary when group checkboxes change."""
        selected_cols = [col for cb, col in self._group_checkboxes if cb.isChecked()]
        self.state.group_cols = selected_cols

        if not selected_cols or self.state._metadata_df is None:
            self.conditions_label.setText("")
            return

        try:
            combos = get_group_combinations(
                self.state._metadata_df, selected_cols, self.state.mouse_col
            )
            lines = [f"This creates {len(combos)} conditions:"]
            for i, row in combos.iterrows():
                parts = [f"{col}={row[col]}" for col in selected_cols]
                lines.append(f"  {i+1}. {' x '.join(parts)} (n={row['n']})")
                if row["n"] < 3:
                    lines[-1] += " ⚠️ WARNING: n < 3"
            self.conditions_label.setText("\n".join(lines))
        except Exception as e:
            self.conditions_label.setText(f"Error computing conditions: {e}")

    def _update_timepoint_order(self) -> None:
        """Update timepoint order and exclusions."""
        excluded = [tp for cb, tp in self._tp_checkboxes if cb.isChecked()]
        self.state.excluded_timepoints = excluded

    def get_config(self) -> None:
        """Collect configuration from UI into state."""
        self.state.group_cols = [col for cb, col in self._group_checkboxes if cb.isChecked()]
        self.state.excluded_timepoints = [tp for cb, tp in self._tp_checkboxes if cb.isChecked()]
        self.state.timepoint_type = "numeric" if self.tp_numeric_radio.isChecked() else "categorical"

        # Get timepoint order from list widget
        order = []
        for i in range(self.tp_order_list.count()):
            order.append(self.tp_order_list.item(i).text())
        self.state.timepoint_order = order

        # Intervention — accept any numeric value; blank means no line
        intervention_text = self.intervention_edit.text().strip()
        if intervention_text:
            try:
                float(intervention_text)  # validate it's a number
                self.state.intervention_timepoint = intervention_text
            except ValueError:
                self.state.intervention_timepoint = None
        else:
            self.state.intervention_timepoint = None

        self.config_ready.emit()
