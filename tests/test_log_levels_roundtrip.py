import os
import sys
import tempfile
import unittest

import h5py

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import LogLevelDefinition, LogPile


class TestLogLevelRoundTrip(unittest.TestCase):
    def _make_logpile(self):
        custom_levels = [
            LogLevelDefinition(1, "TRACE", main_color="M1", bold_color="B1", quiet_color="Q1", alt_color="A1", label_color="L1"),
            LogLevelDefinition(2, "NOTICE", main_color="M2", bold_color="B2", quiet_color="Q2", alt_color="A2", label_color="L2"),
        ]
        lp = LogPile(level_list=custom_levels)
        lp.terminal_output_enable = False
        lp.add_log(1, "hello", detail="world")
        return lp, custom_levels

    def test_round_trip_log_levels(self):
        lp, custom_levels = self._make_logpile()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "levels.plflog")
            lp.save_plflog(path, file_version="1.0")

            lp_loaded = LogPile()
            lp_loaded.terminal_output_enable = False
            lp_loaded.load_plflog(path)

            self.assertEqual(len(lp_loaded.log_levels), len(custom_levels))
            for got, exp in zip(lp_loaded.log_levels, custom_levels):
                self.assertEqual(got.level_int, exp.level_int)
                self.assertEqual(got.level_name, exp.level_name)
                self.assertEqual(got.main_color, exp.main_color)
                self.assertEqual(got.bold_color, exp.bold_color)
                self.assertEqual(got.quiet_color, exp.quiet_color)
                self.assertEqual(got.alt_color, exp.alt_color)
                self.assertEqual(got.label_color, exp.label_color)

    def test_corrupted_log_levels_raise(self):
        lp, _ = self._make_logpile()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "corrupt.plflog")
            lp.save_plflog(path, file_version="1.0")

            with h5py.File(path, "a") as fh:
                del fh["log_levels"]["level_name"]

            lp_loaded = LogPile()
            lp_loaded.terminal_output_enable = False
            with self.assertRaises(ValueError):
                lp_loaded.load_plflog(path)


if __name__ == "__main__":
    unittest.main()
