"""Longitudinal line plots for multi-timepoint von Frey designs.

Produces individual animal traces (thin, transparent) overlaid with
group mean +/- SEM (thick), with sex-specific markers and linestyles.
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
    add_intervention_line,
    add_significance_annotation,
    apply_publication_style,
    despine,
    format_log_yaxis,
)


def plot_longitudinal(
    df: pd.DataFrame,
    dependent_var: str = "threshold_50",
    timepoint_col: str = "timepoint",
    group_col: str = "group",
    subject_col: str = "mouse",
    gender_col: str = "gender",
    colors: Optional[dict[str, str]] = None,
    sex_markers: Optional[dict[str, str]] = None,
    sex_linestyles: Optional[dict[str, str]] = None,
    individual_alpha: float = 0.15,
    intervention_x: Optional[float] = None,
    y_min: float = 0.01,
    y_max: float = 10.0,
    figsize: tuple[float, float] = (6.0, 4.0),
    x_label: str = "Timepoint (days)",
    y_label: str = "50% threshold (g)",
    title: str = "",
    pairwise_results: Optional[list[PairwiseResult]] = None,
    show_p_values: bool = True,
    use_log_scale: bool = True,
    fig: Optional[Figure] = None,
    ax: Optional[matplotlib.axes.Axes] = None,
    timepoint_order: Optional[list[str]] = None,
) -> tuple[Figure, matplotlib.axes.Axes]:
    """Create a longitudinal line plot.

    Individual animal traces (thin, semi-transparent) with group mean +/- SEM
    overlaid as thick lines with error bars.

    Args:
        df: DataFrame with columns for dependent_var, timepoint, group, subject, gender.
        dependent_var: Column with threshold values.
        timepoint_col: Column with timepoint values.
        group_col: Column with group labels.
        subject_col: Column with subject/mouse IDs.
        gender_col: Column with gender ('male'/'female').
        colors: Dict mapping group names to colors.
        sex_markers: Dict mapping gender to marker shapes.
        sex_linestyles: Dict mapping gender to line styles.
        individual_alpha: Alpha for individual traces.
        intervention_x: X-position for intervention vertical line (None to skip).
        y_min: Y-axis minimum.
        y_max: Y-axis maximum.
        figsize: Figure size in inches.
        x_label: X-axis label.
        y_label: Y-axis label.
        title: Plot title.
        pairwise_results: Optional list of pairwise comparisons to annotate.
        show_p_values: Whether to show p-values alongside stars.
        use_log_scale: Whether to use log scale on y-axis.
        fig: Existing figure to draw on.
        ax: Existing axes to draw on.
        timepoint_order: Optional list of timepoint labels in the desired display
            order.  When provided the x-axis will use this ordering instead of
            the default sorted order.  For numeric timepoints the actual values
            are used as tick positions (proportional spacing).  For categorical
            timepoints they are evenly spaced with these labels.

    Returns:
        Tuple of (Figure, Axes).
    """
    apply_publication_style()

    if colors is None:
        colors = DEFAULT_COLORS
    if sex_markers is None:
        sex_markers = DEFAULT_SEX_MARKERS
    if sex_linestyles is None:
        sex_linestyles = DEFAULT_SEX_LINESTYLES

    if fig is None or ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)

    groups = df[group_col].unique()

    # Determine timepoint ordering: prefer the user-supplied order,
    # fall back to sorted unique values from the data.
    if timepoint_order is not None:
        # Keep only timepoints that actually appear in the data
        data_tp_set = set(str(tp) for tp in df[timepoint_col].unique())
        timepoints = [tp for tp in timepoint_order if tp in data_tp_set]
    else:
        timepoints = sorted(df[timepoint_col].unique(), key=str)

    # Determine if timepoints are numeric
    try:
        timepoint_values = [float(tp) for tp in timepoints]
        numeric_tp = True
    except (ValueError, TypeError):
        timepoint_values = list(range(len(timepoints)))
        numeric_tp = False

    # Plot individual animal traces
    for group in groups:
        color = colors.get(str(group), "gray")
        df_group = df[df[group_col] == group]
        subjects = df_group[subject_col].unique()

        for subject in subjects:
            df_subj = df_group[df_group[subject_col] == subject].copy()
            df_subj = df_subj.sort_values(timepoint_col)

            if numeric_tp:
                x_vals = df_subj[timepoint_col].astype(float).values
            else:
                x_vals = [timepoint_values[timepoints.index(str(tp))] for tp in df_subj[timepoint_col]]

            y_vals = df_subj[dependent_var].values

            # Determine sex for marker/linestyle
            gender = "male"  # default
            if gender_col in df_subj.columns:
                gender_vals = df_subj[gender_col].dropna().unique()
                if len(gender_vals) > 0:
                    gender = str(gender_vals[0]).lower()

            marker = sex_markers.get(gender, "o")
            linestyle = sex_linestyles.get(gender, "-")

            ax.plot(x_vals, y_vals, linestyle=linestyle, color=color,
                    alpha=individual_alpha, linewidth=1, zorder=1)
            ax.scatter(x_vals, y_vals, marker=marker, color=color,
                       edgecolor="none", alpha=individual_alpha, s=20, zorder=1)

    # Plot group mean +/- SEM
    for group in groups:
        color = colors.get(str(group), "gray")
        df_group = df[df[group_col] == group]

        means = []
        sems = []
        for tp in timepoints:
            # Compare as strings to avoid type mismatch (timepoint_order
            # supplies strings, but the column may contain int/float).
            vals = df_group[df_group[timepoint_col].astype(str) == str(tp)][dependent_var].dropna()
            means.append(vals.mean())
            sems.append(vals.sem())

        means = np.array(means)
        sems = np.array(sems)

        ax.plot(timepoint_values, means, color=color, label=str(group),
                linewidth=2.5, zorder=2)
        ax.errorbar(timepoint_values, means, yerr=sems, fmt="o",
                     color=color, markersize=5, capsize=3, linewidth=1.5, zorder=2)

    # Intervention line
    if intervention_x is not None:
        add_intervention_line(ax, intervention_x)

    # Significance annotations
    if pairwise_results:
        annotation_y = y_max * 0.85
        for pw in pairwise_results:
            if pw.timepoint is not None and pw.stars != "n.s.":
                try:
                    tp_x = float(pw.timepoint)
                except (ValueError, TypeError):
                    if str(pw.timepoint) in timepoints:
                        tp_x = timepoint_values[timepoints.index(str(pw.timepoint))]
                    else:
                        continue
                add_significance_annotation(
                    ax, tp_x, annotation_y, pw.stars,
                    p_value=pw.p_adjusted if show_p_values else None,
                    show_p=show_p_values,
                )

    # Formatting
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
        fig.suptitle(title)

    # Always set explicit ticks to display the actual experimental timepoints.
    # For numeric timepoints the values are used as tick positions (proportional
    # spacing on the axis).  For categorical timepoints they are evenly spaced
    # with the category names as labels.
    ax.set_xticks(timepoint_values)
    ax.set_xticklabels([str(tp) for tp in timepoints])

    if use_log_scale:
        format_log_yaxis(ax, y_min, y_max)

    ax.legend(loc="best", frameon=False)
    despine(ax)

    fig.tight_layout()
    return fig, ax
