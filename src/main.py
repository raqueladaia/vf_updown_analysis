"""CLI entry point for von Frey Up-Down Analysis Tool.

Provides backward-compatible command-line access and launches the GUI.
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Main entry point: launch GUI or run CLI analysis."""
    parser = argparse.ArgumentParser(
        description="Von Frey Up-Down Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                         # Launch GUI
  python run.py --compute \\
    --data data/data_timeline_experiment.xlsx \\
    --metadata data/metadata_timeline_experiment.xlsx \\
    --filament-ref data/VF_Calculator_Up-down.xlsx \\
    --output results/
        """,
    )

    parser.add_argument("--compute", action="store_true",
                        help="Run threshold computation in CLI mode (skip GUI)")
    parser.add_argument("--data", type=str, help="Path to von Frey data file")
    parser.add_argument("--metadata", type=str, help="Path to metadata file")
    parser.add_argument("--filament-ref", type=str,
                        default="data/VF_Calculator_Up-down.xlsx",
                        help="Path to filament reference file")
    parser.add_argument("--output", type=str, default=".", help="Output directory")
    parser.add_argument("--log-column", type=str, default="Log_new",
                        choices=["Log", "Log_new"],
                        help="Which log column to use for computation")

    args = parser.parse_args()

    if args.compute:
        _run_cli(args)
    else:
        _run_gui()


def _run_gui() -> None:
    """Launch the PyQt6 GUI."""
    from .gui.app import main as gui_main
    gui_main()


def _run_cli(args: argparse.Namespace) -> None:
    """Run computation in CLI mode."""
    from pathlib import Path

    import pandas as pd

    from .core.data_loader import load_excel_or_csv, merge_metadata
    from .core.vf_threshold import compute_thresholds_batch, load_filament_reference

    if not args.data:
        print("Error: --data is required in compute mode", file=sys.stderr)
        sys.exit(1)

    # Load filament reference
    print(f"Loading filament reference: {args.filament_ref}")
    filament_info, series_stats = load_filament_reference(args.filament_ref)

    # Load data
    print(f"Loading data: {args.data}")
    df = load_excel_or_csv(args.data)

    # Compute thresholds
    print(f"Computing thresholds using {args.log_column} column...")
    df["threshold_50"] = compute_thresholds_batch(
        df, filament_info, series_stats, log_column=args.log_column
    )

    # Merge metadata if provided
    if args.metadata:
        print(f"Loading metadata: {args.metadata}")
        meta_df = load_excel_or_csv(args.metadata)
        df = merge_metadata(df, meta_df)

    # Save output
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "vf_thresholds.xlsx"
    df.to_excel(output_file, index=False)
    print(f"Results saved to {output_file}")

    n_nan = df["threshold_50"].isna().sum()
    print(f"Computed {len(df)} thresholds ({n_nan} NaN)")


if __name__ == "__main__":
    main()
