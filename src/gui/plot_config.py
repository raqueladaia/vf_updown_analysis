"""Steps 3 & 4: Appearance configuration and plot preview panels.

Step 3: Plot type, colors, sex markers, axes configuration.
Step 4: Live Matplotlib preview with embedded canvas.
"""

from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .state import AnalysisState


class ColorButton(QPushButton):
    """A button that shows a color swatch and opens a color picker."""

    color_changed = pyqtSignal(str, str)  # group_name, hex_color

    def __init__(self, group_name: str, initial_color: str = "#808080", parent: QWidget | None = None):
        super().__init__(parent)
        self.group_name = group_name
        self._color = initial_color
        self._update_style()
        self.setFixedWidth(60)
        self.setFixedHeight(25)
        self.clicked.connect(self._pick_color)

    def _update_style(self) -> None:
        self.setStyleSheet(
            f"QPushButton {{ background-color: {self._color}; border: 1px solid #333; }}"
        )

    def _pick_color(self) -> None:
        from PyQt6.QtGui import QColor
        color = QColorDialog.getColor(QColor(self._color), self, f"Color for {self.group_name}")
        if color.isValid():
            self._color = color.name()
            self._update_style()
            self.color_changed.emit(self.group_name, self._color)

    @property
    def color(self) -> str:
        return self._color


class AppearancePanel(QWidget):
    """Step 3: Plot type selection and appearance configuration."""

    settings_changed = pyqtSignal()

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._color_buttons: list[ColorButton] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Plot type ────────────────────────────────────────────────────
        type_group = QGroupBox("Plot Type")
        tg_layout = QVBoxLayout(type_group)

        self.design_label = QLabel("Auto-detected design: (configure groups first)")
        tg_layout.addWidget(self.design_label)

        self.radio_longitudinal = QRadioButton("Longitudinal line plot (individual traces + mean±SEM)")
        self.radio_paired = QRadioButton("Paired line plot (pre→post lines per animal)")
        self.radio_delta = QRadioButton("Delta plot (change scores as strip plot)")
        self.radio_both = QRadioButton("Both paired + delta (side by side)")
        self.radio_longitudinal.setChecked(True)

        for radio in [self.radio_longitudinal, self.radio_paired, self.radio_delta, self.radio_both]:
            radio.toggled.connect(self._on_settings_changed)
            tg_layout.addWidget(radio)

        layout.addWidget(type_group)

        # ── Colors ───────────────────────────────────────────────────────
        self.color_group = QGroupBox("Colors")
        self.color_layout = QVBoxLayout(self.color_group)
        self.color_info_label = QLabel("Configure groups first to assign colors.")
        self.color_layout.addWidget(self.color_info_label)
        layout.addWidget(self.color_group)

        # ── Sex markers / line styles ────────────────────────────────────
        self.sex_group = QGroupBox("Sex encoding")
        sg_layout = QVBoxLayout(self.sex_group)
        self.show_sex_cb = QCheckBox("Show sex-specific markers")
        self.show_sex_cb.setChecked(True)
        self.show_sex_cb.toggled.connect(self._on_settings_changed)
        sg_layout.addWidget(self.show_sex_cb)
        self.sex_help_label = QLabel(
            "Male: circle (●), solid line  |  Female: triangle (▲), dotted line"
        )
        sg_layout.addWidget(self.sex_help_label)
        layout.addWidget(self.sex_group)

        # ── Axes ─────────────────────────────────────────────────────────
        axes_group = QGroupBox("Axes")
        ag_layout = QVBoxLayout(axes_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Y-axis label:"))
        self.y_label_edit = QLineEdit("50% threshold (g)")
        self.y_label_edit.textChanged.connect(self._on_settings_changed)
        row.addWidget(self.y_label_edit)
        ag_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("X-axis label:"))
        self.x_label_edit = QLineEdit("Timepoint")
        self.x_label_edit.textChanged.connect(self._on_settings_changed)
        row.addWidget(self.x_label_edit)
        ag_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit("")
        self.title_edit.textChanged.connect(self._on_settings_changed)
        row.addWidget(self.title_edit)
        ag_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Y-axis scale:"))
        self.scale_log = QRadioButton("Log")
        self.scale_linear = QRadioButton("Linear")
        self.scale_log.setChecked(True)
        self.scale_log.toggled.connect(self._on_settings_changed)
        row.addWidget(self.scale_log)
        row.addWidget(self.scale_linear)
        row.addStretch()
        ag_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Y-axis range: min"))
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(0.001, 100.0)
        self.y_min_spin.setValue(0.01)
        self.y_min_spin.setDecimals(3)
        self.y_min_spin.valueChanged.connect(self._on_settings_changed)
        row.addWidget(self.y_min_spin)
        row.addWidget(QLabel("max"))
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(0.01, 100.0)
        self.y_max_spin.setValue(10.0)
        self.y_max_spin.setDecimals(2)
        self.y_max_spin.valueChanged.connect(self._on_settings_changed)
        row.addWidget(self.y_max_spin)
        row.addStretch()
        ag_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Figure size:  W"))
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(2.0, 20.0)
        self.width_spin.setValue(4.0)
        self.width_spin.valueChanged.connect(self._on_settings_changed)
        row.addWidget(self.width_spin)
        row.addWidget(QLabel("× H"))
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(2.0, 20.0)
        self.height_spin.setValue(4.0)
        self.height_spin.valueChanged.connect(self._on_settings_changed)
        row.addWidget(self.height_spin)
        row.addWidget(QLabel("inches"))
        row.addStretch()
        ag_layout.addLayout(row)

        layout.addWidget(axes_group)
        layout.addStretch()

    def refresh(self) -> None:
        """Refresh panel based on current state."""
        if self.state.get_analysis_df() is None and self.state._merged_df is None:
            return

        timepoints = self.state.active_timepoints()
        n_tp = len(timepoints)

        if n_tp <= 2:
            self.sex_group.setTitle("Sex encoding (paired plots)")
            self.show_sex_cb.setText("Distinguish sex by line style")
            self.sex_help_label.setText(
                "Individual animals: male = solid line, female = dotted line. "
                "Group mean ± SEM with thick pre→post line."
            )
            self.state.compute_facet_slices()
            slices = self.state.get_facet_slices()
            panel_desc = ""
            if len(slices) > 1:
                panel_desc = f" | {len(slices)} figures"
            elif slices and slices[0].label != "all":
                panel_desc = f" | panel: {slices[0].label}"
            self.design_label.setText(
                f"Auto-detected design: Factorial pre-post "
                f"({self.state.pre_label} vs {self.state.post_label}{panel_desc})"
            )
            self.radio_paired.setChecked(True)
            self.state.fig_width = 4.0
            self.state.auto_assign_pre_post_labels()
        else:
            self.sex_group.setTitle("Sex encoding")
            self.show_sex_cb.setText("Show sex-specific markers")
            self.sex_help_label.setText(
                "Male: circle (●), solid line  |  Female: triangle (▲), dotted line"
            )
            self.design_label.setText(f"Auto-detected design: Longitudinal ({n_tp} timepoints)")
            self.radio_longitudinal.setChecked(True)
            self.state.fig_width = 6.0
            self.width_spin.setValue(self.state.fig_width)

        # Populate color buttons
        self._rebuild_color_buttons()

    def _rebuild_color_buttons(self) -> None:
        """Rebuild color buttons based on group columns."""
        # Clear existing
        for btn in self._color_buttons:
            self.color_layout.removeWidget(btn)
            btn.deleteLater()
        self._color_buttons.clear()
        self.color_info_label.hide()

        if self.state._merged_df is None:
            self.color_info_label.show()
            return

        analysis_df = self.state.get_analysis_df()
        source_df = analysis_df if analysis_df is not None else self.state._merged_df

        # Determine unique group values
        group_values: list[str] = []
        if self.state.group_cols:
            for col in self.state.group_cols:
                if col in source_df.columns:
                    for val in source_df[col].dropna().unique():
                        group_values.append(str(val))
        else:
            group_values = ["all"]

        # Default color cycle
        from ..plotting.plot_utils import DEFAULT_COLORS
        default_palette = ["#4169E1", "#FFA500", "#808080", "#228B22", "#DC143C", "#9932CC"]

        for i, gv in enumerate(group_values):
            color = DEFAULT_COLORS.get(gv, default_palette[i % len(default_palette)])
            if gv in self.state.colors:
                color = self.state.colors[gv]

            row = QHBoxLayout()
            row.addWidget(QLabel(f"{gv}:"))
            btn = ColorButton(gv, color)
            btn.color_changed.connect(self._on_color_changed)
            row.addWidget(btn)
            row.addStretch()

            container = QWidget()
            container.setLayout(row)
            self.color_layout.addWidget(container)
            self._color_buttons.append(btn)
            self.state.colors[gv] = color

    def _on_color_changed(self, group_name: str, hex_color: str) -> None:
        self.state.colors[group_name] = hex_color
        self._on_settings_changed()

    def _on_settings_changed(self) -> None:
        self.settings_changed.emit()

    def get_config(self) -> None:
        """Collect configuration from UI into state."""
        if self.radio_longitudinal.isChecked():
            self.state.plot_type = "longitudinal"
        elif self.radio_paired.isChecked():
            self.state.plot_type = "paired"
        elif self.radio_delta.isChecked():
            self.state.plot_type = "delta"
        else:
            self.state.plot_type = "both"

        self.state.show_sex_markers = self.show_sex_cb.isChecked()
        self.state.y_label = self.y_label_edit.text()
        self.state.x_label = self.x_label_edit.text()
        self.state.plot_title = self.title_edit.text()
        self.state.use_log_scale = self.scale_log.isChecked()
        self.state.y_min = self.y_min_spin.value()
        self.state.y_max = self.y_max_spin.value()
        self.state.fig_width = self.width_spin.value()
        self.state.fig_height = self.height_spin.value()


class PreviewPanel(QWidget):
    """Step 4: Plot preview with embedded Matplotlib canvas and animal checklist."""

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._fig: Optional[Figure] = None
        self._animal_checkboxes: dict[str, QCheckBox] = {}
        self._select_all_cb: QCheckBox | None = None
        self._updating_checkboxes: bool = False
        self._facet_combo: QComboBox | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        # ── Content area: plot (left) + checklist (right) ────────────────
        content_layout = QHBoxLayout()

        # Left side: panel selector + toolbar + canvas
        plot_area = QVBoxLayout()

        facet_row = QHBoxLayout()
        self._facet_label = QLabel("Figure panel:")
        self._facet_label.hide()
        facet_row.addWidget(self._facet_label)
        self._facet_combo = QComboBox()
        self._facet_combo.hide()
        self._facet_combo.currentIndexChanged.connect(self._on_facet_changed)
        facet_row.addWidget(self._facet_combo, stretch=1)
        facet_row.addStretch()
        plot_area.addLayout(facet_row)

        self._fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self._fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        plot_area.addWidget(self.toolbar)
        plot_area.addWidget(self.canvas, stretch=1)
        content_layout.addLayout(plot_area, stretch=1)

        # Right side: animal checklist
        checklist_panel = QWidget()
        checklist_panel.setFixedWidth(180)
        cl_layout = QVBoxLayout(checklist_panel)
        cl_layout.setContentsMargins(4, 4, 4, 4)

        cl_layout.addWidget(QLabel("<b>Animals</b>"))

        self._select_all_cb = QCheckBox("Select All")
        self._select_all_cb.setChecked(True)
        self._select_all_cb.toggled.connect(self._on_select_all_toggled)
        cl_layout.addWidget(self._select_all_cb)

        # Scrollable area for animal checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.addStretch()
        scroll.setWidget(self._scroll_content)
        cl_layout.addWidget(scroll, stretch=1)

        content_layout.addWidget(checklist_panel)
        main_layout.addLayout(content_layout, stretch=1)

        # ── Excluded animals label ────────────────────────────────────────
        self._excluded_label = QLabel("")
        self._excluded_label.setWordWrap(True)
        self._excluded_label.setStyleSheet("color: #888; font-size: 11px;")
        main_layout.addWidget(self._excluded_label)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.regenerate_btn = QPushButton("Regenerate Plot")
        self.regenerate_btn.clicked.connect(self.regenerate_plot)
        btn_row.addWidget(self.regenerate_btn)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

    # ── Checklist management ──────────────────────────────────────────────

    def _rebuild_checklist(self) -> None:
        """Rebuild the animal checklist from current data."""
        self._animal_checkboxes.clear()
        while self._scroll_layout.count():
            item = self._scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        merged = self.state.get_analysis_df()
        if merged is None:
            merged = self.state._merged_df
        if merged is None:
            self._scroll_layout.addStretch()
            return

        mouse_col = self.state.mouse_col
        group_col = self.state.group_cols[0] if self.state.group_cols else None
        excluded = set(self.state.excluded_animals)

        self._updating_checkboxes = True

        if group_col and group_col in merged.columns:
            for group_val in merged[group_col].dropna().unique():
                # Group header with color
                header = QLabel(f"<b>{group_val}</b>")
                color = self.state.colors.get(str(group_val), "#000000")
                header.setStyleSheet(f"color: {color}; margin-top: 6px;")
                self._scroll_layout.addWidget(header)

                group_mice = merged.loc[
                    merged[group_col] == group_val, mouse_col
                ].unique()
                for mid in sorted(group_mice, key=str):
                    ms = str(mid)
                    cb = QCheckBox(ms)
                    cb.setChecked(ms not in excluded)
                    cb.toggled.connect(self._on_animal_toggled)
                    self._scroll_layout.addWidget(cb)
                    self._animal_checkboxes[ms] = cb
        else:
            for mid in sorted(merged[mouse_col].unique(), key=str):
                ms = str(mid)
                cb = QCheckBox(ms)
                cb.setChecked(ms not in excluded)
                cb.toggled.connect(self._on_animal_toggled)
                self._scroll_layout.addWidget(cb)
                self._animal_checkboxes[ms] = cb

        self._scroll_layout.addStretch()
        self._updating_checkboxes = False
        self._update_select_all_state()
        self._update_excluded_label()

    def _on_select_all_toggled(self, checked: bool) -> None:
        if self._updating_checkboxes:
            return
        self._updating_checkboxes = True
        for cb in self._animal_checkboxes.values():
            cb.setChecked(checked)
        self._updating_checkboxes = False
        self._sync_excluded_from_checkboxes()
        self._update_excluded_label()
        self._replot()

    def _on_animal_toggled(self) -> None:
        if self._updating_checkboxes:
            return
        self._sync_excluded_from_checkboxes()
        self._update_select_all_state()
        self._update_excluded_label()
        self._replot()

    def _sync_excluded_from_checkboxes(self) -> None:
        """Sync state.excluded_animals from checkbox state."""
        self.state.excluded_animals = [
            ms for ms, cb in self._animal_checkboxes.items()
            if not cb.isChecked()
        ]

    def _update_select_all_state(self) -> None:
        """Update Select All checkbox to reflect current individual state."""
        if not self._animal_checkboxes:
            return
        self._updating_checkboxes = True
        all_checked = all(cb.isChecked() for cb in self._animal_checkboxes.values())
        self._select_all_cb.setChecked(all_checked)
        self._updating_checkboxes = False

    def _update_excluded_label(self) -> None:
        """Update the excluded animals text below the plot."""
        excluded = self.state.excluded_animals
        if excluded:
            self._excluded_label.setText(
                f"Excluded animals: {', '.join(sorted(excluded))}"
            )
        else:
            self._excluded_label.setText("")

    # ── Plot generation ───────────────────────────────────────────────────

    def regenerate_plot(self) -> None:
        """Rebuild checklist and regenerate the plot."""
        self._refresh_facet_selector()
        self._rebuild_checklist()
        self._replot()

    def _refresh_facet_selector(self) -> None:
        """Populate panel selector when multiple facet slices exist."""
        if self._facet_combo is None:
            return

        self._facet_combo.blockSignals(True)
        self._facet_combo.clear()

        if not self.state.is_pre_post_design():
            self._facet_label.hide()
            self._facet_combo.hide()
            self._facet_combo.blockSignals(False)
            return

        self.state.compute_facet_slices()
        slices = self.state.get_facet_slices()

        if len(slices) <= 1:
            self._facet_label.hide()
            self._facet_combo.hide()
        else:
            self._facet_label.show()
            self._facet_combo.show()
            for i, sl in enumerate(slices):
                self._facet_combo.addItem(sl.label, i)

            idx = min(max(self.state.active_facet_index, 0), len(slices) - 1)
            self._facet_combo.setCurrentIndex(idx)
            self.state.active_facet_index = idx

        self._facet_combo.blockSignals(False)

    def _on_facet_changed(self, index: int) -> None:
        if index < 0:
            return
        self.state.active_facet_index = index
        self.state.refresh_pairing_columns()
        self._rebuild_checklist()
        self._replot()

    def _replot(self) -> None:
        """Regenerate the plot, filtering out excluded animals."""
        self._fig.clear()

        merged = self.state.get_analysis_df()
        if merged is None:
            merged = self.state._merged_df
        if merged is None:
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data loaded.\nLoad data and compute thresholds first.",
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw()
            return

        tp_col = self.state.timepoint_col
        mouse_col = self.state.mouse_col
        df_plot = merged.copy()
        active_tp = self.state.active_timepoints()

        # Exclude unchecked animals
        excluded = set(self.state.excluded_animals)
        if excluded:
            df_plot = df_plot[~df_plot[mouse_col].astype(str).isin(excluded)]

        if df_plot.empty:
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data after filtering.",
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw()
            return

        group_col = self.state.group_cols[0] if self.state.group_cols else None
        colors = self.state.colors if self.state.colors else None

        plot_title = self.state.plot_title
        if self.state.is_pre_post_design():
            slices = self.state.get_facet_slices()
            if slices and len(slices) > 1:
                idx = min(max(self.state.active_facet_index, 0), len(slices) - 1)
                panel_label = slices[idx].label
                if plot_title:
                    plot_title = f"{plot_title} ({panel_label})"
                else:
                    plot_title = panel_label

        intervention_x = None
        if self.state.intervention_timepoint:
            try:
                intervention_x = float(self.state.intervention_timepoint)
            except (ValueError, TypeError):
                intervention_x = None

        pairwise = self.state._pairwise_results
        show_p = self.state.significance_style in ("stars_and_p", "p_only")

        delta_df = self.state._delta_df
        if delta_df is not None and excluded and mouse_col in delta_df.columns:
            delta_df = delta_df[~delta_df[mouse_col].astype(str).isin(excluded)]

        plot_type = self.state.plot_type

        if plot_type == "longitudinal":
            from ..plotting.longitudinal import plot_longitudinal
            self._fig, _ax = plot_longitudinal(
                df_plot,
                dependent_var="threshold_50",
                timepoint_col=tp_col,
                group_col=group_col or tp_col,
                subject_col=self.state.mouse_col,
                sex_col=self.state.sex_col,
                colors=colors,
                show_sex_encoding=self.state.show_sex_markers,
                individual_alpha=0.15,
                intervention_x=intervention_x,
                y_min=self.state.y_min,
                y_max=self.state.y_max,
                figsize=(self.state.fig_width, self.state.fig_height),
                x_label=self.state.x_label,
                y_label=self.state.y_label,
                title=plot_title,
                pairwise_results=pairwise if self.state.show_significance else None,
                show_p_values=show_p,
                use_log_scale=self.state.use_log_scale,
                fig=self._fig,
                ax=self._fig.add_subplot(111),
                timepoint_order=active_tp,
            )

        elif plot_type == "paired":
            from ..plotting.factorial import plot_paired_lines
            self._fig, _ax = plot_paired_lines(
                df_plot,
                dependent_var="threshold_50",
                timepoint_col=tp_col,
                subject_col=self.state.mouse_col,
                group_col=group_col or tp_col,
                sex_col=self.state.sex_col,
                colors=colors,
                show_sex_encoding=self.state.show_sex_markers,
                pre_label=self.state.pre_label,
                post_label=self.state.post_label,
                y_min=self.state.y_min,
                y_max=self.state.y_max,
                figsize=(self.state.fig_width, self.state.fig_height),
                y_label=self.state.y_label,
                title=plot_title,
                use_log_scale=self.state.use_log_scale,
                fig=self._fig,
                ax=self._fig.add_subplot(111),
            )

        elif plot_type == "delta":
            from ..plotting.factorial import plot_delta
            if delta_df is not None and not delta_df.empty:
                self._fig, _ax = plot_delta(
                    delta_df,
                    delta_col="delta",
                    group_col=group_col or "group",
                    sex_col=self.state.sex_col,
                    colors=colors,
                    figsize=(self.state.fig_width, self.state.fig_height),
                    y_label="Change in threshold (g)",
                    title=plot_title,
                    pairwise_results=pairwise if self.state.show_significance else None,
                    show_p_values=show_p,
                    fig=self._fig,
                    ax=self._fig.add_subplot(111),
                )
            else:
                ax = self._fig.add_subplot(111)
                ax.text(0.5, 0.5, "Run delta analysis first\n(Statistics step)",
                        ha="center", va="center", transform=ax.transAxes)

        elif plot_type == "both":
            from ..plotting.factorial import plot_paired_lines, plot_delta
            ax1 = self._fig.add_subplot(121)
            plot_paired_lines(
                df_plot,
                dependent_var="threshold_50",
                timepoint_col=tp_col,
                subject_col=self.state.mouse_col,
                group_col=group_col or tp_col,
                sex_col=self.state.sex_col,
                colors=colors,
                show_sex_encoding=self.state.show_sex_markers,
                pre_label=self.state.pre_label,
                post_label=self.state.post_label,
                y_min=self.state.y_min,
                y_max=self.state.y_max,
                y_label=self.state.y_label,
                use_log_scale=self.state.use_log_scale,
                fig=self._fig,
                ax=ax1,
            )

            ax2 = self._fig.add_subplot(122)
            if delta_df is not None and not delta_df.empty:
                plot_delta(
                    delta_df,
                    delta_col="delta",
                    group_col=group_col or "group",
                    sex_col=self.state.sex_col,
                    colors=colors,
                    y_label="Change in threshold (g)",
                    pairwise_results=pairwise if self.state.show_significance else None,
                    show_p_values=show_p,
                    fig=self._fig,
                    ax=ax2,
                )

        # Refresh the canvas with new figure
        self.canvas.figure = self._fig
        self.canvas.draw()

    def get_figure(self) -> Optional[Figure]:
        """Return the current figure for export."""
        return self._fig

    def get_figure_for_export(self) -> Optional[Figure]:
        """Regenerate plot for the active panel and return the figure."""
        self._replot()
        return self._fig
