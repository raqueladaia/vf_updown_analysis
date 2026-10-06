"""Lightweight import and logic smoke tests (no GUI launch)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_imports() -> None:
    from src.core import data_loader, statistics, vf_threshold
    from src.plotting import factorial, longitudinal, plot_utils
    from src.gui import state

    assert data_loader.build_facet_slices is not None
    assert statistics.compute_delta_scores is not None
    assert vf_threshold.compute_thresholds_batch is not None
    assert factorial.plot_paired_lines is not None
    assert longitudinal.plot_longitudinal is not None
    assert state.AnalysisState is not None
    assert plot_utils.DEFAULT_SEX_LINESTYLES is not None


def test_facet_and_state() -> None:
    import pandas as pd

    from src.core.data_loader import build_facet_slices, get_active_timepoints
    from src.gui.state import AnalysisState

    assert get_active_timepoints(["pre", "post"], []) == ["pre", "post"]

    df = pd.DataFrame(
        {
            "mouse": ["m1", "m1", "m2", "m2"],
            "timepoint": ["pre", "post", "pre", "post"],
            "drug": ["sal", "sal", "DCZ", "DCZ"],
            "threshold_50": [1.0, 2.0, 3.0, 4.0],
        }
    )
    slices = build_facet_slices(
        df,
        mouse_col="mouse",
        timepoint_col="timepoint",
        timepoint_order=["pre", "post"],
        excluded_timepoints=[],
        facet_cols=[],
        facet_values={},
    )
    assert len(slices) == 1

    st = AnalysisState.from_json('{"facet_cols": [], "group_cols": ["drug"]}')
    assert st.group_cols == ["drug"]

    legacy = AnalysisState.from_json(
        '{"blocking_factor_cols": ["treatment"], "blocking_factor_values": {"treatment": ["acute"]}}'
    )
    assert legacy.facet_cols == ["treatment"]
    assert legacy.facet_values == {"treatment": ["acute"]}


def test_metadata_accept_exclusions() -> None:
    import pandas as pd

    from src.core.data_loader import get_mice_not_accepted

    meta = pd.DataFrame(
        {
            "animal_id": [1, 2, 3],
            "include_in_analysis": [1, 0, 1],
        }
    )
    assert get_mice_not_accepted(meta, "animal_id") == ["2"]

    meta_accept = pd.DataFrame(
        {
            "mouse": ["a", "b"],
            "accept": [1, 0],
        }
    )
    assert get_mice_not_accepted(meta_accept, "mouse") == ["b"]


def test_paired_plot() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import pandas as pd

    from src.plotting.factorial import plot_paired_lines

    df = pd.DataFrame(
        {
            "mouse": ["m1", "m1", "m2", "m2"],
            "timepoint": ["pre", "post", "pre", "post"],
            "group": ["A", "A", "B", "B"],
            "sex": ["male", "male", "female", "female"],
            "threshold_50": [0.5, 1.0, 0.8, 1.2],
        }
    )
    fig, ax = plot_paired_lines(
        df,
        timepoint_col="timepoint",
        group_col="group",
        pre_label="pre",
        post_label="post",
        use_log_scale=False,
    )
    assert len(ax.lines) > 0
    import matplotlib.pyplot as plt

    plt.close(fig)


def test_longitudinal_plot() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import pandas as pd

    from src.plotting.longitudinal import plot_longitudinal

    df = pd.DataFrame(
        {
            "mouse": ["m1", "m1", "m2", "m2"],
            "Timepoint_SNI_day": [-7, 7, -7, 7],
            "group": ["A", "A", "B", "B"],
            "sex": ["male", "male", "female", "female"],
            "threshold_50": [0.5, 1.0, 0.8, 1.2],
        }
    )
    fig, ax = plot_longitudinal(
        df,
        timepoint_col="Timepoint_SNI_day",
        group_col="group",
        show_sex_encoding=False,
        use_log_scale=False,
    )
    assert len(ax.lines) > 0
    import matplotlib.pyplot as plt

    plt.close(fig)


def test_validate_pre_post_missing_pairs() -> None:
    import pandas as pd

    from src.core.data_loader import validate_pre_post_design
    from src.core.statistics import compute_delta_scores

    df = pd.DataFrame(
        {
            "mouse": ["m1", "m1", "m2", "m3"],
            "timepoint": ["pre", "post", "pre", "post"],
            "threshold_50": [1.0, 2.0, 3.0, 4.0],
        }
    )
    errors, warnings = validate_pre_post_design(
        df,
        mouse_col="mouse",
        timepoint_col="timepoint",
        active_timepoints=["pre", "post"],
        pre_label="pre",
        post_label="post",
    )
    assert not errors
    assert any("Excluding" in w for w in warnings)
    assert "m2" in warnings[0]

    delta_df = compute_delta_scores(
        df,
        timepoint_col="timepoint",
        subject_col="mouse",
        pre_label="pre",
        post_label="post",
    )
    assert list(delta_df["mouse"]) == ["m1"]


def test_validate_pre_post_duplicate_rows_still_error() -> None:
    import pandas as pd

    from src.core.data_loader import validate_pre_post_design

    df = pd.DataFrame(
        {
            "mouse": ["m1", "m1", "m1"],
            "timepoint": ["pre", "pre", "post"],
            "threshold_50": [1.0, 1.1, 2.0],
        }
    )
    errors, warnings = validate_pre_post_design(
        df,
        mouse_col="mouse",
        timepoint_col="timepoint",
        active_timepoints=["pre", "post"],
        pre_label="pre",
        post_label="post",
    )
    assert errors
    assert any("Duplicate" in e for e in errors)
    assert not warnings


def test_group_combination_labels() -> None:
    import pandas as pd

    from src.core.data_loader import (
        GROUP_COMBINATION_COL,
        add_group_combination_column,
        format_group_combination_label,
        get_unique_group_combination_labels,
        resolve_plot_group_column,
    )

    df = pd.DataFrame(
        {
            "mouse": ["m1", "m1", "m2", "m2", "m3", "m3"],
            "timepoint": ["pre", "post", "pre", "post", "pre", "post"],
            "condition": ["control", "control", "control", "control", "exp", "exp"],
            "treatment": ["acute", "acute", "chronic", "chronic", "acute", "acute"],
            "threshold_50": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )

    labels = get_unique_group_combination_labels(
        df, ["condition", "treatment"], mouse_col="mouse"
    )
    assert labels == [
        "condition=control x treatment=acute",
        "condition=control x treatment=chronic",
        "condition=exp x treatment=acute",
    ]

    row = df.iloc[0]
    assert (
        format_group_combination_label(["condition", "treatment"], row)
        == "condition=control x treatment=acute"
    )
    assert format_group_combination_label(["condition"], row) == "control"

    plot_df = add_group_combination_column(df, ["condition", "treatment"], "mouse")
    assert GROUP_COMBINATION_COL in plot_df.columns
    assert plot_df[GROUP_COMBINATION_COL].nunique() == 3
    assert resolve_plot_group_column(["condition", "treatment"]) == GROUP_COMBINATION_COL
    assert resolve_plot_group_column(["condition"]) == "condition"


def main() -> int:
    test_imports()
    test_facet_and_state()
    test_metadata_accept_exclusions()
    test_validate_pre_post_missing_pairs()
    test_validate_pre_post_duplicate_rows_still_error()
    test_group_combination_labels()
    test_paired_plot()
    test_longitudinal_plot()
    print("smoke_test: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
