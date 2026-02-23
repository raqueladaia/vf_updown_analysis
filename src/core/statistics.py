"""Statistical analysis for von Frey up-down data.

Provides:
- Linear mixed-effects models (longitudinal designs)
- ANOVA (factorial designs)
- Post-hoc pairwise comparisons with multiple comparison correction
- Delta score computation (pre-post designs)
- Effect sizes (Cohen's d, eta-squared)
- Significance annotation helpers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

import numpy as np
import pandas as pd
import pingouin as pg
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


@dataclass
class StatResult:
    """Container for statistical test results."""

    test_name: str
    summary_text: str
    table: Optional[pd.DataFrame] = None
    pairwise: Optional[pd.DataFrame] = None
    effect_sizes: Optional[pd.DataFrame] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class PairwiseResult:
    """Container for a pairwise comparison at a single timepoint/condition."""

    group_a: str
    group_b: str
    timepoint: Optional[str] = None
    statistic: float = 0.0
    df: float = 0.0
    p_value: float = 1.0
    p_adjusted: float = 1.0
    effect_size: float = 0.0
    effect_size_type: str = "Cohen's d"
    stars: str = ""


def significance_stars(p: float) -> str:
    """Convert a p-value to significance stars.

    Args:
        p: p-value.

    Returns:
        Stars string: '***' (p<0.001), '**' (p<0.01), '*' (p<0.05), 'n.s.' otherwise.
    """
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    return "n.s."


def cohens_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Compute Cohen's d effect size between two groups.

    Uses pooled standard deviation.

    Args:
        group_a: Values for group A.
        group_b: Values for group B.

    Returns:
        Cohen's d value.
    """
    n_a, n_b = len(group_a), len(group_b)
    if n_a < 2 or n_b < 2:
        return np.nan

    var_a = np.var(group_a, ddof=1)
    var_b = np.var(group_b, ddof=1)
    pooled_std = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))

    if pooled_std == 0:
        return 0.0

    return float((np.mean(group_a) - np.mean(group_b)) / pooled_std)


def holm_bonferroni_correction(p_values: list[float]) -> list[float]:
    """Apply Holm-Bonferroni correction to a list of p-values.

    Args:
        p_values: List of raw p-values.

    Returns:
        List of corrected p-values (same order as input).
    """
    n = len(p_values)
    if n == 0:
        return []

    # Sort p-values and track original indices
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])

    corrected = [0.0] * n
    cumulative_max = 0.0

    for rank, (orig_idx, p) in enumerate(indexed):
        adjusted = p * (n - rank)
        adjusted = min(adjusted, 1.0)
        cumulative_max = max(cumulative_max, adjusted)
        corrected[orig_idx] = cumulative_max

    return corrected


# ── Longitudinal analysis (mixed-effects model) ─────────────────────────


def _validate_design_matrix(
    df: pd.DataFrame,
    dependent_var: str,
    group_col: str,
    timepoint_col: str,
    subject_col: str,
) -> list[str]:
    """Check the group x timepoint design matrix for problems.

    Returns a list of warning strings (empty if no problems).
    """
    warnings: list[str] = []

    # Cross-tabulate group x timepoint: count non-NaN observations per cell
    ct = df.groupby([group_col, timepoint_col])[dependent_var].count().unstack(fill_value=0)

    # Empty cells (no observations)
    empty_cells = []
    for grp in ct.index:
        for tp in ct.columns:
            if ct.loc[grp, tp] == 0:
                empty_cells.append(f"  {group_col}={grp}, {timepoint_col}={tp}")
    if empty_cells:
        warnings.append(
            "Empty cells in the design (no observations):\n" + "\n".join(empty_cells)
            + "\nThe model may fail or be unidentifiable."
        )

    # Cells with n=1 (mixed model needs n>=2 per cell for variance estimation)
    small_cells = []
    for grp in ct.index:
        for tp in ct.columns:
            n = ct.loc[grp, tp]
            if 0 < n < 2:
                small_cells.append(f"  {group_col}={grp}, {timepoint_col}={tp} (n={n})")
    if small_cells:
        warnings.append(
            "Cells with n < 2 (mixed models need n >= 2 per cell):\n"
            + "\n".join(small_cells)
        )

    # Groups with only one subject (random intercept is unestimable)
    subjects_per_group = df.groupby(group_col)[subject_col].nunique()
    tiny_groups = subjects_per_group[subjects_per_group < 2]
    if not tiny_groups.empty:
        parts = [f"  {group_col}={grp} (n_subjects={n})" for grp, n in tiny_groups.items()]
        warnings.append(
            "Groups with fewer than 2 subjects (random intercept cannot be "
            "estimated):\n" + "\n".join(parts)
        )

    return warnings


def run_mixed_effects_model(
    df: pd.DataFrame,
    dependent_var: str = "threshold_50",
    group_col: str = "group",
    timepoint_col: str = "timepoint",
    subject_col: str = "mouse",
) -> StatResult:
    """Fit a linear mixed-effects model for longitudinal data.

    Model: dependent_var ~ C(group) * C(timepoint), random intercept for subject.

    Timepoint is always treated as a categorical factor (C(timepoint)) so that
    the model does not assume a linear trend across timepoints.

    If the full interaction model fails (e.g. singular matrix), the function
    falls back to an additive model (group + timepoint, no interaction) and
    includes a warning in the output.

    Args:
        df: DataFrame with the data.
        dependent_var: Name of the dependent variable column.
        group_col: Name of the group column.
        timepoint_col: Name of the timepoint column.
        subject_col: Name of the subject/mouse column.

    Returns:
        StatResult with model summary, fixed-effects table, and any warnings.
    """
    # ── 1. Clean data ─────────────────────────────────────────────────────
    required_cols = [dependent_var, group_col, timepoint_col, subject_col]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in data: {missing_cols}")

    df_clean = df[required_cols].dropna(subset=[dependent_var]).copy()

    if df_clean.empty:
        raise ValueError(
            f"No valid observations: all rows have NaN in '{dependent_var}'."
        )

    # Ensure categorical types for the formula
    df_clean[group_col] = df_clean[group_col].astype(str)
    df_clean[timepoint_col] = df_clean[timepoint_col].astype(str)

    # ── 2. Validate design matrix ─────────────────────────────────────────
    design_warnings = _validate_design_matrix(
        df_clean, dependent_var, group_col, timepoint_col, subject_col,
    )

    # ── 3. Fit model (full interaction → additive fallback) ───────────────
    full_formula = f"{dependent_var} ~ C({group_col}) * C({timepoint_col})"
    additive_formula = f"{dependent_var} ~ C({group_col}) + C({timepoint_col})"

    fit_warnings: list[str] = []
    used_formula = full_formula
    result = None

    try:
        model = smf.mixedlm(
            full_formula, df_clean, groups=df_clean[subject_col],
        )
        result = model.fit(reml=True)
    except Exception as full_err:
        fit_warnings.append(
            f"Full interaction model failed:\n"
            f"  Formula: {full_formula}\n"
            f"  Error:   {type(full_err).__name__}: {full_err}\n"
            f"\nFalling back to additive model (no interaction term)."
        )
        used_formula = additive_formula
        try:
            model = smf.mixedlm(
                additive_formula, df_clean, groups=df_clean[subject_col],
            )
            result = model.fit(reml=True)
        except Exception as add_err:
            # Both models failed — return a descriptive error result
            all_warnings = design_warnings + fit_warnings
            all_warnings.append(
                f"Additive model also failed:\n"
                f"  Formula: {additive_formula}\n"
                f"  Error:   {type(add_err).__name__}: {add_err}"
            )
            error_text = (
                "MIXED-EFFECTS MODEL FAILED\n"
                + "=" * 60 + "\n\n"
                + "Both the full interaction model and the additive fallback\n"
                + "failed to converge. This usually happens when:\n"
                + "  - Some group x timepoint cells are empty or have n=1\n"
                + "  - A group has only one subject (random intercept is\n"
                + "    unidentifiable)\n"
                + "  - There is no variance within some cells\n\n"
                + "\n\n".join(all_warnings)
            )
            return StatResult(
                test_name="Linear Mixed-Effects Model (FAILED)",
                summary_text=error_text,
                table=None,
                warnings=all_warnings,
            )

    # ── 4. Build result ───────────────────────────────────────────────────
    all_warnings = design_warnings + fit_warnings
    summary_parts: list[str] = []

    if all_warnings:
        summary_parts.append("WARNINGS")
        summary_parts.append("-" * 40)
        for w in all_warnings:
            summary_parts.append(w)
        summary_parts.append("")

    summary_parts.append(f"Formula: {used_formula}")
    summary_parts.append(f"Random: ~1 | {subject_col}")
    summary_parts.append(f"N observations: {len(df_clean)}")
    summary_parts.append(f"N subjects: {df_clean[subject_col].nunique()}")
    summary_parts.append("")
    summary_parts.append(str(result.summary()))

    # Extract fixed effects table
    table = pd.DataFrame({
        "coefficient": result.fe_params,
        "std_error": result.bse_fe,
        "z_value": result.tvalues,
        "p_value": result.pvalues,
    })

    return StatResult(
        test_name="Linear Mixed-Effects Model",
        summary_text="\n".join(summary_parts),
        table=table,
        warnings=all_warnings,
    )


def run_rm_anova(
    df: pd.DataFrame,
    dependent_var: str = "threshold_50",
    group_col: str = "group",
    timepoint_col: str = "timepoint",
    subject_col: str = "mouse",
) -> StatResult:
    """Run a two-way repeated-measures / mixed ANOVA.

    Uses pingouin.mixed_anova with *group_col* as between-subject factor and
    *timepoint_col* as within-subject factor.  Greenhouse-Geisser correction
    is applied automatically when sphericity is violated.

    Args:
        df: DataFrame with the data.
        dependent_var: Dependent variable column.
        group_col: Between-subject factor (group).
        timepoint_col: Within-subject factor (timepoint).
        subject_col: Subject/mouse column.

    Returns:
        StatResult with ANOVA table (F, df, p, partial eta-squared) and
        any warnings.
    """
    required_cols = [dependent_var, group_col, timepoint_col, subject_col]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in data: {missing_cols}")

    df_clean = df[required_cols].dropna(subset=[dependent_var]).copy()
    if df_clean.empty:
        raise ValueError(
            f"No valid observations: all rows have NaN in '{dependent_var}'."
        )

    df_clean[group_col] = df_clean[group_col].astype(str)
    df_clean[timepoint_col] = df_clean[timepoint_col].astype(str)

    # ── Validate design ───────────────────────────────────────────────────
    design_warnings = _validate_design_matrix(
        df_clean, dependent_var, group_col, timepoint_col, subject_col,
    )

    # pingouin.mixed_anova requires balanced-ish data: every subject must
    # have an observation at every timepoint.  Drop incomplete subjects.
    all_tp = set(df_clean[timepoint_col].unique())
    complete_subjects = []
    for subj, grp in df_clean.groupby(subject_col):
        if set(grp[timepoint_col].unique()) == all_tp:
            complete_subjects.append(subj)

    n_dropped = df_clean[subject_col].nunique() - len(complete_subjects)
    if n_dropped > 0:
        design_warnings.append(
            f"Dropped {n_dropped} subject(s) with missing timepoints "
            f"(mixed ANOVA requires complete cases)."
        )

    df_clean = df_clean[df_clean[subject_col].isin(complete_subjects)].copy()
    if df_clean.empty:
        raise ValueError(
            "No subjects have observations at all timepoints. "
            "Cannot run repeated-measures ANOVA."
        )

    # ── Run mixed ANOVA (between: group, within: timepoint) ───────────────
    aov = pg.mixed_anova(
        data=df_clean,
        dv=dependent_var,
        within=timepoint_col,
        between=group_col,
        subject=subject_col,
    )

    # ── Check sphericity for the within-subject factor ────────────────────
    n_tp = df_clean[timepoint_col].nunique()
    gg_note = ""
    if n_tp > 2:
        try:
            _, W, _, _, p_spher = pg.sphericity(
                data=df_clean,
                dv=dependent_var,
                within=timepoint_col,
                subject=subject_col,
            )
            if p_spher < 0.05:
                gg_note = (
                    f"Sphericity violated (W={W:.3f}, p={p_spher:.4f}). "
                    "Greenhouse-Geisser corrected p-values are reported "
                    "(p-GG-corr column)."
                )
                design_warnings.append(gg_note)
        except Exception:
            design_warnings.append(
                "Could not test sphericity (may require more subjects "
                "or timepoints). Uncorrected p-values are reported."
            )

    # ── Format output ─────────────────────────────────────────────────────
    summary_parts: list[str] = []
    if design_warnings:
        summary_parts.append("WARNINGS")
        summary_parts.append("-" * 40)
        for w in design_warnings:
            summary_parts.append(w)
        summary_parts.append("")

    summary_parts.append(
        f"Two-way mixed ANOVA: {dependent_var} ~ "
        f"{group_col} (between) x {timepoint_col} (within)"
    )
    summary_parts.append(f"Subject: {subject_col}")
    summary_parts.append(f"N observations: {len(df_clean)}")
    summary_parts.append(f"N subjects: {df_clean[subject_col].nunique()}")
    summary_parts.append("")

    # Pretty-print the ANOVA table
    display_cols = [c for c in [
        "Source", "SS", "DF1", "DF2", "MS", "F", "p-unc", "p-GG-corr",
        "np2", "eps",
    ] if c in aov.columns]
    summary_parts.append(aov[display_cols].to_string(index=False))

    return StatResult(
        test_name="Repeated-Measures ANOVA",
        summary_text="\n".join(summary_parts),
        table=aov,
        warnings=design_warnings,
    )


def run_posthoc_pairwise_at_timepoints(
    df: pd.DataFrame,
    dependent_var: str = "threshold_50",
    group_col: str = "group",
    timepoint_col: str = "timepoint",
    correction: str = "holm",
) -> list[PairwiseResult]:
    """Run pairwise comparisons between groups at each timepoint.

    Uses Welch's t-test (unequal variances) at each timepoint.  All p-values
    across ALL timepoints are collected first, then corrected simultaneously
    using the selected method.

    Args:
        df: DataFrame with the data.
        dependent_var: Dependent variable column.
        group_col: Group column.
        timepoint_col: Timepoint column.
        correction: Correction method — 'holm', 'bonferroni', or 'fdr_bh'.

    Returns:
        List of PairwiseResult objects (one per comparison per timepoint).
    """
    df_clean = df.dropna(subset=[dependent_var]).copy()
    results: list[PairwiseResult] = []
    timepoints = df_clean[timepoint_col].unique()
    groups = df_clean[group_col].unique()

    if len(groups) < 2:
        return results

    # ── Collect all raw comparisons across ALL timepoints first ────────────
    raw_comparisons: list[dict] = []

    for tp in timepoints:
        df_tp = df_clean[df_clean[timepoint_col] == tp]
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                g_a = df_tp[df_tp[group_col] == groups[i]][dependent_var].dropna().values
                g_b = df_tp[df_tp[group_col] == groups[j]][dependent_var].dropna().values

                if len(g_a) < 2 or len(g_b) < 2:
                    continue

                # Welch's t-test (does not assume equal variances)
                t_result = stats.ttest_ind(g_a, g_b, equal_var=False)
                t_stat = t_result.statistic
                p_val = t_result.pvalue

                # Welch-Satterthwaite degrees of freedom
                n_a, n_b = len(g_a), len(g_b)
                var_a = np.var(g_a, ddof=1)
                var_b = np.var(g_b, ddof=1)
                num = (var_a / n_a + var_b / n_b) ** 2
                denom = (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
                welch_df = num / denom if denom > 0 else n_a + n_b - 2

                d = cohens_d(g_a, g_b)

                raw_comparisons.append({
                    "group_a": str(groups[i]),
                    "group_b": str(groups[j]),
                    "timepoint": str(tp),
                    "statistic": float(t_stat),
                    "df": float(welch_df),
                    "p_value": float(p_val),
                    "effect_size": d,
                })

    # ── Apply correction across the FULL set of p-values ──────────────────
    if raw_comparisons:
        raw_p = np.array([c["p_value"] for c in raw_comparisons])

        method_map = {
            "holm": "holm",
            "bonferroni": "bonferroni",
            "fdr_bh": "fdr_bh",
            "none": None,
        }
        mt_method = method_map.get(correction)

        if mt_method is not None:
            _, corrected_p, _, _ = multipletests(raw_p, method=mt_method)
        else:
            corrected_p = raw_p

        for comp, p_adj in zip(raw_comparisons, corrected_p):
            results.append(PairwiseResult(
                group_a=comp["group_a"],
                group_b=comp["group_b"],
                timepoint=comp["timepoint"],
                statistic=comp["statistic"],
                df=comp["df"],
                p_value=comp["p_value"],
                p_adjusted=float(p_adj),
                effect_size=comp["effect_size"],
                stars=significance_stars(float(p_adj)),
            ))

    return results


# ── Factorial analysis (ANOVA / delta scores) ───────────────────────────


def compute_delta_scores(
    df: pd.DataFrame,
    dependent_var: str = "threshold_50",
    timepoint_col: str = "timepoint",
    subject_col: str = "mouse",
    pre_label: str = "pre",
    post_label: str = "post_chronic",
) -> pd.DataFrame:
    """Compute delta (change) scores: post - pre for each animal.

    Args:
        df: DataFrame with the data.
        dependent_var: Dependent variable column.
        timepoint_col: Timepoint column.
        subject_col: Subject/mouse column.
        pre_label: Label for the pre-intervention timepoint.
        post_label: Label for the post-intervention timepoint.

    Returns:
        DataFrame with one row per subject containing:
        - subject_col
        - '{dependent_var}_pre'
        - '{dependent_var}_post'
        - 'delta' (post - pre)
        - Any other metadata columns that are constant per subject.
    """
    df_pre = df[df[timepoint_col] == pre_label].set_index(subject_col)
    df_post = df[df[timepoint_col] == post_label].set_index(subject_col)

    common_subjects = df_pre.index.intersection(df_post.index)

    result = pd.DataFrame({
        subject_col: common_subjects,
        f"{dependent_var}_pre": df_pre.loc[common_subjects, dependent_var].values,
        f"{dependent_var}_post": df_post.loc[common_subjects, dependent_var].values,
    })
    result["delta"] = result[f"{dependent_var}_post"] - result[f"{dependent_var}_pre"]

    # Carry over metadata columns that are constant per subject
    meta_cols = [c for c in df.columns if c not in [dependent_var, timepoint_col, subject_col]]
    for col in meta_cols:
        vals = df_pre.loc[common_subjects, col] if col in df_pre.columns else None
        if vals is not None:
            result[col] = vals.values

    return result


def run_anova_on_deltas(
    delta_df: pd.DataFrame,
    dependent_var: str = "delta",
    factors: Optional[list[str]] = None,
) -> StatResult:
    """Run ANOVA on delta scores.

    Supports one-way or multi-way ANOVA depending on number of factors.

    Args:
        delta_df: DataFrame with delta scores and factor columns.
        dependent_var: Name of the dependent variable (delta scores).
        factors: List of factor column names. If None, auto-detect group columns.

    Returns:
        StatResult with ANOVA table and summary.
    """
    if factors is None or len(factors) == 0:
        raise ValueError("At least one factor must be specified for ANOVA.")

    delta_df = delta_df.dropna(subset=[dependent_var] + factors).copy()

    # Build formula with interactions
    factor_terms = " * ".join([f"C({f})" for f in factors])
    formula = f"{dependent_var} ~ {factor_terms}"

    model = smf.ols(formula, data=delta_df).fit()
    anova_table = sm.stats.anova_lm(model, typ=2)

    summary_text = f"ANOVA: {dependent_var} ~ {' * '.join(factors)}\n\n"
    summary_text += str(anova_table)
    summary_text += f"\n\nModel R² = {model.rsquared:.4f}"

    # Compute eta-squared
    ss_total = anova_table["sum_sq"].sum()
    anova_table["eta_squared"] = anova_table["sum_sq"] / ss_total

    return StatResult(
        test_name="ANOVA on Delta Scores",
        summary_text=summary_text,
        table=anova_table,
    )


def run_posthoc_on_deltas(
    delta_df: pd.DataFrame,
    dependent_var: str = "delta",
    group_col: str = "group",
    correction: str = "holm",
) -> list[PairwiseResult]:
    """Run post-hoc pairwise comparisons on delta scores.

    Args:
        delta_df: DataFrame with delta scores.
        dependent_var: Delta score column.
        group_col: Group column for comparisons.
        correction: Multiple comparison correction method.

    Returns:
        List of PairwiseResult objects.
    """
    groups = delta_df[group_col].unique()
    results: list[PairwiseResult] = []
    raw_comparisons: list[dict] = []

    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            g_a = delta_df[delta_df[group_col] == groups[i]][dependent_var].dropna().values
            g_b = delta_df[delta_df[group_col] == groups[j]][dependent_var].dropna().values

            if len(g_a) < 2 or len(g_b) < 2:
                continue

            t_result = stats.ttest_ind(g_a, g_b, equal_var=False)
            d = cohens_d(g_a, g_b)

            n_a, n_b = len(g_a), len(g_b)
            var_a = np.var(g_a, ddof=1)
            var_b = np.var(g_b, ddof=1)
            num = (var_a / n_a + var_b / n_b) ** 2
            denom = (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
            welch_df = num / denom if denom > 0 else n_a + n_b - 2

            raw_comparisons.append({
                "group_a": str(groups[i]),
                "group_b": str(groups[j]),
                "statistic": float(t_result.statistic),
                "df": float(welch_df),
                "p_value": float(t_result.pvalue),
                "effect_size": d,
            })

    if raw_comparisons:
        raw_p = np.array([c["p_value"] for c in raw_comparisons])

        method_map = {"holm": "holm", "bonferroni": "bonferroni", "fdr_bh": "fdr_bh", "none": None}
        mt_method = method_map.get(correction)
        if mt_method is not None and len(raw_p) > 1:
            _, corrected_p, _, _ = multipletests(raw_p, method=mt_method)
        else:
            corrected_p = raw_p

        for comp, p_adj in zip(raw_comparisons, corrected_p):
            results.append(PairwiseResult(
                group_a=comp["group_a"],
                group_b=comp["group_b"],
                statistic=comp["statistic"],
                df=comp["df"],
                p_value=comp["p_value"],
                p_adjusted=float(p_adj),
                effect_size=comp["effect_size"],
                stars=significance_stars(float(p_adj)),
            ))

    return results


def pairwise_results_to_dataframe(results: list[PairwiseResult]) -> pd.DataFrame:
    """Convert a list of PairwiseResult objects to a DataFrame.

    Args:
        results: List of PairwiseResult.

    Returns:
        DataFrame with one row per comparison.
    """
    if not results:
        return pd.DataFrame()

    rows = []
    for r in results:
        rows.append({
            "group_a": r.group_a,
            "group_b": r.group_b,
            "timepoint": r.timepoint,
            "statistic": round(r.statistic, 4),
            "df": round(r.df, 2),
            "p_value": r.p_value,
            "p_adjusted": r.p_adjusted,
            "effect_size": round(r.effect_size, 4),
            "effect_size_type": r.effect_size_type,
            "significance": r.stars,
        })

    return pd.DataFrame(rows)
