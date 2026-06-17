"""Shared plotting configuration for publication-ready figures.

Provides:
- Publication-standard rcParams (Arial 14pt, editable fonts for Illustrator)
- Axis formatting (log scale with ScalarFormatter, despine)
- Sex-specific marker/linestyle defaults
- Figure export helpers
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from matplotlib.figure import Figure


# ── Default visual config ────────────────────────────────────────────────

DEFAULT_COLORS: dict[str, str] = {
    "control": "gray",
    "experimental": "orange",
    "dark": "royalblue",
    "light": "orange",
}

DEFAULT_SEX_MARKERS: dict[str, str] = {
    "male": "o",
    "female": "^",
}

DEFAULT_SEX_LINESTYLES: dict[str, str] = {
    "male": "-",
    "female": ":",
}


def apply_publication_style() -> None:
    """Apply publication-ready matplotlib rcParams.

    Sets Arial font, size 14, editable font types for Adobe Illustrator,
    and clean seaborn whitegrid style.
    """
    plt.rcParams.update({
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 14,
        "axes.titlesize": 14,
        "axes.labelsize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 11,
    })
    sns.set_style("ticks")


def format_log_yaxis(
    ax: matplotlib.axes.Axes,
    y_min: float = 0.01,
    y_max: float = 10.0,
) -> None:
    """Format y-axis as log scale with scalar tick labels.

    Data is NOT transformed — only the axis scale is logarithmic.

    Args:
        ax: Matplotlib axes to format.
        y_min: Y-axis lower limit.
        y_max: Y-axis upper limit.
    """
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
    ax.yaxis.set_major_locator(ticker.LogLocator(base=10.0, numticks=15))
    ax.set_ylim([y_min, y_max])


def despine(ax: matplotlib.axes.Axes) -> None:
    """Remove top and right spines from axes.

    Args:
        ax: Matplotlib axes.
    """
    sns.despine(ax=ax)


def add_intervention_line(
    ax: matplotlib.axes.Axes,
    x_position: float,
    color: str = "black",
    linestyle: str = "--",
) -> None:
    """Add a vertical dashed line at the intervention timepoint.

    Args:
        ax: Matplotlib axes.
        x_position: X-axis position for the line.
        color: Line color.
        linestyle: Line style.
    """
    ax.axvline(x=x_position, color=color, linestyle=linestyle, linewidth=1, alpha=0.7)


def add_significance_annotation(
    ax: matplotlib.axes.Axes,
    x: float,
    y: float,
    stars: str,
    p_value: Optional[float] = None,
    show_p: bool = True,
) -> None:
    """Add significance stars and optional p-value text above a data point.

    Args:
        ax: Matplotlib axes.
        x: X position.
        y: Y position (top of annotation).
        stars: Significance stars string.
        p_value: Raw p-value to display.
        show_p: Whether to show the p-value text below stars.
    """
    ax.text(x, y, stars, ha="center", va="bottom", fontsize=12, fontweight="bold")
    if show_p and p_value is not None:
        p_text = f"p={p_value:.3f}" if p_value >= 0.001 else f"p<0.001"
        ax.text(x, y * 0.92, p_text, ha="center", va="top", fontsize=8)


def export_figure(
    fig: Figure,
    output_dir: Union[str, Path],
    filename_prefix: str,
    formats: Optional[list[str]] = None,
    dpi: int = 300,
) -> list[Path]:
    """Export figure in specified formats.

    Args:
        fig: Matplotlib figure to export.
        output_dir: Directory for output files.
        filename_prefix: Base filename (without extension).
        formats: List of formats ('pdf', 'png', 'svg'). Defaults to ['pdf'].
        dpi: DPI for raster formats.

    Returns:
        List of paths to exported files.
    """
    if formats is None:
        formats = ["pdf"]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    for fmt in formats:
        path = output_dir / f"{filename_prefix}.{fmt}"
        fig.savefig(path, format=fmt, dpi=dpi, bbox_inches="tight")
        exported.append(path)

    return exported
