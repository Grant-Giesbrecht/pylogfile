import os
import sys
import tempfile
import unittest

import h5py

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pylogfile
from pylogfile.base import (
	LogPile, LogLevelDefinition, SortConditions,
	str_to_level, level_to_str, get_default_levels,
	DEBUG, INFO, WARNING,
)


class TestTopLevelPackageAPI(unittest.TestCase):
	def test_version_exposed(self):
		self.assertTrue(hasattr(pylogfile, "__version__"))
		self.assertIsInstance(pylogfile.__version__, str)

	def test_top_level_reexports(self):
		self.assertIs(pylogfile.LogPile, LogPile)
		self.assertIs(pylogfile.LogLevelDefinition, LogLevelDefinition)
		self.assertIs(pylogfile.SortConditions, SortConditions)

	def test_star_import_does_not_leak_third_party_names(self):
		ns = {}
		exec("from pylogfile.base import *", ns)
		for leaked in ("np", "h5py", "json", "datetime", "threading", "Fore", "Style", "Back", "dataclass", "field"):
			self.assertNotIn(leaked, ns, f"'{leaked}' leaked into caller namespace via import *")
		self.assertIn("LogPile", ns)


class TestSortConditionsIsolation(unittest.TestCase):
	def test_instances_do_not_share_list_state(self):
		a = SortConditions()
		b = SortConditions()
		a.contains_and.append("leaked")
		a.contains_or.append("also leaked")
		self.assertEqual(b.contains_and, [])
		self.assertEqual(b.contains_or, [])
		self.assertIsNot(a.contains_and, b.contains_and)
		self.assertIsNot(a.contains_or, b.contains_or)


class TestLevelLookupNotFound(unittest.TestCase):
	def setUp(self):
		self.levels = get_default_levels()

	def test_str_to_level_returns_none_when_missing(self):
		self.assertIsNone(str_to_level("NOT_A_REAL_LEVEL", self.levels))

	def test_level_to_str_returns_none_when_missing(self):
		self.assertIsNone(level_to_str(9999, self.levels))

	def test_str_to_level_found(self):
		self.assertEqual(str_to_level("WARNING", self.levels), WARNING)

	def test_level_to_str_found(self):
		self.assertEqual(level_to_str(WARNING, self.levels), "WARNING")


class TestSetTerminalLevel(unittest.TestCase):
	def test_unrecognized_level_string_is_rejected_not_minus_one(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		before = lp.terminal_level
		lp.set_terminal_level("NOT_A_REAL_LEVEL")
		# Must be left unchanged, and must never end up as -1/None (which would
		# make every future log print, or crash the `>=` comparison entirely).
		self.assertEqual(lp.terminal_level, before)
		self.assertIsNotNone(lp.terminal_level)

	def test_recognized_level_string_applies(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.set_terminal_level("WARNING")
		self.assertEqual(lp.terminal_level, WARNING)


class TestUnregisteredLevelSaveDoesNotCrash(unittest.TestCase):
	""" LogPile explicitly allows logging at levels that aren't registered in
	log_levels (see NOTE near the top of base.py). Saving must not crash just
	because str_to_level/level_to_str now return None instead of -1 for those
	entries. """

	def test_v1_save_with_unregistered_level(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.add_log(12345, "custom level entry")  # not in default levels

		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "custom.plflog")
			lp.save_plflog(path, file_version="1.0")  # must not raise

			with h5py.File(path, "r") as fh:
				self.assertEqual(int(fh["logs"]["level"][0]), 12345)

			lp2 = LogPile()
			lp2.terminal_output_enable = False
			self.assertTrue(lp2.load_plflog(path))
			self.assertEqual(lp2.logs[0].level, 12345)

	def test_v0_save_with_unregistered_level(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.add_log(12345, "custom level entry")

		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "custom_v0.plflog")
			lp.save_plflog(path, file_version="0.0")  # must not raise

	def test_entry_str_falls_back_to_raw_number_for_unregistered_level(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.add_log(12345, "custom level entry")
		rendered = lp.logs[0].str(lp.str_format, lp.log_levels)
		self.assertIn("12345", rendered)
		self.assertNotIn("None", rendered)


class TestJsonRoundTrip(unittest.TestCase):
	def test_save_and_load_json(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.info("hello json")

		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "test.log.json")
			lp.save_json(path)

			lp2 = LogPile()
			lp2.terminal_output_enable = False
			self.assertTrue(lp2.load_json(path))
			self.assertEqual(len(lp2.logs), 1)
			self.assertEqual(lp2.logs[0].message, "hello json")


if __name__ == "__main__":
	unittest.main()
