import datetime
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

import h5py
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import (
	LogPile, LogEntry, LogFormat, LogLevelDefinition,
	_to_epoch_ns, _epoch_ns_to_datetime, _detect_pylogfile_format,
	INFO, WARNING,
)
from colorama import Fore


class TestToEpochNs(unittest.TestCase):
	def test_small_int_treated_as_seconds(self):
		# 1_700_000_000 seconds is well under the 1e14 "already ns" heuristic
		ns = _to_epoch_ns(1_700_000_000)
		self.assertEqual(ns, 1_700_000_000 * 1_000_000_000)

	def test_large_int_treated_as_already_ns(self):
		already_ns = 1_700_000_000 * 1_000_000_000
		self.assertEqual(_to_epoch_ns(already_ns), already_ns)

	def test_float_seconds(self):
		ns = _to_epoch_ns(1_700_000_000.5)
		self.assertEqual(ns, int(1_700_000_000.5 * 1_000_000_000))

	def test_naive_datetime_treated_as_utc(self):
		dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
		ns = _to_epoch_ns(dt)
		expected = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1_000_000_000)
		self.assertEqual(ns, expected)

	def test_aware_datetime_uses_its_own_tzinfo(self):
		dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
		ns = _to_epoch_ns(dt)
		expected = int(dt.timestamp() * 1_000_000_000)
		self.assertEqual(ns, expected)

	def test_iso_string_is_parsed(self):
		ns = _to_epoch_ns("2024-01-01 12:00:00.000000")
		expected = _to_epoch_ns(datetime.datetime(2024, 1, 1, 12, 0, 0))
		self.assertEqual(ns, expected)

	def test_round_trip_with_epoch_ns_to_datetime(self):
		original = datetime.datetime(2024, 6, 15, 8, 30, 0, 123456, tzinfo=datetime.timezone.utc)
		ns = _to_epoch_ns(original)
		restored = _epoch_ns_to_datetime(ns)
		self.assertEqual(restored, original)


class TestDetectPylogfileFormat(unittest.TestCase):
	def test_matching_standard_non_compressed_encoding_returns_v0(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "weird.h5")
			with h5py.File(path, "w") as fh:
				mfi = fh.create_group("_file_info_")
				mfi.attrs["file_standard"] = "pylogfile.logpile"
				mfi.attrs["encoding"] = "something-else"
			with h5py.File(path, "r") as fh:
				self.assertEqual(_detect_pylogfile_format(fh), "0.0")

	def test_heuristic_detects_compressed_layout_without_file_info(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "no_file_info.h5")
			with h5py.File(path, "w") as fh:
				g = fh.create_group("logs")
				str_dt = h5py.string_dtype(encoding="utf-8")
				g.create_dataset("message_table", data=np.asarray([], dtype=object), dtype=str_dt)
				g.create_dataset("detail_table", data=np.asarray([], dtype=object), dtype=str_dt)
				g.create_dataset("message_id", data=np.asarray([], dtype=np.int32))
				g.create_dataset("detail_id", data=np.asarray([], dtype=np.int32))
				g.create_dataset("timestamp_ns", data=np.asarray([], dtype=np.int64))
				g.create_dataset("level", data=np.asarray([], dtype=np.int16))
			with h5py.File(path, "r") as fh:
				self.assertEqual(_detect_pylogfile_format(fh), "1.0")


class TestLogEntryStrColorPaths(unittest.TestCase):
	def test_show_color_help_prints_debug_info_without_crashing(self):
		levels = [LogLevelDefinition(INFO, "INFO", label_color=Fore.GREEN)]
		e = LogEntry(level=INFO, message="msg")
		fmt = LogFormat(show_color_help=True)
		buf = io.StringIO()
		with redirect_stdout(buf):
			rendered = e.str(fmt, levels)
		self.assertIn("Default colors, from LogFormat object", buf.getvalue())
		self.assertIn("After override from LogLevelDefinition", buf.getvalue())
		self.assertIn("After override from LogFormat Overrides", buf.getvalue())
		self.assertIn("msg", rendered)

	def test_all_five_level_definition_color_slots_apply(self):
		ld = LogLevelDefinition(
			INFO, "INFO",
			main_color=Fore.RED, bold_color=Fore.GREEN, quiet_color=Fore.BLUE,
			alt_color=Fore.YELLOW, label_color=Fore.CYAN,
		)
		e = LogEntry(level=INFO, message="hi")
		rendered = e.str(LogFormat(), [ld])
		self.assertIn(Fore.CYAN, rendered)  # label color wraps the level name

	def test_color_overrides_dict_applies_all_five_slots(self):
		fmt = LogFormat()
		fmt.color_overrides = {
			INFO: {
				"main": Fore.RED, "bold": Fore.GREEN, "quiet": Fore.BLUE,
				"alt": Fore.YELLOW, "label": Fore.MAGENTA,
			}
		}
		e = LogEntry(level=INFO, message="hi")
		rendered = e.str(fmt, [LogLevelDefinition(INFO, "INFO")])
		self.assertIn(Fore.MAGENTA, rendered)  # label
		self.assertIn(Fore.RED, rendered)  # main/return color


class TestSetTerminalLevelDirectValue(unittest.TestCase):
	def test_int_value_sets_directly(self):
		lp = LogPile()
		lp.set_terminal_level(WARNING)
		self.assertEqual(lp.terminal_level, WARNING)

	def test_float_value_is_coerced_to_int(self):
		lp = LogPile()
		lp.set_terminal_level(30.0)
		self.assertEqual(lp.terminal_level, 30)
		self.assertIsInstance(lp.terminal_level, int)


class TestSaveTxtStub(unittest.TestCase):
	def test_is_currently_a_no_op(self):
		lp = LogPile()
		self.assertIsNone(lp.save_txt())


class TestLoadV1CorruptionHandling(unittest.TestCase):
	def _make_valid_v1_file(self, tmpdir):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.info("a")
		lp.warning("b")
		path = os.path.join(tmpdir, "valid.plflog")
		lp.save_plflog(path, file_version="1.0")
		return path

	def test_missing_file_info_raises(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = self._make_valid_v1_file(tmpdir)
			with h5py.File(path, "a") as fh:
				del fh["_file_info_"]
			lp = LogPile()
			with self.assertRaisesRegex(ValueError, "_file_info_"):
				lp.load_plflog(path)

	def test_wrong_file_standard_raises(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = self._make_valid_v1_file(tmpdir)
			with h5py.File(path, "a") as fh:
				fh["_file_info_"].attrs["file_standard"] = "some.other.standard"
			lp = LogPile()
			with self.assertRaisesRegex(ValueError, "file_standard"):
				lp.load_plflog(path)

	def test_wrong_encoding_raises(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = self._make_valid_v1_file(tmpdir)
			with h5py.File(path, "a") as fh:
				fh["_file_info_"].attrs["encoding"] = "uncompressed"
			lp = LogPile()
			# _detect_pylogfile_format now routes this to the v0 loader, which
			# will fail differently (missing legacy datasets) - either way it
			# must not silently succeed with wrong data.
			with self.assertRaises(Exception):
				lp.load_plflog(path)

	def test_missing_required_dataset_raises(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = self._make_valid_v1_file(tmpdir)
			with h5py.File(path, "a") as fh:
				del fh["logs"]["timestamp_ns"]
			lp = LogPile()
			with self.assertRaisesRegex(ValueError, "missing datasets"):
				lp.load_plflog(path)

	def test_out_of_range_message_id_raises(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = self._make_valid_v1_file(tmpdir)
			with h5py.File(path, "a") as fh:
				fh["logs"]["message_id"][0] = 9999
			lp = LogPile()
			with self.assertRaisesRegex(ValueError, "message_id"):
				lp.load_plflog(path)


if __name__ == "__main__":
	unittest.main()
