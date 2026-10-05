"""Run with python -m unittest discover -s tests -p 'test_*.py'."""
from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

from src.core.vf_threshold import (
    DELTA_INTERVAL, compute_50_threshold, compute_thresholds_batch,
    get_delta, load_filament_reference, load_filament_set,
)
from src.gui.state import AnalysisState

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'data/VF_Calculator_Up-down.xlsx'


class FilamentSetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'ladder.csv'

    def csv(self, text):
        self.path.write_text(text)
        return self.path

    def test_legacy_values_all_patterns_and_filaments(self):
        info, stats = load_filament_reference(REFERENCE)
        self.assertEqual(len(info), 8)
        self.assertEqual(get_delta(info), DELTA_INTERVAL)
        for log_column in ['Log', 'Log_new']:
            for row in info.itertuples(index=False, name=None):
                # Independent reference calculation from the original workbook.
                number = row[0]
                source_row = info.loc[info.Filament_number == number].iloc[0]
                for series, k in stats.items():
                    if not isinstance(series, str) or set(series) - set('XO'):
                        continue
                    expected = 10 ** (source_row[log_column] + k * 0.441428571) / 10000
                    actual = compute_50_threshold(series, number, info, stats, log_column)
                    self.assertEqual(actual, expected)
        # Protect the shipped calibration and historical rounding explicitly.
        self.assertEqual(info['Force (g)'].tolist(), [.0045, .023, .068, .158, .178, 1.202, 2.041, 5.495])
        self.assertEqual(info['Log_new'].tolist(), [1.653, 2.362, 2.833, 3.199, 3.25, 4.08, 4.31, 4.74])

    def test_rat_mapping_delta_and_known_result(self):
        info, stats = load_filament_reference(REFERENCE, filament_set='rat')
        self.assertEqual(info['Handle_code'].tolist(), [3.61, 3.84, 4.08, 4.31, 4.56, 4.74, 4.93, 5.18])
        self.assertEqual(info.Filament_number.tolist(), list(range(1, 9)))
        self.assertEqual(stats['OX'], -0.5)
        for column in ['Log_new']:
            self.assertAlmostEqual(get_delta(info, column), math.log10(15/.4) / 7)
            expected = 15 * 10 ** (-0.5 * (math.log10(15/.4) / 7))
            self.assertAlmostEqual(compute_50_threshold('ox', 8, info, stats, column), expected)
        self.assertAlmostEqual(info['Force (g)'].iloc[-1], 15.0)

    def test_custom_more_than_eight_and_preserved_ids(self):
        self.csv('Filament_number,Force (g)\n' + ''.join(f'{i*10},{2**i}\n' for i in range(1, 11)))
        info, stats = load_filament_reference(REFERENCE, filament_set='custom', custom_filaments=self.path)
        self.assertEqual(len(info), 10)
        df = pd.DataFrame({'xo_series': ['OX', 'bad', 'OX'], 'last_filament': [100, 100, 999]}, index=[3, 7, 9])
        result = compute_thresholds_batch(df, info, stats)
        self.assertEqual(result.index.tolist(), [3, 7, 9])
        self.assertAlmostEqual(result.loc[3], 1024 / math.sqrt(2))
        self.assertTrue(result.loc[[7, 9]].isna().all())

    def test_selected_log_column_controls_delta(self):
        info = load_filament_set(self.csv('Filament_number,Force (g),Log\n1,1,4\n2,10,4.5\n3,100,5\n'))
        self.assertAlmostEqual(get_delta(info, 'Log'), .5)
        self.assertAlmostEqual(get_delta(info, 'Log_new'), 1)
        self.assertAlmostEqual(compute_50_threshold('OX', 2, info, {'OX': -.5}), math.sqrt(10))
        self.assertAlmostEqual(compute_50_threshold('OX', 2, info, {'OX': -.5}, 'Log'), 10**.25)

    def test_invalid_csvs(self):
        invalid_rows = ['1,0\n2,1', '1,-1\n2,1', '1,nan\n2,1', '1,inf\n2,2',
                        '1,2\n2,1', '1,1\n2,1', '1,1\n1,2', '1.5,1\n2,2',
                        '0,1\n2,2', 'nan,1\n2,2', '1,1']
        for rows in invalid_rows:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                load_filament_set(self.csv('Filament_number,Force (g)\n' + rows))
        for logs in ['4,nan', '4,inf', '4,3', '4,4']:
            first, second = logs.split(',')
            with self.subTest(logs=logs), self.assertRaises(ValueError):
                load_filament_set(self.csv(f'Filament_number,Force (g),Log\n1,1,{first}\n2,2,{second}\n'))
        with self.assertRaises(ValueError):
            load_filament_set(self.csv('Number,Force\n1,1\n2,2'))

    def test_bad_profile_and_delta(self):
        for kwargs in [{'filament_set': 'other'}, {'filament_set': 'custom'},
                       {'filament_set': 'rat', 'custom_filaments': 'unused.csv'}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                load_filament_reference(REFERENCE, **kwargs)
        info, stats = load_filament_reference(REFERENCE, filament_set='rat')
        for delta in [0, -1, np.nan, np.inf]:
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                compute_50_threshold('OX', 4, info, stats, delta=delta)
        self.assertAlmostEqual(compute_50_threshold('OX', 4, info, stats, delta=.2), 2 * 10**(-.1))
        result = compute_thresholds_batch(pd.DataFrame({'xo_series':['OX'], 'last_filament':[4]}), info, stats, delta=.2)
        self.assertAlmostEqual(result.iloc[0], 2 * 10**(-.1))

    def test_session_compatibility(self):
        self.assertEqual(AnalysisState.from_json('{}').filament_set, 'legacy')
        state = AnalysisState(filament_set='custom', custom_filaments_path='my.csv', log_column='Log')
        restored = AnalysisState.from_json(state.to_json())
        self.assertEqual(restored.filament_set, 'custom')
        self.assertEqual(restored.custom_filaments_path, 'my.csv')
        self.assertEqual(restored.log_column, 'Log')

    def test_provenance_is_not_an_experimental_factor(self):
        from src.core.data_loader import detect_facet_factor_candidates
        data = pd.DataFrame({'mouse': ['a', 'a'], 'timepoint': ['pre', 'post'],
                             'vf_filament_set': ['rat', 'custom'],
                             'vf_log_column': ['Log', 'Log_new'], 'vf_delta': [.2, .3],
                             'drug': ['sal', 'drug']})
        self.assertEqual(detect_facet_factor_candidates(data), ['drug'])

    def test_cli_rat_and_custom(self):
        data = Path(self.temp.name) / 'input.csv'
        data.write_text('mouse,timepoint,xo_series,last_filament\nr1,pre,OX,8\n')
        for profile in ['rat', 'custom']:
            args = [sys.executable, str(ROOT/'run.py'), '--compute', '--data', str(data),
                    '--filament-ref', str(REFERENCE), '--filament-set', profile, '--output', self.temp.name]
            if profile == 'custom':
                self.csv('Filament_number,Force (g)\n4,4\n8,8\n')
                args += ['--custom-filaments', str(self.path)]
            result = subprocess.run(args, cwd=self.temp.name, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = pd.read_excel(Path(self.temp.name)/'vf_thresholds.xlsx')
            expected = 15 * 10**(-.5*math.log10(15/.4)/7) if profile == 'rat' else 8/math.sqrt(2)
            self.assertAlmostEqual(output.threshold_50.iloc[0], expected)
            self.assertEqual(output.vf_filament_set.iloc[0], profile)
            self.assertEqual(output.vf_log_column.iloc[0], 'Log_new')
        result = subprocess.run([sys.executable, str(ROOT/'run.py'), '--compute', '--filament-set', 'custom'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--custom-filaments', result.stderr)


class GuiFilamentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_profile_switch_worker_and_restore(self):
        from src.gui.data_input import DataInputPanel, ThresholdWorker
        state = AnalysisState(filament_ref_path=str(REFERENCE))
        panel = DataInputPanel(state)
        self.addCleanup(panel.close)
        panel.filament_set_combo.setCurrentIndex(1)
        self.assertEqual(state.filament_set, 'rat')
        self.assertIn('0.224861610', panel.filament_status.text())
        worker = ThresholdWorker(pd.DataFrame({'xo_series':['OX'], 'last_filament':[8]}),
                                 state._filament_info, state._series_stats, 'xo_series', 'last_filament', 'Log_new')
        results, errors = [], []
        worker.finished.connect(results.append)
        worker.error.connect(errors.append)
        worker.run()
        self.assertFalse(errors)
        self.assertAlmostEqual(results[0].threshold_50.iloc[0], 15 * 10**(-.5*math.log10(15/.4)/7))
        self.assertEqual(results[0].vf_filament_set.iloc[0], 'rat')
        panel.filament_set_combo.setCurrentIndex(2)
        self.assertIsNone(state._filament_info)  # Cannot reuse previous valid ladder.
        self.assertFalse(panel.compute_btn.isEnabled())
        panel.state = AnalysisState(filament_ref_path=str(REFERENCE), filament_set='rat', log_column='Log')
        panel.restore_filament_settings()
        self.assertTrue(panel.log_new_radio.isChecked())
        self.assertFalse(panel.log_old_radio.isEnabled())
        self.assertEqual(panel.state.log_column, 'Log_new')
        self.assertEqual(panel.filament_set_combo.currentData(), 'rat')
        panel.filament_set_combo.setCurrentIndex(0)
        panel._load_filament_ref('/missing.xlsx')
        self.assertIsNone(panel.state._filament_info)
        self.assertFalse(panel.compute_btn.isEnabled())


if __name__ == '__main__':
    unittest.main()
