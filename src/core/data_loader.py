"""Data loading and validation for von Frey up-down analysis.

Handles loading experimental data files (Excel/CSV) and metadata files,
validates required columns, merges metadata into data, and provides
clear error messages for common issues.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Optional, Union

import pandas as pd


@dataclass
class FacetSlice:
    """One figure panel: a single combination of panel-factor levels."""

    filters: dict[str, str]
    label: str
    df: pd.DataFrame


METADATA_ACCEPT_COLUMN_CANDIDATES = ("accept", "include_in_analysis", "accepted")


def detect_metadata_accept_column(metadata_df: pd.DataFrame) -> Optional[str]:
    """Return the metadata column that flags animals for inclusion, if present."""
    for col in METADATA_ACCEPT_COLUMN_CANDIDATES:
        if col in metadata_df.columns:
            return col
    for col in metadata_df.columns:
        if "accept" in str(col).lower():
            return col
    return None


def get_mice_not_accepted(
    metadata_df: Optional[pd.DataFrame],
    meta_mouse_col: str,
) -> list[str]:
    """Return mouse IDs (as strings) with accept/include flag equal to zero.

    Animals without an explicit zero remain included (unchecked list empty for them).
    """
    if metadata_df is None or metadata_df.empty:
        return []

    accept_col = detect_metadata_accept_column(metadata_df)
    if accept_col is None:
        return []

    id_col = meta_mouse_col if meta_mouse_col in metadata_df.columns else None
    if id_col is None:
        for candidate in ("mouse", "animal_id"):
            if candidate in metadata_df.columns:
                id_col = candidate
                break
    if id_col is None:
        return []

    mask = metadata_df[accept_col] == 0
    return [str(m) for m in metadata_df.loc[mask, id_col].dropna().unique()]


def filter_metadata_by_accept(
    metadata_df: pd.DataFrame,
    filter_accept: bool = True,
    accept_col: Optional[str] = None,
) -> pd.DataFrame:
    """Return metadata subset with accepted mice only when column exists.

    Args:
        metadata_df: Metadata DataFrame.
        filter_accept: If True and an accept column exists, keep rows with accept==1.
        accept_col: Name of the inclusion column. Auto-detected when None.

    Returns:
        Filtered metadata DataFrame (copy).
    """
    df = metadata_df.copy()
    col = accept_col or detect_metadata_accept_column(df)
    if filter_accept and col is not None:
        df = df[df[col] == 1]
    return df


def load_excel_or_csv(
    filepath: Union[str, Path],
    sheet_name: str = "Sheet1",
) -> pd.DataFrame:
    """Load a data file (Excel or CSV) into a DataFrame.

    Args:
        filepath: Path to the data file.
        sheet_name: Sheet name for Excel files (ignored for CSV).

    Returns:
        Loaded DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is unsupported or cannot be read.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    suffix = filepath.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(filepath, engine="openpyxl", sheet_name=sheet_name)
    elif suffix == ".csv":
        return pd.read_csv(filepath)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .xlsx, .xls, or .csv")


def validate_data_columns(
    df: pd.DataFrame,
    mouse_col: str = "mouse",
    timepoint_col: str = "Timepoint_SNI_day",
    series_col: str = "xo_series",
    filament_col: str = "last_filament",
) -> list[str]:
    """Validate that required columns exist in the data DataFrame.

    Args:
        df: The data DataFrame to validate.
        mouse_col: Expected mouse ID column name.
        timepoint_col: Expected timepoint column name.
        series_col: Expected xo_series column name.
        filament_col: Expected last_filament column name.

    Returns:
        List of warning/error messages. Empty list means all valid.
    """
    errors: list[str] = []
    required = {
        "mouse": mouse_col,
        "timepoint": timepoint_col,
        "xo_series": series_col,
        "last_filament": filament_col,
    }

    for label, col_name in required.items():
        if col_name not in df.columns:
            errors.append(f"Missing required column '{col_name}' ({label})")

    if series_col in df.columns:
        invalid_series = df[series_col].dropna().apply(
            lambda s: not (isinstance(s, str) and all(c in "xXoO" for c in s))
        )
        n_invalid = invalid_series.sum()
        if n_invalid > 0:
            errors.append(f"{n_invalid} rows have invalid xo_series values (must be x/o characters only)")

    return errors


def validate_metadata_columns(
    df: pd.DataFrame,
    mouse_col: str = "mouse",
    sex_col: str = "sex",
    meta_mouse_col: Optional[str] = None,
) -> list[str]:
    """Validate that required columns exist in the metadata DataFrame.

    Args:
        df: The metadata DataFrame to validate.
        mouse_col: Mouse ID column name in the data file (used if meta_mouse_col is None).
        sex_col: Expected sex column name.
        meta_mouse_col: Mouse ID column name in the metadata file.
            If None, falls back to mouse_col.

    Returns:
        List of warning/error messages.
    """
    errors: list[str] = []
    effective_mouse_col = meta_mouse_col if meta_mouse_col is not None else mouse_col

    if effective_mouse_col not in df.columns:
        errors.append(f"Missing required column '{effective_mouse_col}' in metadata")

    if sex_col not in df.columns:
        errors.append(f"Missing required column '{sex_col}' in metadata")
    elif sex_col in df.columns:
        valid_sexes = {"male", "female"}
        actual = set(df[sex_col].dropna().str.lower().unique())
        invalid = actual - valid_sexes
        if invalid:
            errors.append(f"Invalid sex values: {invalid}. Expected 'male' or 'female'.")

    return errors


def check_mouse_id_match(
    data_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    mouse_col: str = "mouse",
    meta_mouse_col: Optional[str] = None,
) -> list[str]:
    """Check that mouse IDs match between data and metadata files.

    Args:
        data_df: The experimental data DataFrame.
        metadata_df: The metadata DataFrame.
        mouse_col: Column name for mouse IDs in the data file.
        meta_mouse_col: Column name for mouse IDs in the metadata file.
            If None, uses mouse_col.

    Returns:
        List of warning messages about mismatches.
    """
    warnings: list[str] = []
    effective_meta_col = meta_mouse_col if meta_mouse_col is not None else mouse_col

    data_mice = set(data_df[mouse_col].unique())
    meta_mice = set(metadata_df[effective_meta_col].unique())

    in_data_not_meta = data_mice - meta_mice
    in_meta_not_data = meta_mice - data_mice

    if in_data_not_meta:
        warnings.append(
            f"Mice in data but not in metadata: {sorted(in_data_not_meta)}. "
            "These animals will have missing group/sex info."
        )
    if in_meta_not_data:
        warnings.append(
            f"Mice in metadata but not in data: {sorted(in_meta_not_data)}. "
            "These animals have no observations."
        )

    return warnings


def merge_metadata(
    data_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    mouse_col: str = "mouse",
    group_cols: Optional[list[str]] = None,
    sex_col: str = "sex",
    meta_mouse_col: Optional[str] = None,
) -> pd.DataFrame:
    """Merge metadata columns into the data DataFrame.

    Args:
        data_df: The experimental data DataFrame.
        metadata_df: The metadata DataFrame.
        mouse_col: Column name for mouse IDs in the data file (merge key).
        group_cols: List of group-defining column names from metadata to merge.
            If None, merges all metadata columns except the mouse column.
        sex_col: Sex column name.
        meta_mouse_col: Column name for mouse IDs in the metadata file.
            If None, uses mouse_col. When different from mouse_col, the
            metadata column is renamed to mouse_col before merging.

    Returns:
        Merged DataFrame with metadata columns added.
    """
    effective_meta_col = meta_mouse_col if meta_mouse_col is not None else mouse_col

    # Rename metadata mouse column to match data mouse column if they differ
    if effective_meta_col != mouse_col:
        metadata_df = metadata_df.rename(columns={effective_meta_col: mouse_col})

    if group_cols is not None:
        cols_to_merge = [mouse_col] + [sex_col] + [c for c in group_cols if c != sex_col]
        cols_to_merge = [c for c in cols_to_merge if c in metadata_df.columns]
    else:
        cols_to_merge = list(metadata_df.columns)

    # Remove columns that already exist in data_df (except the merge key)
    existing_in_data = set(data_df.columns) - {mouse_col}
    cols_to_merge = [c for c in cols_to_merge if c == mouse_col or c not in existing_in_data]

    merged = data_df.merge(
        metadata_df[cols_to_merge],
        on=mouse_col,
        how="left",
    )

    return merged


def detect_column_candidates(df: pd.DataFrame) -> dict[str, list[str]]:
    """Auto-detect likely column names for required fields.

    Looks for columns matching common patterns for mouse ID, timepoint,
    xo_series, and last_filament.

    Args:
        df: DataFrame to analyze.

    Returns:
        Dict mapping field names to lists of candidate column names.
    """
    candidates: dict[str, list[str]] = {
        "mouse": [],
        "timepoint": [],
        "xo_series": [],
        "last_filament": [],
        "sex": [],
        "group": [],
    }

    for col in df.columns:
        col_lower = str(col).lower()

        if "mouse" in col_lower or "animal" in col_lower or "subject" in col_lower or col_lower == "id":
            candidates["mouse"].append(col)
        if "time" in col_lower or "day" in col_lower or "point" in col_lower:
            candidates["timepoint"].append(col)
        if "series" in col_lower or "xo" in col_lower or "pattern" in col_lower:
            candidates["xo_series"].append(col)
        if "filament" in col_lower or "last" in col_lower:
            candidates["last_filament"].append(col)
        if "sex" in col_lower or "gender" in col_lower:
            candidates["sex"].append(col)
        if "group" in col_lower or "condition" in col_lower or "treatment" in col_lower:
            candidates["group"].append(col)

    return candidates


def detect_timepoint_type(values: pd.Series) -> str:
    """Detect whether timepoint values are numeric or categorical.

    Args:
        values: Series of timepoint values.

    Returns:
        'numeric' or 'categorical'.
    """
    try:
        pd.to_numeric(values.dropna())
        return "numeric"
    except (ValueError, TypeError):
        return "categorical"


def get_group_combinations(
    metadata_df: pd.DataFrame,
    group_cols: list[str],
    mouse_col: str = "mouse",
) -> pd.DataFrame:
    """Get unique group combinations and their sample sizes.

    Args:
        metadata_df: Metadata DataFrame.
        group_cols: List of column names that define experimental groups.
        mouse_col: Mouse ID column name.

    Returns:
        DataFrame with columns for each group factor plus 'n' (sample size).
    """
    if not group_cols:
        return pd.DataFrame({"n": [metadata_df[mouse_col].nunique()]})

    groups = (
        metadata_df.groupby(group_cols)[mouse_col]
        .nunique()
        .reset_index()
        .rename(columns={mouse_col: "n"})
    )
    return groups


def _reserved_data_columns(
    mouse_col: str,
    timepoint_col: str,
    series_col: str,
    filament_col: str,
) -> set[str]:
    """Column names that are never blocking or comparison factors."""
    return {
        mouse_col,
        timepoint_col,
        series_col,
        filament_col,
        "threshold_50",
    }


def detect_facet_factor_candidates(
    data_df: pd.DataFrame,
    mouse_col: str = "mouse",
    timepoint_col: str = "timepoint",
    series_col: str = "xo_series",
    filament_col: str = "last_filament",
) -> list[str]:
    """List data-file columns suitable as panel or pairing factors.

    A column qualifies if it is not a required mapping column and is not
    constant for every mouse (i.e. it distinguishes multiple observations
    per animal).

    Args:
        data_df: Raw or merged experimental data.
        mouse_col: Mouse ID column.
        timepoint_col: Timepoint column.
        series_col: XO series column.
        filament_col: Last filament column.

    Returns:
        Sorted list of candidate column names.
    """
    reserved = _reserved_data_columns(mouse_col, timepoint_col, series_col, filament_col)
    candidates: list[str] = []

    for col in data_df.columns:
        if col in reserved:
            continue
        per_mouse_nunique = data_df.groupby(mouse_col)[col].nunique(dropna=False)
        if (per_mouse_nunique > 1).any():
            candidates.append(col)

    return sorted(candidates)


def apply_facet_filters(
    df: pd.DataFrame,
    facet_filters: dict[str, str],
) -> pd.DataFrame:
    """Subset rows to one panel combination."""
    result = df.copy()
    for col, val in facet_filters.items():
        result = result[result[col].astype(str) == str(val)]
    return result


def resolve_facet_levels(
    df: pd.DataFrame,
    col: str,
    selected_values: list[str],
) -> list[str]:
    """Return facet levels for a column; empty selected_values means all levels."""
    if not selected_values:
        return sorted(df[col].dropna().astype(str).unique(), key=str)
    return [str(v) for v in selected_values]


def build_facet_slices(
    merged_df: pd.DataFrame,
    mouse_col: str,
    timepoint_col: str,
    timepoint_order: list[str],
    excluded_timepoints: list[str],
    facet_cols: Optional[list[str]] = None,
    facet_values: Optional[dict[str, list[str]]] = None,
) -> list[FacetSlice]:
    """Build one :class:`FacetSlice` per panel-factor combination.

    Args:
        merged_df: Full merged data with thresholds.
        mouse_col: Mouse ID column (unused; kept for API symmetry).
        timepoint_col: Timepoint column.
        timepoint_order: Ordered timepoint labels.
        excluded_timepoints: Timepoints to drop.
        facet_cols: Columns that split figures (Cartesian product).
        facet_values: Per-column selected levels; empty list = all levels.

    Returns:
        List of facet slices (one slice if no panel factors configured).
    """
    _ = mouse_col
    active_tp = get_active_timepoints(timepoint_order, excluded_timepoints)
    base = merged_df[merged_df[timepoint_col].astype(str).isin(active_tp)].copy()

    cols = facet_cols or []
    values = facet_values or {}

    if not cols:
        return [FacetSlice(filters={}, label="all", df=base)]

    level_lists: list[list[str]] = []
    for col in cols:
        if col not in base.columns:
            continue
        level_lists.append(resolve_facet_levels(base, col, values.get(col, [])))

    if not level_lists:
        return [FacetSlice(filters={}, label="all", df=base)]

    slices: list[FacetSlice] = []
    for combo in product(*level_lists):
        filters = {col: val for col, val in zip(cols, combo)}
        sdf = apply_facet_filters(base, filters)
        label = " · ".join(f"{k}={v}" for k, v in filters.items())
        slices.append(FacetSlice(filters=filters, label=label, df=sdf))
    return slices


def validate_facet_slices(
    slices: list[FacetSlice],
    mouse_col: str,
    timepoint_col: str,
    active_timepoints: list[str],
    pre_label: str,
    post_label: str,
    compare_cols: list[str],
    facet_cols: list[str],
    factor_candidates: list[str],
) -> tuple[list[str], list[str]]:
    """Validate every facet slice for pre-post structure."""
    errors: list[str] = []
    warnings: list[str] = []

    for sl in slices:
        if sl.df.empty:
            errors.append(f"{sl.label}: no data in this panel.")
            continue
        pairing_cols = get_pairing_columns(
            sl.df,
            mouse_col,
            timepoint_col,
            pre_label,
            post_label,
            compare_cols,
            facet_cols,
            factor_candidates,
        )
        slice_errors, slice_warnings = validate_pre_post_design(
            sl.df,
            mouse_col,
            timepoint_col,
            active_timepoints,
            pre_label=pre_label,
            post_label=post_label,
            pairing_cols=pairing_cols,
            group_cols=compare_cols,
            facet_cols=facet_cols,
            factor_candidates=factor_candidates,
        )
        for err in slice_errors:
            errors.append(f"{sl.label}: {err}")
        for warn in slice_warnings:
            warnings.append(f"{sl.label}: {warn}")

    return errors, warnings


def validate_facet_selection(
    facet_cols: list[str],
    facet_values: dict[str, list[str]],
    compare_cols: list[str],
) -> list[str]:
    """Validate panel-factor and compare-factor UI selections."""
    errors: list[str] = []
    overlap = set(facet_cols) & set(compare_cols)
    if overlap:
        errors.append(
            f"Column(s) {', '.join(sorted(overlap))} cannot be both a panel factor "
            f"and a compare factor. Use panel factors to split figures; compare "
            f"factors for sal vs DCZ etc. within each figure."
        )
    for col in facet_cols:
        selected = facet_values.get(col)
        if selected is not None and len(selected) == 0 and col in facet_values:
            pass  # empty list = all values, valid
    return errors


def get_pairing_columns(
    df: pd.DataFrame,
    mouse_col: str,
    timepoint_col: str,
    pre_label: str,
    post_label: str,
    group_cols: list[str],
    facet_cols: list[str],
    factor_candidates: list[str],
) -> list[str]:
    """Columns that define separate pre/post pairs within each mouse.

    Used when a mouse has multiple pre and post rows in one panel
    (e.g. both sal and DCZ under ``treatment=acute``). Such columns belong
    in compare factors, not panel factors.

    Args:
        df: Panel DataFrame.
        mouse_col: Mouse ID column.
        timepoint_col: Timepoint column.
        pre_label: Pre timepoint label.
        post_label: Post timepoint label.
        group_cols: Selected compare-within-figure columns.
        facet_cols: Columns used to split figures (fixed per panel).
        factor_candidates: Data-file factor candidates.

    Returns:
        Sorted list of pairing column names.
    """
    pairing: list[str] = []
    candidate_set = set(factor_candidates)
    facet_set = set(facet_cols)

    for col in group_cols:
        if col in facet_set:
            continue
        if col not in df.columns or col not in candidate_set:
            continue
        if _column_pairs_pre_post(df, mouse_col, timepoint_col, pre_label, post_label, [col]):
            pairing.append(col)

    if pairing:
        return sorted(pairing)

    for col in factor_candidates:
        if col in facet_set:
            continue
        if col not in df.columns:
            continue
        if _column_pairs_pre_post(df, mouse_col, timepoint_col, pre_label, post_label, [col]):
            pairing.append(col)

    return sorted(pairing)


def _column_pairs_pre_post(
    df: pd.DataFrame,
    mouse_col: str,
    timepoint_col: str,
    pre_label: str,
    post_label: str,
    pairing_cols: list[str],
) -> bool:
    """Return True if grouping by mouse + pairing_cols yields 1 pre and 1 post each."""
    tp_str = df[timepoint_col].astype(str)
    df_pre = df[tp_str == str(pre_label)]
    df_post = df[tp_str == str(post_label)]
    group_cols = [mouse_col] + pairing_cols

    for _key, pre_grp in df_pre.groupby(group_cols, dropna=False):
        if len(pre_grp) != 1:
            return False
    for _key, post_grp in df_post.groupby(group_cols, dropna=False):
        if len(post_grp) != 1:
            return False

    mice = df[mouse_col].unique()
    if len(mice) == 0:
        return False
    n_pre = df_pre.groupby(group_cols, dropna=False).ngroups
    n_post = df_post.groupby(group_cols, dropna=False).ngroups
    return n_pre == n_post and n_pre >= len(mice)


def get_active_timepoints(
    timepoint_order: list[str],
    excluded_timepoints: list[str],
) -> list[str]:
    """Return timepoints that are not excluded, preserving order."""
    excluded = set(excluded_timepoints)
    return [tp for tp in timepoint_order if tp not in excluded]


def is_pre_post_design(
    timepoint_order: list[str],
    excluded_timepoints: list[str],
) -> bool:
    """True when the active design has at most two timepoints."""
    return len(get_active_timepoints(timepoint_order, excluded_timepoints)) <= 2


def infer_pre_post_labels(active_timepoints: list[str]) -> tuple[str, str]:
    """Guess pre and post labels from detected timepoint names.

    Prefers ``pre`` for pre and ``post`` over ``post_chronic`` for post.
    Falls back to first and last active timepoint.

    Args:
        active_timepoints: Non-excluded timepoint labels (ordered).

    Returns:
        Tuple of (pre_label, post_label).

    Raises:
        ValueError: If fewer than two timepoints.
    """
    if len(active_timepoints) < 2:
        raise ValueError("Need at least two timepoints to infer pre/post labels.")

    tp_strs = [str(tp) for tp in active_timepoints]
    tp_lower = {tp.lower(): tp for tp in tp_strs}

    pre_label = tp_lower.get("pre", tp_strs[0])

    post_label = None
    for preferred in ("post", "post_chronic"):
        if preferred in tp_lower:
            post_label = tp_lower[preferred]
            break
    if post_label is None:
        post_label = tp_strs[-1]

    return pre_label, post_label


def validate_pre_post_design(
    df: pd.DataFrame,
    mouse_col: str,
    timepoint_col: str,
    active_timepoints: list[str],
    pre_label: Optional[str] = None,
    post_label: Optional[str] = None,
    pairing_cols: Optional[list[str]] = None,
    group_cols: Optional[list[str]] = None,
    facet_cols: Optional[list[str]] = None,
    factor_candidates: Optional[list[str]] = None,
) -> tuple[list[str], list[str]]:
    """Validate factorial pre-post structure for one panel.

    Args:
        df: Filtered merged DataFrame for this panel.
        mouse_col: Mouse ID column.
        timepoint_col: Timepoint column.
        active_timepoints: Timepoints included in the analysis.
        pre_label: Expected pre timepoint (inferred if None).
        post_label: Expected post timepoint (inferred if None).
        pairing_cols: Columns splitting pre/post within mouse (inferred if None).
        group_cols: Compare-within-figure columns (for pairing inference).
        facet_cols: Panel columns fixed within this figure.
        factor_candidates: Data-file factor candidates (for pairing inference).

    Returns:
        Tuple of (errors, warnings). Empty errors means valid.
    """
    errors: list[str] = []
    warnings: list[str] = []

    panel_cols = facet_cols or []
    candidates = factor_candidates or []

    if len(active_timepoints) != 2:
        errors.append(
            f"Pre-post analysis requires exactly 2 active timepoints; "
            f"found {len(active_timepoints)}: {active_timepoints}"
        )
        return errors, warnings

    if pre_label is None or post_label is None:
        pre_label, post_label = infer_pre_post_labels(active_timepoints)

    if pairing_cols is None:
        pairing_cols = get_pairing_columns(
            df,
            mouse_col,
            timepoint_col,
            pre_label,
            post_label,
            group_cols or [],
            panel_cols,
            candidates,
        )

    tp_col_str = df[timepoint_col].astype(str)
    df_pre = df[tp_col_str == str(pre_label)]
    df_post = df[tp_col_str == str(post_label)]

    if df_pre.empty:
        errors.append(f"No rows found for pre timepoint '{pre_label}'.")
    if df_post.empty:
        errors.append(f"No rows found for post timepoint '{post_label}'.")

    if errors:
        return errors, warnings

    group_keys = [mouse_col] + list(pairing_cols)
    problem_units: list[str] = []

    pre_counts = df_pre.groupby(group_keys, dropna=False).size()
    post_counts = df_post.groupby(group_keys, dropna=False).size()
    all_keys = pre_counts.index.union(post_counts.index)

    for key in all_keys:
        n_pre = int(pre_counts.get(key, 0))
        n_post = int(post_counts.get(key, 0))
        if n_pre != 1 or n_post != 1:
            if pairing_cols:
                label = ", ".join(
                    f"{col}={key[i + 1] if isinstance(key, tuple) else key}"
                    for i, col in enumerate(pairing_cols)
                )
                problem_units.append(f"mouse {key[0] if isinstance(key, tuple) else key} ({label}: pre={n_pre}, post={n_post})")
            else:
                mouse = key[0] if isinstance(key, tuple) else key
                problem_units.append(f"{mouse} (pre={n_pre}, post={n_post})")

    if problem_units:
        shown = ", ".join(problem_units[:6])
        if len(problem_units) > 6:
            shown += f", ... (+{len(problem_units) - 6} more)"
        hint = ""
        if not pairing_cols:
            hint = (
                " If each animal has multiple drugs/treatments, add the varying column "
                "(e.g. drug) under Compare within each figure — not under Separate figures."
            )
        errors.append(
            "Each mouse must have exactly one pre and one post row per experimental "
            f"unit.{hint} Problems: {shown}"
        )
    elif pairing_cols:
        warnings.append(
            f"Paired pre/post computed separately for each level of: "
            f"{', '.join(pairing_cols)}."
        )

    return errors, warnings


def build_analysis_dataframe(
    merged_df: pd.DataFrame,
    mouse_col: str,
    timepoint_col: str,
    timepoint_order: list[str],
    excluded_timepoints: list[str],
) -> pd.DataFrame:
    """Apply timepoint exclusion for plot/stats base data.

    Panel filtering for pre-post designs uses :func:`build_facet_slices`.

    Args:
        merged_df: Full merged data with thresholds.
        mouse_col: Mouse ID column (unused; kept for API symmetry).
        timepoint_col: Timepoint column.
        timepoint_order: Ordered timepoint labels.
        excluded_timepoints: Timepoints to drop.

    Returns:
        Filtered DataFrame with excluded timepoints removed.
    """
    _ = mouse_col
    active_tp = get_active_timepoints(timepoint_order, excluded_timepoints)
    return merged_df[
        merged_df[timepoint_col].astype(str).isin(active_tp)
    ].copy()


def get_comparison_group_candidates(
    metadata_df: Optional[pd.DataFrame],
    data_df: pd.DataFrame,
    mouse_col: str,
    sex_col: str,
    meta_mouse_col: str,
    timepoint_col: str,
    series_col: str,
    filament_col: str,
    facet_cols: Optional[list[str]] = None,
) -> list[str]:
    """Columns eligible as compare-within-figure groups (metadata + data file).

    Excludes reserved columns, ``accept``, and columns used as panel factors.
    """
    reserved = _reserved_data_columns(mouse_col, timepoint_col, series_col, filament_col)
    reserved |= {sex_col, meta_mouse_col, "accept", "include_in_analysis", "accepted"}
    panel = set(facet_cols or [])

    candidates: list[str] = []
    seen: set[str] = set()

    for source in (metadata_df, data_df):
        if source is None:
            continue
        for col in source.columns:
            if col in reserved or col in panel or col in seen:
                continue
            seen.add(col)
            candidates.append(col)

    return candidates
