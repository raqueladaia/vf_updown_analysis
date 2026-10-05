"""Regression coverage for species choice, stale results, and boundary policies."""
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.core.vf_threshold import (
    boundary_summary, compute_50_threshold, compute_threshold_report,
    load_filament_reference, load_filament_set, load_k_statistics,
    spacing_warning, unresolved_boundaries,
)
from src.gui.state import AnalysisState

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / 'data/VF_Calculator_Up-down.xlsx'


class CalculationSafetyTests(unittest.TestCase):
    def test_rat_does_not_open_excel_and_uses_target_force(self):
        with patch('pandas.read_excel', side_effect=AssertionError('Rat must not read Excel')):
            info, stats = load_filament_reference('/nonexistent/master.xlsx', filament_set='rat')
        self.assertEqual(info['Force (g)'].tolist(), [.4, .6, 1, 2, 4, 6, 8, 15])
        self.assertEqual(info.Log_new.iloc[2], 4.0)
        # Supported six-response alternation has k=-0.5; equal log steps imply this ratio.
        value = compute_50_threshold('OXOXOX', 8, info, stats)
        self.assertAlmostEqual(value, 15 / (15/.4)**(1/14))
        with self.assertRaisesRegex(ValueError, 'Rat thresholds use Log_new'):
            compute_50_threshold('OXOXOX', 8, info, stats, 'Log')

    def test_standalone_k_table_is_exact_transcription(self):
        _, legacy = load_filament_reference(MASTER)
        standalone = load_k_statistics()
        original = {s: k for s, k in legacy.items() if isinstance(s, str) and set(s) <= set('XO')}
        self.assertEqual(len(standalone), 248)
        self.assertEqual(original, standalone)

    def test_boundaries_and_invalid_rows_remain_distinct(self):
        info, stats = load_filament_reference(filament_set='rat')
        df = pd.DataFrame({
            'xo_series': ['XXXX', 'OOOOO', 'XXX', 'OOO', 'X'*9, 'bad', 'OXOXOX', 'OXOXOX'],
            'last_filament': [1, 8, 2, 7, 1, 4, 8, 999],
        }, index=[2, 2, 4, 9, 10, 20, 30, 50])
        for policy in ['flag', 'endpoints', 'exclude']:
            report = compute_threshold_report(df, info, stats, boundary_policy=policy)
            self.assertEqual(report.index.tolist(), df.index.tolist())
            self.assertEqual(report.vf_status.tolist(), [
                'below_range', 'above_range', 'incomplete_no_reversal', 'incomplete_no_reversal',
                'invalid_boundary_history', 'invalid_series', 'estimated', 'unknown_filament',
            ])
            np.testing.assert_allclose(report.vf_boundary_limit_g.iloc[:2], [.4, 15])
            self.assertEqual(unresolved_boundaries(report), policy == 'flag')
            if policy == 'endpoints':
                np.testing.assert_allclose(report.threshold_50.iloc[:2], [.4, 15])
            else:
                self.assertTrue(report.threshold_50.iloc[:2].isna().all())
            self.assertTrue(report.threshold_50.iloc[2:6].isna().all())
            self.assertIn('1 below / 1 above', boundary_summary(report))
            self.assertAlmostEqual(report.threshold_50.iloc[6], 15 / (15/.4)**(1/14))

    def test_mixed_response_extrapolation_is_not_clamped(self):
        info, stats = load_filament_reference(filament_set='rat')
        df = pd.DataFrame({'xo_series': ['XO', 'OX'], 'last_filament': [8, 1]})
        report = compute_threshold_report(df, info, stats, boundary_policy='endpoints')
        self.assertEqual(report.vf_status.tolist(), ['estimate_above_range', 'estimate_below_range'])
        self.assertGreater(report.threshold_50.iloc[0], 15)
        self.assertLess(report.threshold_50.iloc[1], .4)
        self.assertTrue(report.vf_boundary_limit_g.isna().all())

    def test_spacing_warning_uses_selected_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'uneven.csv'
            path.write_text('Filament_number,Force (g),Log\n1,.4,4\n2,.41,4.2\n3,15,4.4\n')
            info = load_filament_set(path)
            self.assertIn('98.6%', spacing_warning(info))
            self.assertEqual(spacing_warning(info, 'Log'), '')
        rat, _ = load_filament_reference(filament_set='rat')
        self.assertEqual(spacing_warning(rat), '')

    def test_mouse_numeric_results_unchanged_in_report(self):
        info, stats = load_filament_reference(MASTER)
        for column in ['Log', 'Log_new']:
            rows = [(s, fid) for s in stats if isinstance(s, str) and set(s) <= set('XO')
                    for fid in info.Filament_number]
            df = pd.DataFrame(rows, columns=['xo_series', 'last_filament'])
            report = compute_threshold_report(df, info, stats, log_column=column)
            expected = [compute_50_threshold(s, fid, info, stats, column) for s, fid in rows]
            np.testing.assert_array_equal(report.threshold_50, expected)

    def test_cli_no_master_exports_boundaries_and_ladder(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.csv'
            path.write_text('mouse,timepoint,xo_series,last_filament\nr1,pre,XXXX,1\nr2,pre,OOOOO,8\n')
            args=[sys.executable, str(ROOT/'run.py'), '--compute', '--data', str(path),
                  '--filament-set', 'rat', '--filament-ref', str(Path(directory)/'absent.xlsx'),
                  '--boundary-policy', 'endpoints', '--output', directory]
            run=subprocess.run(args, cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            df=pd.read_excel(Path(directory)/'vf_thresholds.xlsx')
            np.testing.assert_allclose(df.threshold_50, [.4,15])
            self.assertTrue((Path(directory)/'vf_filaments.csv').exists())
            self.assertIn('1 below / 1 above', run.stdout)


class GuiSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PyQt6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def test_species_log_boundary_changes_invalidate_every_result(self):
        from src.gui.data_input import DataInputPanel
        state=AnalysisState(filament_ref_path=str(MASTER))
        panel=DataInputPanel(state)
        self.addCleanup(panel.close)
        state._data_df=pd.DataFrame({'mouse':['m1'],'threshold_50':[3.3], 'vf_delta':[.44]})
        for change in [lambda:panel.filament_set_combo.setCurrentIndex(1),
                       lambda:panel.boundary_combo.setCurrentIndex(1),
                       lambda:panel.filament_set_combo.setCurrentIndex(0),
                       lambda:panel.log_old_radio.setChecked(True)]:
            state._merged_df=state._data_df.copy()
            state._stat_results=object()
            state._pairwise_results=[object()]
            state._facet_slices=[object()]
            state._delta_df=state._data_df.copy()
            change()
            for attr in ['_merged_df','_stat_results','_pairwise_results','_facet_slices','_delta_df']:
                self.assertIsNone(getattr(state, attr))
            self.assertNotIn('threshold_50', state._data_df)
        self.assertEqual(state.y_max,10)
        panel.filament_set_combo.setCurrentIndex(1)
        self.assertEqual(state.y_max,20)
        self.assertFalse(panel.log_old_radio.isEnabled())
        self.assertFalse(panel.reference_browse_btn.isEnabled())

    def test_rat_axis_is_adjustable_and_session_retains_policy(self):
        from src.gui.plot_config import AppearancePanel
        state=AnalysisState(filament_set='rat', y_max=25, boundary_policy='endpoints')
        panel=AppearancePanel(state)
        self.addCleanup(panel.close)
        panel.refresh()
        self.assertEqual(panel.y_max_spin.value(),25)
        panel.y_max_spin.setValue(30)
        panel.get_config()
        restored=AnalysisState.from_json(state.to_json())
        self.assertEqual(restored.y_max,30)
        self.assertEqual(restored.boundary_policy,'endpoints')

    def test_unresolved_boundaries_block_statistics_and_plot(self):
        from src.gui.export_panel import StatsPanel
        from src.gui.plot_config import PreviewPanel
        info, stats=load_filament_reference(filament_set='rat')
        data=pd.DataFrame({'mouse':['r1'], 'timepoint':['pre'], 'xo_series':['OOOOO'], 'last_filament':[8]})
        state=AnalysisState(filament_set='rat', timepoint_col='timepoint', timepoint_order=['pre'])
        state._merged_df=compute_threshold_report(data,info,stats)
        panel=StatsPanel(state)
        self.addCleanup(panel.close)
        with patch('src.gui.export_panel.QMessageBox.warning') as warning:
            panel._run_analysis()
        self.assertEqual(warning.call_args.args[1], 'Boundary policy required')
        preview=PreviewPanel(state)
        self.addCleanup(preview.close)
        preview._replot()
        self.assertIn('Boundary observations need a policy', preview._fig.axes[0].texts[0].get_text())

    def test_compute_without_metadata_and_discard_obsolete_worker(self):
        from src.gui.data_input import DataInputPanel
        state=AnalysisState(filament_set='rat')
        panel=DataInputPanel(state)
        self.addCleanup(panel.close)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'rats.csv'
            path.write_text('mouse,timepoint,xo_series,last_filament\nr1,pre,OXOXOX,8\n')
            panel._load_data_file(str(path))
        self.assertTrue(panel.compute_btn.isEnabled())
        # Run synchronously to exercise the same completion code without event-loop races.
        with patch('src.gui.data_input.ThresholdWorker.start', lambda worker: worker.run()):
            panel._compute_thresholds()
        self.assertAlmostEqual(state._merged_df.threshold_50.iloc[0],15/(15/.4)**(1/14))
        old=state._merged_df.copy()
        panel.filament_set_combo.setCurrentIndex(0)
        panel._on_threshold_done(old)
        self.assertIsNone(state._merged_df)


if __name__ == '__main__':
    unittest.main()
