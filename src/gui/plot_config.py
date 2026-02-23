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

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
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

        # ── Sex markers ──────────────────────────────────────────────────
        sex_group = QGroupBox("Sex Markers")
        sg_layout = QVBoxLayout(sex_group)
        self.show_sex_cb = QCheckBox("Show sex-specific markers")
        self.show_sex_cb.setChecked(True)
        self.show_sex_cb.toggled.connect(self._on_settings_changed)
        sg_layout.addWidget(self.show_sex_cb)
        sg_layout.addWidget(QLabel("Male: circle (●), solid line  |  Female: triangle (▲), dotted line"))
        layout.addWidget(sex_group)

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
        merged = self.state._merged_df
        if merged is None:
            return

        # Auto-detect design
        timepoints = [tp for tp in self.state.timepoint_order
                      if tp not in self.state.excluded_timepoints]
        n_tp = len(timepoints)

        if n_tp <= 2:
            self.design_label.setText(f"Auto-detected design: Factorial ({n_tp} timepoints)")
            self.radio_paired.setChecked(True)
            self.state.fig_width = 4.0
        else:
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

        # Determine unique group values
        group_values: list[str] = []
        if self.state.group_cols:
            for col in self.state.group_cols:
                if col in self.state._merged_df.columns:
                    for val in self.state._merged_df[col].dropna().unique():
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
    """Step 4: Plot preview with embedded Matplotlib canvas."""

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._fig: Optional[Figure] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Matplotlib canvas
        self._fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self._fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        self.regenerate_btn = QPushButton("Regenerate Plot")
        self.regenerate_btn.clicked.connect(self.regenerate_plot)
        btn_row.addWidget(self.regenerate_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def regenerate_plot(self) -> None:
        """Regenerate the plot based on current state."""
        self._fig.clear()

        merged = self.state._merged_df
        if merged is None:
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data loaded.\nLoad data and compute thresholds first.",
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw()
            return

        # Filter timepoints
        active_tp = [tp for tp in self.state.timepoint_order
                     if tp not in self.state.excluded_timepoints]

        tp_col = self.state.timepoint_col
        df_plot = merged[merged[tp_col].astype(str).isin(active_tp)].copy()

        if df_plot.empty:
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data after filtering timepoints.",
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw()
            return

        # Determine the group column for coloring
        group_col = self.state.group_cols[0] if self.state.group_cols else None

        # Build colors dict
        colors = self.state.colors if self.state.colors else None

        # Determine intervention x
        intervention_x = None
        if self.state.intervention_timepoint:
            try:
                intervention_x = float(self.state.intervention_timepoint)
            except (ValueError, TypeError):
                intervention_x = None

        pairwise = self.state._pairwise_results
        show_p = self.state.significance_style in ("stars_and_p", "p_only")

        plot_type = self.state.plot_type

        if plot_type == "longitudinal":
            from ..plotting.longitudinal import plot_longitudinal
            self._fig, _ax = plot_longitudinal(
                df_plot,
                dependent_var="threshold_50",
                timepoint_col=tp_col,
                group_col=group_col or tp_col,
                subject_col=self.state.mouse_col,
                gender_col=self.state.gender_col,
                colors=colors,
                individual_alpha=0.15,
                intervention_x=intervention_x,
                y_min=self.state.y_min,
                y_max=self.state.y_max,
                figsize=(self.state.fig_width, self.state.fig_height),
                x_label=self.state.x_label,
                y_label=self.state.y_label,
                title=self.state.plot_title,
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
                gender_col=self.state.gender_col,
                colors=colors,
                pre_label=self.state.pre_label,
                post_label=self.state.post_label,
                y_min=self.state.y_min,
                y_max=self.state.y_max,
                figsize=(self.state.fig_width, self.state.fig_height),
                y_label=self.state.y_label,
                title=self.state.plot_title,
                use_log_scale=self.state.use_log_scale,
                fig=self._fig,
                ax=self._fig.add_subplot(111),
            )

        elif plot_type == "delta":
            from ..plotting.factorial import plot_delta
            if self.state._delta_df is not None:
                self._fig, _ax = plot_delta(
                    self.state._delta_df,
                    delta_col="delta",
                    group_col=group_col or "group",
                    gender_col=self.state.gender_col,
                    colors=colors,
                    figsize=(self.state.fig_width, self.state.fig_height),
                    y_label="Change in threshold (g)",
                    title=self.state.plot_title,
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
                gender_col=self.state.gender_col,
                colors=colors,
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
            if self.state._delta_df is not None:
                plot_delta(
                    self.state._delta_df,
                    delta_col="delta",
                    group_col=group_col or "group",
                    gender_col=self.state.gender_col,
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
