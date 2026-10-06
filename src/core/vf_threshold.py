"""50% withdrawal threshold computation using the Dixon up-down method.

Refactored from legacy/read_vf_analysis_file.py. Removes hardcoded paths,
adds type hints, and provides a clean API for threshold calculation.

The threshold is computed as:
    threshold = 10^(Xf + k * delta) / 10000
Where:
    Xf = log value of the final filament
    k  = tabulated statistic based on the x/o series pattern
    delta = mean log interval between filaments (profile-specific)
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd


# Default mean log interval between filaments
DELTA_INTERVAL: float = 0.441428571

# Default starting filament number
INITIAL_FILAMENT: int = 4

FILAMENT_SETS = ("legacy", "rat", "custom")
RAT_REFERENCE = Path(__file__).resolve().parents[2] / "data" / "filaments_rat.csv"
K_REFERENCE = Path(__file__).resolve().parents[2] / "data" / "dixon_k.csv"


def spacing_warning(filament_info: pd.DataFrame, log_column: str = "Log_new") -> str:
    """Describe ladders outside Dixon's approximate equal-step condition."""
    intervals = np.diff(filament_info[log_column].to_numpy(dtype=float))
    mean = float(intervals.mean())
    deviation = float(np.max(np.abs(intervals / mean - 1)))
    if deviation > 0.5 + 1e-12:
        return (f"Uneven log spacing: an interval differs from the mean by {deviation:.1%} "
                "(more than 50%). The mean-spacing Dixon estimate may be unreliable. "
                "Review the experimental ladder/method; see docs/references.md.")
    return ""


def load_k_statistics() -> dict[str, float]:
    """Species-independent Dixon coefficients, transcribed from the legacy table."""
    table = pd.read_csv(K_REFERENCE)
    return dict(zip(table["OBSERVATION"], table["STATISTIC"]))


def load_filament_set(filepath: Union[str, Path]) -> pd.DataFrame:
    """Read a CSV containing the complete ordered ladder used in an experiment.

    IDs are positive integers, unique but not necessarily consecutive. Forces
    must increase in row order. Optional Log values are handle codes, whereas
    Log_new is calculated from Force (g) without legacy rounding.
    """
    info = pd.read_csv(filepath)
    required = {"Filament_number", "Force (g)"}
    if not required.issubset(info.columns):
        raise ValueError(f"Filament CSV must contain columns: {sorted(required)}")
    if len(info) < 2:
        raise ValueError("A filament ladder must contain at least two filaments.")
    ids = pd.to_numeric(info["Filament_number"], errors="raise")
    if (not np.isfinite(ids).all() or (ids <= 0).any()
            or (ids != np.floor(ids)).any() or ids.duplicated().any()):
        raise ValueError("Filament numbers must be unique positive integers.")
    info["Filament_number"] = ids.astype(int)
    forces = pd.to_numeric(info["Force (g)"], errors="raise")
    if (not np.isfinite(forces).all() or (forces <= 0).any()
            or (np.diff(forces) <= 0).any()):
        raise ValueError("Forces must be finite, positive, and increasing in CSV row order.")
    info["Force (g)"] = forces
    info["Log_new"] = np.log10(forces * 10000)
    if "Log" not in info:
        info["Log"] = info["Log_new"]
    logs = pd.to_numeric(info["Log"], errors="raise")
    if not np.isfinite(logs).all() or (np.diff(logs) <= 0).any():
        raise ValueError("Log values must be finite and increasing in CSV row order.")
    info["Log"] = logs
    info.attrs["delta_mode"] = "mean"
    return info


def get_delta(filament_info: pd.DataFrame, log_column: str = "Log_new") -> float:
    """Keep the historical interval unless an explicit ladder was loaded."""
    if filament_info.attrs.get("delta_mode") != "mean":
        return DELTA_INTERVAL
    if log_column not in filament_info:
        raise ValueError(f"Log column '{log_column}' not found in filament info.")
    intervals = np.diff(filament_info[log_column].to_numpy(dtype=float))
    if not len(intervals) or not np.isfinite(intervals).all() or (intervals <= 0).any():
        raise ValueError("Filament logs must be finite and strictly increasing.")
    return float(intervals.mean())


def calculate_log(force_grams: float) -> float:
    """Compute the log value from force in grams.

    Formula: log10(10 * force_in_grams * 1000)

    Args:
        force_grams: Force value in grams.

    Returns:
        The computed log value.
    """
    return float(np.log10(10 * force_grams * 1000))


def load_filament_reference(
    filepath: Union[str, Path, None] = None,
    sheet_name: str = "values_analysis",
    *,
    filament_set: str = "legacy",
    custom_filaments: Union[str, Path, None] = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Load filament reference data and series statistics from the VF Calculator file.

    Args:
        filepath: Mouse master path; ignored for rat/custom (no Excel needed).
        sheet_name: Name of the sheet containing values_analysis data.
        filament_set: 'legacy' (unchanged workbook), 'rat', or 'custom'.
        custom_filaments: CSV ladder required for 'custom'; rat/custom k values
            come from the standalone, species-independent dixon_k.csv.

    Returns:
        Tuple of (filament_info DataFrame, series_statistics dict).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing.
    """
    if filament_set not in FILAMENT_SETS:
        raise ValueError(f"Unknown filament set: {filament_set}")
    if filament_set == "custom" and not custom_filaments:
        raise ValueError("Custom filament set requires a filament CSV path.")
    if filament_set != "custom" and custom_filaments:
        raise ValueError("A custom filament CSV can only be used with the custom set.")
    if filament_set != "legacy":
        info = load_filament_set(RAT_REFERENCE if filament_set == "rat" else custom_filaments)
        info.attrs["filament_set"] = filament_set
        return info, load_k_statistics()
    if filepath is None:
        filepath = Path(__file__).resolve().parents[2] / "data/VF_Calculator_Up-down.xlsx"
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Filament reference file not found: {filepath}")

    # Load observation/statistic lookup table (columns A:B)
    df_obs_statistics = pd.read_excel(
        filepath, engine="openpyxl", sheet_name=sheet_name, usecols="A:B"
    )

    required_obs_cols = {"OBSERVATION", "STATISTIC"}
    if not required_obs_cols.issubset(df_obs_statistics.columns):
        raise ValueError(
            f"Sheet '{sheet_name}' must contain columns: {required_obs_cols}. "
            f"Found: {set(df_obs_statistics.columns)}"
        )

    observations = df_obs_statistics["OBSERVATION"].tolist()
    statistics = df_obs_statistics["STATISTIC"].tolist()
    dict_obs_stat: dict[str, float] = dict(zip(observations, statistics))

    # Load filament information (columns G:K, 8 rows of filament data)
    df_filament_info = pd.read_excel(
        filepath, engine="openpyxl", sheet_name=sheet_name, usecols="G:K", nrows=8
    )

    # Rename the duplicate "Number" column
    if "Number.1" in df_filament_info.columns:
        df_filament_info.rename(columns={"Number.1": "Filament_number"}, inplace=True)

    if "Force (g)" not in df_filament_info.columns:
        raise ValueError(
            f"Sheet '{sheet_name}' must contain 'Force (g)' column in the filament info section."
        )

    # Compute correct log values from force
    forces = df_filament_info["Force (g)"].values
    df_filament_info["Log_new"] = [round(calculate_log(f), 3) for f in forces]

    return df_filament_info, dict_obs_stat


def compute_50_threshold(
    series: str,
    final_filament: int,
    filament_info: pd.DataFrame,
    series_statistics: dict[str, float],
    log_column: str = "Log_new",
    delta: float | None = None,
) -> float:
    """Compute the 50% withdrawal threshold for a single observation.

    Args:
        series: String of x's and o's representing the response pattern (e.g., 'oxoxox').
        final_filament: Filament number at the end of the series.
        filament_info: DataFrame with filament reference data (must have 'Filament_number'
            and the specified log_column).
        series_statistics: Dict mapping uppercase series patterns to k statistics.
        log_column: Which log column to use ('Log_new' or 'Log').
        delta: Override the mean log interval. None selects the loaded ladder's
            mean interval, or the historical constant for legacy inputs.

    Returns:
        The 50% withdrawal threshold in grams, or NaN if series is invalid.
    """
    if delta is None:
        delta = get_delta(filament_info, log_column)
    if filament_info.attrs.get("filament_set") == "rat" and log_column != "Log_new":
        raise ValueError("Rat thresholds use Log_new calculated from force; no rat master workbook is used.")
    if not np.isfinite(delta) or delta <= 0:
        raise ValueError("Delta must be finite and positive.")
    if not isinstance(series, str) or len(series) == 0:
        return np.nan

    series_lower = series.lower()

    # Validate series characters
    if not all(c in ("x", "o") for c in series_lower):
        return np.nan

    # Look up the series statistic (k value)
    series_upper = series_lower.upper()
    if series_upper not in series_statistics:
        return np.nan

    k = series_statistics[series_upper]

    # Look up the log value of the final filament
    filament_row = filament_info[filament_info["Filament_number"] == final_filament]
    if filament_row.empty:
        return np.nan
    if log_column not in filament_row.columns:
        raise ValueError(
            f"Log column '{log_column}' not found in filament info. "
            f"Available columns: {list(filament_info.columns)}"
        )

    xf = filament_row[log_column].values[0]

    # Compute threshold: 10^(Xf + k * delta) / 10000
    threshold_50 = (10 ** (xf + k * delta)) / 10000

    return float(threshold_50)


def compute_thresholds_batch(
    df: pd.DataFrame,
    filament_info: pd.DataFrame,
    series_statistics: dict[str, float],
    series_col: str = "xo_series",
    filament_col: str = "last_filament",
    log_column: str = "Log_new",
    delta: float | None = None,
) -> pd.Series:
    """Compute 50% thresholds for all rows in a DataFrame.

    Args:
        df: DataFrame containing von Frey data.
        filament_info: Filament reference DataFrame.
        series_statistics: Series pattern to k-value mapping.
        series_col: Column name containing xo series strings.
        filament_col: Column name containing last filament numbers.
        log_column: Which log column to use.
        delta: Optional override; otherwise resolved from the filament set.

    Returns:
        A pandas Series of threshold values aligned with df's index.
    """
    if delta is None:
        delta = get_delta(filament_info, log_column)
    if not np.isfinite(delta) or delta <= 0:
        raise ValueError("Delta must be finite and positive.")
    return df.apply(
        lambda row: compute_50_threshold(
            series=row[series_col],
            final_filament=row[filament_col],
            filament_info=filament_info,
            series_statistics=series_statistics,
            log_column=log_column,
            delta=delta,
        ),
        axis=1,
    )


BOUNDARY_POLICIES = ("flag", "endpoints", "exclude")


def compute_threshold_report(
    df: pd.DataFrame,
    filament_info: pd.DataFrame,
    series_statistics: dict[str, float],
    series_col: str = "xo_series",
    filament_col: str = "last_filament",
    log_column: str = "Log_new",
    boundary_policy: str = "endpoints",
) -> pd.DataFrame:
    """Calculate estimates and preserve boundary/invalid observations explicitly.

    A uniform response run ending at its directional endpoint is a boundary
    observation, not a Dixon point estimate. 'endpoints' is an explicit numerical
    substitution; 'flag' and 'exclude' retain NaN but distinguish user intent.
    Mixed-response estimates outside the ladder are reported without clamping.
    This does not validate a study's starting filament or stopping rule.
    """
    if boundary_policy not in BOUNDARY_POLICIES:
        raise ValueError(f"Unknown boundary policy: {boundary_policy}")
    result = df.copy()
    result["threshold_50"] = compute_thresholds_batch(
        df, filament_info, series_statistics, series_col, filament_col, log_column
    )
    ids = filament_info["Filament_number"].tolist()
    low = float(10 ** filament_info[log_column].iloc[0] / 10000)
    high = float(10 ** filament_info[log_column].iloc[-1] / 10000)
    statuses, limits, values = [], [], []
    for series, fid, value in zip(df[series_col], df[filament_col], result["threshold_50"]):
        status, limit = "estimated", np.nan
        if pd.isna(fid) or fid not in ids:
            status = "unknown_filament"
        elif not isinstance(series, str) or not series or set(series.upper()) - set("XO"):
            status = "invalid_series"
        elif len(set(series.upper())) == 1:
            if len(series) > len(ids):
                status = "invalid_boundary_history"
            elif series.upper()[0] == "X" and fid == ids[0]:
                status, limit = "below_range", low
            elif series.upper()[0] == "O" and fid == ids[-1]:
                status, limit = "above_range", high
            else:
                status = "incomplete_no_reversal"
            value = limit if np.isfinite(limit) and boundary_policy == "endpoints" else np.nan
        elif pd.isna(value):
            status = "unsupported_pattern"
        elif value < low:
            status = "estimate_below_range"
        elif value > high:
            status = "estimate_above_range"
        statuses.append(status)
        limits.append(limit)
        values.append(value)
    result["threshold_50"] = values
    result["vf_status"] = statuses
    result["vf_boundary_limit_g"] = limits
    result["vf_boundary_policy"] = boundary_policy
    result["vf_filament_set"] = filament_info.attrs.get("filament_set", "legacy")
    result["vf_log_column"] = log_column
    result["vf_delta"] = get_delta(filament_info, log_column)
    return result


def boundary_summary(df: pd.DataFrame) -> str:
    """Human-readable accounting suitable for plots, logs, and statistics."""
    if "vf_status" not in df:
        return ""
    counts = df["vf_status"].value_counts()
    lower, upper = int(counts.get("below_range", 0)), int(counts.get("above_range", 0))
    invalid = int(df["vf_status"].isin([
        "invalid_series", "unknown_filament", "invalid_boundary_history",
        "incomplete_no_reversal", "unsupported_pattern",
    ]).sum())
    outside = int(df["vf_status"].isin(["estimate_below_range", "estimate_above_range"]).sum())
    if not (lower or upper or invalid or outside):
        return ""
    policy = ", ".join(sorted(df["vf_boundary_policy"].dropna().unique()))
    return (f"Boundary observations: {lower} below / {upper} above range; policy: {policy}. "
            f"Invalid/incomplete: {invalid}; outside-range estimates (not clamped): {outside}.")


def unresolved_boundaries(df: pd.DataFrame) -> bool:
    return bool("vf_status" in df and (
        df["vf_status"].isin(["below_range", "above_range"])
        & df["vf_boundary_policy"].eq("flag")
    ).any())
