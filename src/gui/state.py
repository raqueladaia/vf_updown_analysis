"""Central application state for the von Frey analysis GUI.

Holds all configuration, loaded data, and computed results in a single
AnalysisState dataclass that can be serialized to JSON for session save/load.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd


@dataclass
class AnalysisState:
    """Central state container for the analysis pipeline."""

    # ── File paths ───────────────────────────────────────────────────────
    filament_ref_path: str = ""
    data_file_path: str = ""
    metadata_file_path: str = ""
    output_dir: str = ""

    # ── Column mappings ──────────────────────────────────────────────────
    mouse_col: str = "mouse"
    timepoint_col: str = "Timepoint_SNI_day"
    series_col: str = "xo_series"
    filament_col: str = "last_filament"
    gender_col: str = "gender"
    meta_mouse_col: str = "mouse"
    log_column: str = "Log_new"

    # ── Group configuration ──────────────────────────────────────────────
    group_cols: list[str] = field(default_factory=list)
    excluded_timepoints: list[str] = field(default_factory=list)
    timepoint_order: list[str] = field(default_factory=list)
    timepoint_type: str = "numeric"  # 'numeric' or 'categorical'
    intervention_timepoint: Optional[str] = None

    # ── Plot configuration ───────────────────────────────────────────────
    plot_type: str = "longitudinal"  # 'longitudinal', 'paired', 'delta', 'both'
    colors: dict[str, str] = field(default_factory=dict)
    show_sex_markers: bool = True
    y_label: str = "50% threshold (g)"
    x_label: str = "Timepoint"
    plot_title: str = ""
    use_log_scale: bool = True
    y_min: float = 0.01
    y_max: float = 10.0
    fig_width: float = 4.0
    fig_height: float = 4.0

    # ── Statistical options ──────────────────────────────────────────────
    longitudinal_test: str = "rm_anova"  # 'rm_anova', 'pairwise_ttest', 'mixed_effects'
    run_posthoc: bool = True
    run_delta_analysis: bool = False
    run_anova: bool = False
    correction_method: str = "holm"  # 'holm', 'bonferroni', 'fdr_bh', 'none'
    pre_label: str = "pre"
    post_label: str = "post_chronic"
    show_significance: bool = True
    significance_style: str = "stars_and_p"  # 'stars_and_p', 'stars_only', 'p_only', 'none'

    # ── Export options ───────────────────────────────────────────────────
    export_formats: list[str] = field(default_factory=lambda: ["pdf"])
    filename_prefix: str = "vf_updown_analysis"
    export_data: bool = True
    export_stats: bool = True

    # ── Loaded data (not serialized to JSON) ─────────────────────────────
    _filament_info: Optional[pd.DataFrame] = field(default=None, repr=False)
    _series_stats: Optional[dict[str, float]] = field(default=None, repr=False)
    _data_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _metadata_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _merged_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _delta_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _stat_results: Optional[Any] = field(default=None, repr=False)
    _pairwise_results: Optional[list] = field(default=None, repr=False)

    def to_json(self) -> str:
        """Serialize settings (not data) to JSON."""
        d = {}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            d[k] = v
        return json.dumps(d, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> AnalysisState:
        """Deserialize settings from JSON."""
        d = json.loads(json_str)
        return cls(**{k: v for k, v in d.items() if not k.startswith("_")})

    def save_session(self, path: str | Path) -> None:
        """Save session to a JSON file."""
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load_session(cls, path: str | Path) -> AnalysisState:
        """Load session from a JSON file."""
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_json(text)
