"""Central application state for the von Frey analysis GUI.



Holds all configuration, loaded data, and computed results in a single
AnalysisState dataclass that can be serialized to JSON for session save/load.
"""



from __future__ import annotations



import json
from dataclasses import dataclass, field, fields
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
    sex_col: str = "sex"
    meta_mouse_col: str = "mouse"
    log_column: str = "Log_new"



    # ── Group configuration ──────────────────────────────────────────────
    group_cols: list[str] = field(default_factory=list)
    facet_cols: list[str] = field(default_factory=list)
    facet_values: dict[str, list[str]] = field(default_factory=dict)
    active_facet_index: int = 0
    pairing_cols: list[str] = field(default_factory=list)
    filter_accept: bool = True
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
    correction_method: str = "holm"  # 'holm', 'bonferroni', 'fdr_bh', 'none'
    pre_label: str = "pre"
    post_label: str = "post"
    show_significance: bool = True
    significance_style: str = "stars_and_p"  # 'stars_and_p', 'stars_only', 'p_only', 'none'



    # ── Animal inclusion (exploratory) ────────────────────────────────────
    excluded_animals: list[str] = field(default_factory=list)



    # ── Loaded data (not serialized to JSON) ─────────────────────────────
    _filament_info: Optional[pd.DataFrame] = field(default=None, repr=False)
    _series_stats: Optional[dict[str, float]] = field(default=None, repr=False)
    _data_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _metadata_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _merged_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _delta_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _stat_results: Optional[Any] = field(default=None, repr=False)
    _pairwise_results: Optional[list] = field(default=None, repr=False)
    _facet_slices: Optional[list] = field(default=None, repr=False)



    def get_base_df(self) -> Optional[pd.DataFrame]:
        """Merged data after timepoint exclusion only."""
        if self._merged_df is None:
            return None
        from ..core.data_loader import build_analysis_dataframe



        return build_analysis_dataframe(
            self._merged_df,
            mouse_col=self.mouse_col,
            timepoint_col=self.timepoint_col,
            timepoint_order=self.timepoint_order,
            excluded_timepoints=self.excluded_timepoints,
        )



    def compute_facet_slices(self) -> list:
        """Build or refresh panel slices for pre-post designs."""
        from ..core.data_loader import FacetSlice, build_facet_slices



        if self._merged_df is None:
            self._facet_slices = []
            return self._facet_slices



        if not self.is_pre_post_design():
            base = self.get_base_df()
            if base is None:
                self._facet_slices = []
            else:
                self._facet_slices = [FacetSlice(filters={}, label="all", df=base)]
            return self._facet_slices



        self._facet_slices = build_facet_slices(
            self._merged_df,
            mouse_col=self.mouse_col,
            timepoint_col=self.timepoint_col,
            timepoint_order=self.timepoint_order,
            excluded_timepoints=self.excluded_timepoints,
            facet_cols=self.facet_cols,
            facet_values=self.facet_values,
        )
        return self._facet_slices



    def get_facet_slices(self) -> list:
        """Return cached facet slices, computing if needed."""
        if self._facet_slices is None:
            return self.compute_facet_slices()
        return self._facet_slices



    def get_analysis_df(self) -> Optional[pd.DataFrame]:
        """Data for the active panel (or full timepoint-filtered data)."""
        if self._merged_df is None:
            return None



        if not self.is_pre_post_design():
            return self.get_base_df()



        slices = self.get_facet_slices()
        if not slices:
            return self.get_base_df()



        idx = min(max(self.active_facet_index, 0), len(slices) - 1)
        return slices[idx].df



    def invalidate_facet_slices(self) -> None:
        """Clear cached panel slices after configuration changes."""
        self._facet_slices = None



    def active_timepoints(self) -> list[str]:
        """Non-excluded timepoints in display order."""
        from ..core.data_loader import get_active_timepoints



        return get_active_timepoints(self.timepoint_order, self.excluded_timepoints)



    def is_pre_post_design(self) -> bool:
        """True when ≤2 active timepoints (factorial pre-post mode)."""
        from ..core.data_loader import is_pre_post_design



        return is_pre_post_design(self.timepoint_order, self.excluded_timepoints)



    def get_factor_candidates(self) -> list[str]:
        """Data-file columns that can serve as panel or pairing factors."""
        if self._data_df is None:
            return []
        from ..core.data_loader import detect_facet_factor_candidates



        return detect_facet_factor_candidates(
            self._data_df,
            mouse_col=self.mouse_col,
            timepoint_col=self.timepoint_col,
            series_col=self.series_col,
            filament_col=self.filament_col,
        )



    def infer_pairing_columns(self) -> list[str]:
        """Infer columns that split pre/post pairs within each mouse."""
        from ..core.data_loader import get_pairing_columns, infer_pre_post_labels



        df = self.get_analysis_df()
        if df is None or df.empty:
            return []
        active = self.active_timepoints()
        if len(active) != 2:
            return []
        pre_label, post_label = infer_pre_post_labels(active)



        return get_pairing_columns(
            df,
            self.mouse_col,
            self.timepoint_col,
            pre_label,
            post_label,
            self.group_cols,
            self.facet_cols,
            self.get_factor_candidates(),
        )



    def refresh_pairing_columns(self) -> None:
        """Update pairing_cols from current filters and comparison groups."""
        self.pairing_cols = self.infer_pairing_columns()



    def auto_assign_pre_post_labels(self) -> None:
        """Set pre/post labels from active timepoints when exactly two exist."""
        from ..core.data_loader import infer_pre_post_labels



        active = self.active_timepoints()
        if len(active) == 2:
            self.pre_label, self.post_label = infer_pre_post_labels(active)



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
        if "blocking_factor_cols" in d and "facet_cols" not in d:
            d["facet_cols"] = d.pop("blocking_factor_cols")
        if "blocking_factor_values" in d and "facet_values" not in d:
            d["facet_values"] = d.pop("blocking_factor_values")
        if "gender_col" in d and "sex_col" not in d:
            d["sex_col"] = d.pop("gender_col")
        for obsolete in (
            "blocking_factor_cols",
            "blocking_factor_values",
            "gender_col",
            "run_posthoc",
            "run_delta_analysis",
            "run_anova",
            "export_formats",
            "export_data",
            "export_stats",
            "filename_prefix",
        ):
            d.pop(obsolete, None)



        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})



    def save_session(self, path: str | Path) -> None:
        """Save session to a JSON file."""
        Path(path).write_text(self.to_json(), encoding="utf-8")



    @classmethod
    def load_session(cls, path: str | Path) -> AnalysisState:
        """Load session from a JSON file."""
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_json(text)


