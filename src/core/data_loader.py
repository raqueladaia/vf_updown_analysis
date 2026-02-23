"""Data loading and validation for von Frey up-down analysis.

Handles loading experimental data files (Excel/CSV) and metadata files,
validates required columns, merges metadata into data, and provides
clear error messages for common issues.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd


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
    gender_col: str = "gender",
    meta_mouse_col: Optional[str] = None,
) -> list[str]:
    """Validate that required columns exist in the metadata DataFrame.

    Args:
        df: The metadata DataFrame to validate.
        mouse_col: Mouse ID column name in the data file (used if meta_mouse_col is None).
        gender_col: Expected gender column name.
        meta_mouse_col: Mouse ID column name in the metadata file.
            If None, falls back to mouse_col.

    Returns:
        List of warning/error messages.
    """
    errors: list[str] = []
    effective_mouse_col = meta_mouse_col if meta_mouse_col is not None else mouse_col

    if effective_mouse_col not in df.columns:
        errors.append(f"Missing required column '{effective_mouse_col}' in metadata")

    if gender_col not in df.columns:
        errors.append(f"Missing required column '{gender_col}' in metadata")
    elif gender_col in df.columns:
        valid_genders = {"male", "female"}
        actual = set(df[gender_col].dropna().str.lower().unique())
        invalid = actual - valid_genders
        if invalid:
            errors.append(f"Invalid gender values: {invalid}. Expected 'male' or 'female'.")

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
            "These animals will have missing group/gender info."
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
    gender_col: str = "gender",
    meta_mouse_col: Optional[str] = None,
) -> pd.DataFrame:
    """Merge metadata columns into the data DataFrame.

    Args:
        data_df: The experimental data DataFrame.
        metadata_df: The metadata DataFrame.
        mouse_col: Column name for mouse IDs in the data file (merge key).
        group_cols: List of group-defining column names from metadata to merge.
            If None, merges all metadata columns except the mouse column.
        gender_col: Gender column name.
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
        cols_to_merge = [mouse_col] + [gender_col] + [c for c in group_cols if c != gender_col]
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
        "gender": [],
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
        if "gender" in col_lower or "sex" in col_lower:
            candidates["gender"].append(col)
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
