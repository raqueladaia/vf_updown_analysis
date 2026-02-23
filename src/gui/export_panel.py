"""Steps 5 & 6: Statistical analysis and export panels.

Step 5: Statistical analysis configuration and results display.
Step 6: Figure and data export.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .state import AnalysisState


class StatsPanel(QWidget):
    """Step 5: Statistical analysis configuration and results."""

    stats_done = pyqtSignal()

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Longitudinal test options ─────────────────────────────────────
        self.longitudinal_group = QGroupBox("For longitudinal designs (3+ timepoints)")
        lg_layout = QVBoxLayout(self.longitudinal_group)

        self.radio_rm_anova = QRadioButton(
            "Repeated-measures ANOVA (group x timepoint, Greenhouse-Geisser corrected)"
        )
        self.radio_pairwise = QRadioButton(
            "Pairwise t-tests at each timepoint (Welch's t, corrected across ALL timepoints)"
        )
        self.radio_mixed_model = QRadioButton(
            "Mixed-effects model (threshold ~ group * C(timepoint), random: mouse)"
        )
        self.radio_rm_anova.setChecked(True)

        for r in [self.radio_rm_anova, self.radio_pairwise, self.radio_mixed_model]:
            lg_layout.addWidget(r)

        # Correction method (shared by RM-ANOVA post-hoc and pairwise t-tests)
        correction_row = QHBoxLayout()
        correction_row.addWidget(QLabel("Post-hoc / pairwise correction:"))
        self.correction_combo = QComboBox()
        self.correction_combo.addItems([
            "Holm-Bonferroni", "Bonferroni", "Benjamini-Hochberg FDR", "None",
        ])
        correction_row.addWidget(self.correction_combo)
        correction_row.addStretch()
        lg_layout.addLayout(correction_row)

        self.cb_posthoc = QCheckBox("Run post-hoc pairwise comparisons at each timepoint")
        self.cb_posthoc.setChecked(True)
        lg_layout.addWidget(self.cb_posthoc)

        layout.addWidget(self.longitudinal_group)

        # ── Factorial options ────────────────────────────────────────────
        self.factorial_group = QGroupBox("For factorial pre-post designs (2 timepoints)")
        fg_layout = QVBoxLayout(self.factorial_group)
        self.cb_delta = QCheckBox("Delta score analysis (post - pre)")
        self.cb_delta.setChecked(True)
        fg_layout.addWidget(self.cb_delta)

        pre_post_row = QHBoxLayout()
        pre_post_row.addWidget(QLabel("  Pre label:"))
        self.pre_combo = QComboBox()
        pre_post_row.addWidget(self.pre_combo)
        pre_post_row.addWidget(QLabel("  Post label:"))
        self.post_combo = QComboBox()
        pre_post_row.addWidget(self.post_combo)
        pre_post_row.addStretch()
        fg_layout.addLayout(pre_post_row)

        self.cb_anova = QCheckBox("ANOVA on delta scores")
        self.cb_anova.setChecked(True)
        fg_layout.addWidget(self.cb_anova)
        self.cb_effect_size = QCheckBox("Effect sizes (Cohen's d)")
        self.cb_effect_size.setChecked(True)
        fg_layout.addWidget(self.cb_effect_size)
        layout.addWidget(self.factorial_group)

        # Run button
        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.setStyleSheet("QPushButton { padding: 8px; font-weight: bold; }")
        self.run_btn.clicked.connect(self._run_analysis)
        layout.addWidget(self.run_btn)

        # ── Results ──────────────────────────────────────────────────────
        results_group = QGroupBox("Results")
        rg_layout = QVBoxLayout(results_group)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(200)
        self.results_text.setFontFamily("Courier New")
        rg_layout.addWidget(self.results_text)
        layout.addWidget(results_group)

        # ── Significance display options ─────────────────────────────────
        sig_group = QGroupBox("Significance Display")
        sg_layout = QVBoxLayout(sig_group)

        self.cb_show_sig = QCheckBox("Show significance on plot")
        self.cb_show_sig.setChecked(True)
        sg_layout.addWidget(self.cb_show_sig)

        self.radio_stars_p = QRadioButton("Stars + p-value")
        self.radio_stars_only = QRadioButton("Stars only")
        self.radio_p_only = QRadioButton("p-value only")
        self.radio_none = QRadioButton("None")
        self.radio_stars_p.setChecked(True)
        for r in [self.radio_stars_p, self.radio_stars_only, self.radio_p_only, self.radio_none]:
            sg_layout.addWidget(r)

        layout.addWidget(sig_group)
        layout.addStretch()

    def refresh(self) -> None:
        """Refresh panel based on current state."""
        merged = self.state._merged_df
        if merged is None:
            return

        # Populate pre/post combos from timepoints
        timepoints = [tp for tp in self.state.timepoint_order
                      if tp not in self.state.excluded_timepoints]

        self.pre_combo.clear()
        self.post_combo.clear()
        for tp in timepoints:
            self.pre_combo.addItem(tp)
            self.post_combo.addItem(tp)

        # Auto-select first as pre, last as post
        if len(timepoints) >= 2:
            self.pre_combo.setCurrentIndex(0)
            self.post_combo.setCurrentIndex(len(timepoints) - 1)

        # Show/hide appropriate options based on design
        n_tp = len(timepoints)
        is_longitudinal = n_tp > 2
        self.longitudinal_group.setVisible(is_longitudinal)
        self.factorial_group.setVisible(not is_longitudinal)

    def _get_correction_key(self) -> str:
        """Map the correction combo text to the internal key."""
        text = self.correction_combo.currentText()
        mapping = {
            "Holm-Bonferroni": "holm",
            "Bonferroni": "bonferroni",
            "Benjamini-Hochberg FDR": "fdr_bh",
            "None": "none",
        }
        return mapping.get(text, "holm")

    def _run_analysis(self) -> None:
        """Run the selected statistical analyses."""
        merged = self.state._merged_df
        if merged is None:
            QMessageBox.warning(self, "No Data", "Load data and compute thresholds first.")
            return

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        self.results_text.clear()

        results_parts: list[str] = []
        group_col = self.state.group_cols[0] if self.state.group_cols else None

        # Get active timepoints
        active_tp = [tp for tp in self.state.timepoint_order
                     if tp not in self.state.excluded_timepoints]
        tp_col = self.state.timepoint_col
        df = merged[merged[tp_col].astype(str).isin(active_tp)].copy()

        correction = self._get_correction_key()
        self.state.correction_method = correction

        try:
            # ── Longitudinal analysis (3+ timepoints) ────────────────────
            if self.longitudinal_group.isVisible() and group_col:
                self._run_longitudinal(df, group_col, tp_col, correction, results_parts)

            # ── Factorial analysis (2 timepoints) ────────────────────────
            if self.factorial_group.isVisible():
                self._run_factorial(df, group_col, tp_col, correction, results_parts)

        except Exception as e:
            import traceback
            results_parts.append("\n" + "=" * 60)
            results_parts.append("ERROR")
            results_parts.append("=" * 60)
            results_parts.append(f"{type(e).__name__}: {e}")
            results_parts.append("")
            results_parts.append("Traceback (for debugging):")
            results_parts.append(traceback.format_exc())

        self.results_text.setPlainText("\n".join(results_parts))

        # Save significance display options
        self.state.show_significance = self.cb_show_sig.isChecked()
        if self.radio_stars_p.isChecked():
            self.state.significance_style = "stars_and_p"
        elif self.radio_stars_only.isChecked():
            self.state.significance_style = "stars_only"
        elif self.radio_p_only.isChecked():
            self.state.significance_style = "p_only"
        else:
            self.state.significance_style = "none"

        self.run_btn.setText("Run Analysis")
        self.run_btn.setEnabled(True)
        self.stats_done.emit()

    def _run_longitudinal(
        self,
        df: "pd.DataFrame",
        group_col: str,
        tp_col: str,
        correction: str,
        results_parts: list[str],
    ) -> None:
        """Dispatch longitudinal analysis based on selected radio button."""
        import pandas as pd
        from ..core.statistics import (
            pairwise_results_to_dataframe,
            run_mixed_effects_model,
            run_posthoc_pairwise_at_timepoints,
            run_rm_anova,
        )

        # ── Option 1: Repeated-measures ANOVA ─────────────────────────
        if self.radio_rm_anova.isChecked():
            self.state.longitudinal_test = "rm_anova"

            rm_result = run_rm_anova(
                df, "threshold_50", group_col, tp_col, self.state.mouse_col
            )
            self.state._stat_results = rm_result
            results_parts.append("=" * 60)
            results_parts.append("REPEATED-MEASURES ANOVA")
            results_parts.append("=" * 60)
            results_parts.append(rm_result.summary_text)
            if rm_result.warnings:
                results_parts.append("")
                results_parts.append(
                    "NOTE: Check the warnings above for details."
                )

            # Post-hoc pairwise
            if self.cb_posthoc.isChecked():
                pw = run_posthoc_pairwise_at_timepoints(
                    df, "threshold_50", group_col, tp_col, correction
                )
                self.state._pairwise_results = pw
                pw_df = pairwise_results_to_dataframe(pw)
                results_parts.append("\n" + "=" * 60)
                results_parts.append(
                    f"POST-HOC PAIRWISE (Welch's t, {correction} corrected)"
                )
                results_parts.append("=" * 60)
                if not pw_df.empty:
                    results_parts.append(pw_df.to_string(index=False))
                else:
                    results_parts.append("No valid pairwise comparisons (n < 2 in some cells).")

        # ── Option 2: Pairwise t-tests with correction ────────────────
        elif self.radio_pairwise.isChecked():
            self.state.longitudinal_test = "pairwise_ttest"

            pw = run_posthoc_pairwise_at_timepoints(
                df, "threshold_50", group_col, tp_col, correction
            )
            self.state._pairwise_results = pw
            self.state._stat_results = None

            pw_df = pairwise_results_to_dataframe(pw)
            results_parts.append("=" * 60)
            results_parts.append(
                f"PAIRWISE WELCH'S T-TESTS ({correction} corrected across ALL timepoints)"
            )
            results_parts.append("=" * 60)
            n_comparisons = len(pw)
            results_parts.append(f"Total comparisons: {n_comparisons}")
            results_parts.append(f"Correction method: {correction}")
            results_parts.append("")
            if not pw_df.empty:
                results_parts.append(pw_df.to_string(index=False))
            else:
                results_parts.append("No valid pairwise comparisons (n < 2 in some cells).")

        # ── Option 3: Mixed-effects model ─────────────────────────────
        elif self.radio_mixed_model.isChecked():
            self.state.longitudinal_test = "mixed_effects"

            lme_result = run_mixed_effects_model(
                df, "threshold_50", group_col, tp_col, self.state.mouse_col
            )
            self.state._stat_results = lme_result
            results_parts.append("=" * 60)
            results_parts.append("LINEAR MIXED-EFFECTS MODEL")
            results_parts.append("=" * 60)
            results_parts.append(lme_result.summary_text)
            if lme_result.warnings:
                results_parts.append("")
                results_parts.append(
                    "NOTE: Check the warnings above for details."
                )

            # Post-hoc pairwise
            if self.cb_posthoc.isChecked():
                pw = run_posthoc_pairwise_at_timepoints(
                    df, "threshold_50", group_col, tp_col, correction
                )
                self.state._pairwise_results = pw
                pw_df = pairwise_results_to_dataframe(pw)
                results_parts.append("\n" + "=" * 60)
                results_parts.append(
                    f"POST-HOC PAIRWISE (Welch's t, {correction} corrected)"
                )
                results_parts.append("=" * 60)
                if not pw_df.empty:
                    results_parts.append(pw_df.to_string(index=False))
                else:
                    results_parts.append("No valid pairwise comparisons (n < 2 in some cells).")

    def _run_factorial(
        self,
        df: "pd.DataFrame",
        group_col: str | None,
        tp_col: str,
        correction: str,
        results_parts: list[str],
    ) -> None:
        """Run factorial (pre-post) analyses."""
        if not self.cb_delta.isChecked():
            return

        from ..core.statistics import (
            compute_delta_scores,
            pairwise_results_to_dataframe,
            run_anova_on_deltas,
            run_posthoc_on_deltas,
        )

        pre_label = self.pre_combo.currentText()
        post_label = self.post_combo.currentText()
        self.state.pre_label = pre_label
        self.state.post_label = post_label

        delta_df = compute_delta_scores(
            df, "threshold_50", tp_col, self.state.mouse_col,
            pre_label, post_label,
        )
        self.state._delta_df = delta_df
        results_parts.append("=" * 60)
        results_parts.append("DELTA SCORES (post - pre)")
        results_parts.append("=" * 60)
        results_parts.append(delta_df.to_string())

        if self.cb_anova.isChecked() and group_col and group_col in delta_df.columns:
            anova_factors = [c for c in self.state.group_cols if c in delta_df.columns]
            if anova_factors:
                anova_result = run_anova_on_deltas(delta_df, "delta", anova_factors)
                self.state._stat_results = anova_result
                results_parts.append("\n" + "=" * 60)
                results_parts.append("ANOVA ON DELTA SCORES")
                results_parts.append("=" * 60)
                results_parts.append(anova_result.summary_text)

        if group_col and group_col in delta_df.columns:
            pw = run_posthoc_on_deltas(
                delta_df, "delta", group_col, correction
            )
            self.state._pairwise_results = pw
            pw_df = pairwise_results_to_dataframe(pw)
            results_parts.append("\n" + "=" * 60)
            results_parts.append("POST-HOC COMPARISONS ON DELTAS")
            results_parts.append("=" * 60)
            results_parts.append(pw_df.to_string(index=False))


class ExportPanel(QWidget):
    """Step 6: Figure and data export."""

    def __init__(self, state: AnalysisState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._get_figure_callback = None
        self._init_ui()

    def set_figure_callback(self, callback) -> None:
        """Set a callback that returns the current matplotlib Figure."""
        self._get_figure_callback = callback

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Figure export ────────────────────────────────────────────────
        fig_group = QGroupBox("Figure")
        fg_layout = QVBoxLayout(fig_group)
        self.cb_pdf = QCheckBox("PDF (vector, Illustrator-compatible)")
        self.cb_pdf.setChecked(True)
        self.cb_png = QCheckBox("PNG (300 DPI)")
        self.cb_svg = QCheckBox("SVG")
        fg_layout.addWidget(self.cb_pdf)
        fg_layout.addWidget(self.cb_png)
        fg_layout.addWidget(self.cb_svg)
        layout.addWidget(fig_group)

        # ── Data export ──────────────────────────────────────────────────
        data_group = QGroupBox("Data")
        dg_layout = QVBoxLayout(data_group)
        self.cb_data_xlsx = QCheckBox("Processed data with thresholds (.xlsx)")
        self.cb_data_xlsx.setChecked(True)
        self.cb_stats_xlsx = QCheckBox("Statistical results (.xlsx)")
        self.cb_stats_xlsx.setChecked(True)
        self.cb_raw_csv = QCheckBox("Raw computed values (.csv)")
        dg_layout.addWidget(self.cb_data_xlsx)
        dg_layout.addWidget(self.cb_stats_xlsx)
        dg_layout.addWidget(self.cb_raw_csv)
        layout.addWidget(data_group)

        # ── Output settings ──────────────────────────────────────────────
        settings_group = QGroupBox("Output Settings")
        sg_layout = QVBoxLayout(settings_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Output folder:"))
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory")
        btn = QPushButton("Browse...")
        btn.clicked.connect(self._browse_output_dir)
        row.addWidget(self.output_dir_edit, stretch=1)
        row.addWidget(btn)
        sg_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Filename prefix:"))
        self.prefix_edit = QLineEdit("vf_updown_analysis")
        row.addWidget(self.prefix_edit)
        sg_layout.addLayout(row)

        layout.addWidget(settings_group)

        # ── Export button ────────────────────────────────────────────────
        self.export_btn = QPushButton("Export All")
        self.export_btn.setStyleSheet("QPushButton { padding: 10px; font-weight: bold; font-size: 14px; }")
        self.export_btn.clicked.connect(self._export)
        layout.addWidget(self.export_btn)

        self.export_status = QLabel("")
        layout.addWidget(self.export_status)

        layout.addStretch()

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_dir_edit.setText(path)
            self.state.output_dir = path

    def _export(self) -> None:
        output_dir = self.output_dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select an output directory.")
            return

        prefix = self.prefix_edit.text() or "vf_updown_analysis"
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        exported_files: list[str] = []

        try:
            # Export figure
            if self._get_figure_callback:
                fig = self._get_figure_callback()
                if fig is not None:
                    formats = []
                    if self.cb_pdf.isChecked():
                        formats.append("pdf")
                    if self.cb_png.isChecked():
                        formats.append("png")
                    if self.cb_svg.isChecked():
                        formats.append("svg")

                    from ..plotting.plot_utils import export_figure
                    paths = export_figure(fig, output_dir, prefix, formats)
                    exported_files.extend(str(p) for p in paths)

            # Export processed data
            if self.cb_data_xlsx.isChecked() and self.state._merged_df is not None:
                data_path = output_path / f"{prefix}_data.xlsx"
                self.state._merged_df.to_excel(data_path, index=False)
                exported_files.append(str(data_path))

            # Export statistical results
            if self.cb_stats_xlsx.isChecked() and self.state._stat_results is not None:
                stats_path = output_path / f"{prefix}_stats.xlsx"
                with open(stats_path.with_suffix(".txt"), "w") as f:
                    f.write(self.state._stat_results.summary_text)
                exported_files.append(str(stats_path.with_suffix(".txt")))

                if self.state._stat_results.table is not None:
                    self.state._stat_results.table.to_excel(stats_path)
                    exported_files.append(str(stats_path))

                # Also export pairwise results
                if self.state._pairwise_results:
                    from ..core.statistics import pairwise_results_to_dataframe
                    pw_df = pairwise_results_to_dataframe(self.state._pairwise_results)
                    pw_path = output_path / f"{prefix}_pairwise.xlsx"
                    pw_df.to_excel(pw_path, index=False)
                    exported_files.append(str(pw_path))

            # Export raw CSV
            if self.cb_raw_csv.isChecked() and self.state._merged_df is not None:
                csv_path = output_path / f"{prefix}_raw.csv"
                self.state._merged_df.to_csv(csv_path, index=False)
                exported_files.append(str(csv_path))

            self.export_status.setText(f"Exported {len(exported_files)} files to {output_dir}")
            self.export_status.setStyleSheet("color: green;")

        except Exception as e:
            self.export_status.setText(f"Export error: {e}")
            self.export_status.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Export Error", str(e))
