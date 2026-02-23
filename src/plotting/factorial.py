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
    gender_col: str = "gender",
    pre_label: str = "pre",
    post_label: str = "post_chronic",
    colors: Optional[dict[str, str]] = None,
    sex_markers: Optional[dict[str, str]] = None,
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

    Args:
        df: DataFrame with pre and post data for each animal.
        dependent_var: Column with threshold values.
        timepoint_col: Column with timepoint labels.
        subject_col: Column with subject/mouse IDs.
        group_col: Column defining groups (for coloring).
        gender_col: Column with gender for marker shape.
        pre_label: Label for pre-intervention timepoint.
        post_label: Label for post-intervention timepoint.
        colors: Dict mapping group names to colors.
        sex_markers: Dict mapping gender to marker shapes.
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
    if sex_markers is None:
        sex_markers = DEFAULT_SEX_MARKERS
    if alpha_by_group is None:
        alpha_by_group = {}

    if fig is None or ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)

    groups = df[group_col].unique()

    # X positions: spread groups apart
    group_spacing = 0.4
    x_positions: dict[str, dict[str, float]] = {}
    for i, group in enumerate(groups):
        base_x = i * (2 + group_spacing)
        x_positions[str(group)] = {pre_label: base_x, post_label: base_x + 1}

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

        x_pre = x_positions[group][pre_label]
        x_post = x_positions[group][post_label]

        # Determine marker
        gender = "male"
        if gender_col in df_subj.columns:
            genders = df_subj[gender_col].dropna().unique()
            if len(genders) > 0:
                gender = str(genders[0]).lower()
        marker = sex_markers.get(gender, "o")

        ax.plot([x_pre, x_post], [pre_val, post_val],
                color=color, alpha=alpha * 0.6, linewidth=1, zorder=1)
        ax.scatter([x_pre], [pre_val], marker=marker, color=color,
                   edgecolor="none", alpha=alpha, s=40, zorder=2)
        ax.scatter([x_post], [post_val], marker=marker, color=color,
                   edgecolor="none", alpha=alpha, s=40, zorder=2)

    # Plot group means
    for group in groups:
        group_str = str(group)
        color = colors.get(group_str, "gray")
        df_group = df[df[group_col] == group]

        for tp_label in [pre_label, post_label]:
            vals = df_group[df_group[timepoint_col] == tp_label][dependent_var].dropna()
            x = x_positions[group_str][tp_label]
            mean = vals.mean()
            sem = vals.sem()
            ax.errorbar(x, mean, yerr=sem, fmt="s", color=color,
                        markersize=8, capsize=4, linewidth=2, zorder=3,
                        markeredgecolor="black", markeredgewidth=0.5)

    # X-axis formatting
    all_x_positions = []
    all_x_labels = []
    for group in groups:
        group_str = str(group)
        for tp_label in [pre_label, post_label]:
            all_x_positions.append(x_positions[group_str][tp_label])
            all_x_labels.append(f"{tp_label}")

    ax.set_xticks(all_x_positions)
    ax.set_xticklabels(all_x_labels, rotation=0)

    # Add group labels below
    for group in groups:
        group_str = str(group)
        mid_x = (x_positions[group_str][pre_label] + x_positions[group_str][post_label]) / 2
        ax.text(mid_x, -0.12, group_str, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=12, fontweight="bold")

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
    gender_col: str = "gender",
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
        gender_col: Column with gender for marker shape.
        colors: Dict mapping group names to colors.
        sex_markers: Dict mapping gender to marker shapes.
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

            gender = "male"
            if gender_col in df_group.columns and pd.notna(row.get(gender_col)):
                gender = str(row[gender_col]).lower()
            marker = sex_markers.get(gender, "o")

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
