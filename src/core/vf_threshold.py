"""50% withdrawal threshold computation using the Dixon up-down method.

Refactored from legacy/read_vf_analysis_file.py. Removes hardcoded paths,
adds type hints, and provides a clean API for threshold calculation.

The threshold is computed as:
    threshold = 10^(Xf + k * delta) / 10000
Where:
    Xf = log value of the final filament
    k  = tabulated statistic based on the x/o series pattern
    delta = mean log interval between filaments (0.441428571)
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

# Series meaning: x = withdraw (step down), o = no withdraw (step up)
SERIES_MEANING: dict[str, int] = {"x": -1, "o": 1}


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
    filepath: Union[str, Path],
    sheet_name: str = "values_analysis",
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Load filament reference data and series statistics from the VF Calculator file.

    Args:
        filepath: Path to VF_Calculator_Up-down.xlsx.
        sheet_name: Name of the sheet containing values_analysis data.

    Returns:
        Tuple of (filament_info DataFrame, series_statistics dict).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing.
    """
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
    delta: float = DELTA_INTERVAL,
    initial_filament: int = INITIAL_FILAMENT,
) -> float:
    """Compute the 50% withdrawal threshold for a single observation.

    Args:
        series: String of x's and o's representing the response pattern (e.g., 'oxoxox').
        final_filament: Filament number at the end of the series.
        filament_info: DataFrame with filament reference data (must have 'Filament_number'
            and the specified log_column).
        series_statistics: Dict mapping uppercase series patterns to k statistics.
        log_column: Which log column to use ('Log_new' or 'Log').
        delta: Mean log interval between filaments.
        initial_filament: Starting filament number.

    Returns:
        The 50% withdrawal threshold in grams, or NaN if series is invalid.
    """
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
) -> pd.Series:
    """Compute 50% thresholds for all rows in a DataFrame.

    Args:
        df: DataFrame containing von Frey data.
        filament_info: Filament reference DataFrame.
        series_statistics: Series pattern to k-value mapping.
        series_col: Column name containing xo series strings.
        filament_col: Column name containing last filament numbers.
        log_column: Which log column to use.

    Returns:
        A pandas Series of threshold values aligned with df's index.
    """
    return df.apply(
        lambda row: compute_50_threshold(
            series=row[series_col],
            final_filament=row[filament_col],
            filament_info=filament_info,
            series_statistics=series_statistics,
            log_column=log_column,
        ),
        axis=1,
    )
