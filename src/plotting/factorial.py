"""Factorial plots for few-timepoint von Frey designs (pre-post).

Provides:
- Paired line plots (lines connecting each animal's pre -> post)
- Delta plots (strip/box plot of change scores per condition)
"""

from __future__ import annotations

from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from ..core.statistics import PairwiseResult
from .plot_utils import (
    DEFAULT_COLORS,
    DEFAULT_SEX_LINESTYLES,
    DEFAULT_SEX_MARKERS,
    add_significance_annotation,
    apply_publication_style,
    despine,
    format_log_yaxis,
)


def plot_paired_lines(
    df: pd.DataFrame,
    dependent_var: str = "threshold_50",
    timepoint_col: str = "timepoint",
    subject_col: str = "mouse",
    group_col: str = "group",
    sex_col: str = "sex",
    pre_label: str = "pre",
    post_label: str = "post_chronic",
    colors: Optional[dict[str, str]] = None,
    sex_linestyles: Optional[dict[str, str]] = None,
    show_sex_encoding: bool = True,
    alpha_by_group: Optional[dict[str, float]] = None,
    y_min: float = 0.01,
    y_max: float = 10.0,
    figsize: tuple[float, float] = (4.0, 4.0),
    x_label: str = "",
    y_label: str = "50% threshold (g)",
    title: str = "",
    use_log_scale: bool = True,
    fig: Optional[Figure] = None,
    ax: Optional[matplotlib.axes.Axes] = None,
) -> tuple[Figure, matplotlib.axes.Axes]:
    """Create a paired line plot connecting each animal's pre to post value.

    Animals within the same group share a color; lines connect paired observations.
    All compared conditions share the same pre and post x positions.

    Args:
        df: DataFrame with pre and post data for each animal.
        dependent_var: Column with threshold values.
        timepoint_col: Column with timepoint labels.
        subject_col: Column with subject/mouse IDs.
        group_col: Column defining groups (for coloring).
        sex_col: Column with sex for line style (solid male, dotted female).
        pre_label: Label for pre-intervention timepoint.
        post_label: Label for post-intervention timepoint.
        colors: Dict mapping group names to colors.
        sex_linestyles: Dict mapping sex to line styles (solid male, dotted female).
        show_sex_encoding: If True, distinguish sex by line style on individual traces.
        alpha_by_group: Dict mapping group names to alpha values.
        y_min: Y-axis min.
        y_max: Y-axis max.
        figsize: Figure size.
        x_label: X-axis label.
        y_label: Y-axis label.
        title: Figure title.
        use_log_scale: Whether to use log y-axis.
        fig: Existing figure.
        ax: Existing axes.

    Returns:
        Tuple of (Figure, Axes).
    """
    apply_publication_style()

    if colors is None:
        colors = DEFAULT_COLORS
    if sex_linestyles is None:
        sex_linestyles = DEFAULT_SEX_LINESTYLES
    if alpha_by_group is None:
        alpha_by_group = {}

    if fig is None or ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)

    groups = df[group_col].unique()

    # Shared pre/post x for all compared conditions (color encodes group)
    x_pre = 0.0
    x_post = 1.0

    # Plot individual paired lines
    subjects = df[subject_col].unique()
    for subject in subjects:
        df_subj = df[df[subject_col] == subject]

        pre_row = df_subj[df_subj[timepoint_col] == pre_label]
        post_row = df_subj[df_subj[timepoint_col] == post_label]

        if pre_row.empty or post_row.empty:
            continue

        group = str(pre_row[group_col].values[0])
        color = colors.get(group, "gray")
        alpha = alpha_by_group.get(group, 0.8)

        pre_val = pre_row[dependent_var].values[0]
        post_val = post_row[dependent_var].values[0]

        sex = "male"
        if sex_col in df_subj.columns:
            sexes = df_subj[sex_col].dropna().unique()
            if len(sexes) > 0:
                sex = str(sexes[0]).lower()
        linestyle = sex_linestyles.get(sex, "-") if show_sex_encoding else "-"

        ax.plot(
            [x_pre, x_post],
            [pre_val, post_val],
            color=color,
            alpha=alpha * 0.6,
            linewidth=1,
            linestyle=linestyle,
            zorder=1,
        )

    # Plot group means: thick pre→post line plus SEM error bars at each timepoint
    for group in groups:
        group_str = str(group)
        color = colors.get(group_str, "gray")
        df_group = df[df[group_col] == group]

        pre_vals = df_group[df_group[timepoint_col] == pre_label][dependent_var].dropna()
        post_vals = df_group[df_group[timepoint_col] == post_label][dependent_var].dropna()
        if pre_vals.empty or post_vals.empty:
            continue

        mean_pre = pre_vals.mean()
        mean_post = post_vals.mean()
        sem_pre = pre_vals.sem()
        sem_post = post_vals.sem()

        ax.plot(
            [x_pre, x_post],
            [mean_pre, mean_post],
            color=color,
            linewidth=2.5,
            zorder=3,
            label=group_str,
        )
        ax.errorbar(
            x_pre,
            mean_pre,
            yerr=sem_pre,
            fmt="s",
            color=color,
            markersize=8,
            capsize=4,
            linewidth=1.5,
            zorder=4,
            markeredgecolor="black",
            markeredgewidth=0.5,
        )
        ax.errorbar(
            x_post,
            mean_post,
            yerr=sem_post,
            fmt="s",
            color=color,
            markersize=8,
            capsize=4,
            linewidth=1.5,
            zorder=4,
            markeredgecolor="black",
            markeredgewidth=0.5,
        )

    ax.set_xticks([x_pre, x_post])
    ax.set_xticklabels([pre_label, post_label], rotation=0)

    if len(groups) > 1:
        ax.legend(loc="best", frameon=False)

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
        fig.suptitle(title)

    if use_log_scale:
        format_log_yaxis(ax, y_min, y_max)

    despine(ax)
    fig.tight_layout()
    return fig, ax


def plot_delta(
    delta_df: pd.DataFrame,
    delta_col: str = "delta",
    group_col: str = "group",
    sex_col: str = "sex",
    colors: Optional[dict[str, str]] = None,
    sex_markers: Optional[dict[str, str]] = None,
    figsize: tuple[float, float] = (4.0, 4.0),
    x_label: str = "",
    y_label: str = "Change in threshold (g)",
    title: str = "",
    pairwise_results: Optional[list[PairwiseResult]] = None,
    show_p_values: bool = True,
    fig: Optional[Figure] = None,
    ax: Optional[matplotlib.axes.Axes] = None,
) -> tuple[Figure, matplotlib.axes.Axes]:
    """Create a delta (change score) strip plot.

    Shows individual delta values as strip plot with mean +/- SEM overlay.

    Args:
        delta_df: DataFrame with delta scores and group info.
        delta_col: Column containing delta scores.
        group_col: Column defining groups.
        sex_col: Column with sex for marker shape.
        colors: Dict mapping group names to colors.
        sex_markers: Dict mapping sex to marker shapes.
        figsize: Figure size.
        x_label: X-axis label.
        y_label: Y-axis label.
        title: Figure title.
        pairwise_results: Optional pairwise results for significance annotation.
        show_p_values: Whether to show p-values.
        fig: Existing figure.
        ax: Existing axes.

    Returns:
        Tuple of (Figure, Axes).
    """
    apply_publication_style()

    if colors is None:
        colors = DEFAULT_COLORS
    if sex_markers is None:
        sex_markers = DEFAULT_SEX_MARKERS

    if fig is None or ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)

    groups = delta_df[group_col].unique()
    x_positions = {str(g): i for i, g in enumerate(groups)}

    # Plot individual data points with jitter
    rng = np.random.default_rng(42)
    for group in groups:
        group_str = str(group)
        color = colors.get(group_str, "gray")
        df_group = delta_df[delta_df[group_col] == group]
        x_base = x_positions[group_str]

        for _, row in df_group.iterrows():
            jitter = rng.uniform(-0.15, 0.15)

            sex = "male"
            if sex_col in df_group.columns and pd.notna(row.get(sex_col)):
                sex = str(row[sex_col]).lower()
            marker = sex_markers.get(sex, "o")

            ax.scatter(x_base + jitter, row[delta_col], marker=marker,
                       color=color, edgecolor="none", alpha=0.7, s=40, zorder=2)

    # Plot mean +/- SEM bars
    for group in groups:
        group_str = str(group)
        color = colors.get(group_str, "gray")
        vals = delta_df[delta_df[group_col] == group][delta_col].dropna()
        x = x_positions[group_str]

        mean = vals.mean()
        sem = vals.sem()

        ax.errorbar(x, mean, yerr=sem, fmt="s", color=color,
                     markersize=8, capsize=5, linewidth=2, zorder=3,
                     markeredgecolor="black", markeredgewidth=0.5)

    # Zero line
    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)

    # Significance annotations
    if pairwise_results:
        y_data_max = delta_df[delta_col].max()
        y_top = y_data_max + abs(y_data_max) * 0.2

        for pw in pairwise_results:
            if pw.stars != "n.s.":
                x_a = x_positions.get(pw.group_a)
                x_b = x_positions.get(pw.group_b)
                if x_a is not None and x_b is not None:
                    x_mid = (x_a + x_b) / 2
                    add_significance_annotation(
                        ax, x_mid, y_top, pw.stars,
                        p_value=pw.p_adjusted if show_p_values else None,
                        show_p=show_p_values,
                    )
                    # Draw bracket
                    ax.plot([x_a, x_a, x_b, x_b],
                            [y_top * 0.95, y_top, y_top, y_top * 0.95],
                            color="black", linewidth=1)

    # Formatting
    ax.set_xticks(list(x_positions.values()))
    ax.set_xticklabels([str(g) for g in groups])
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
        fig.suptitle(title)

    despine(ax)
    fig.tight_layout()
    return fig, ax
