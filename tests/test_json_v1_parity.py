import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import LogPile, LogLevelDefinition, are_equivalent_piles
from colorama import Fore


def make_sample_pile():
	custom_levels = [
		LogLevelDefinition(1, "TRACE", main_color=Fore.MAGENTA, label_color=Fore.MAGENTA),
		LogLevelDefinition(10, "DEBUG"),
		LogLevelDefinition(20, "INFO", label_color=Fore.GREEN),
		LogLevelDefinition(25, "NOTICE", label_color=Fore.CYAN),
	]
	pile = LogPile(level_list=custom_levels)
	pile.terminal_output_enable = False
	pile.add_log(1, "trace entry", detail="trace detail")
	pile.add_log(20, "info entry")
	pile.add_log(25, "notice entry", detail="notice detail")
	return pile, custom_levels


class TestJsonSchema(unittest.TestCase):
	def setUp(self):
		self.pile, self.custom_levels = make_sample_pile()
		self.tmpdir = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmpdir.cleanup)
		self.path = os.path.join(self.tmpdir.name, "test.json")
		self.pile.save_json(self.path)

	def test_json_has_file_info(self):
		import json
		with open(self.path) as fh:
			data = json.load(fh)
		self.assertEqual(data["file_info"]["file_standard"], "pylogfile.logpile")
		self.assertEqual(data["file_info"]["encoding"], "json")
		self.assertIn("log_levels", data)
		self.assertIn("logs", data)

	def test_json_log_levels_include_colors(self):
		import json
		with open(self.path) as fh:
			data = json.load(fh)
		by_name = {ld["level_name"]: ld for ld in data["log_levels"]}
		self.assertEqual(by_name["NOTICE"]["level_int"], 25)
		self.assertEqual(by_name["NOTICE"]["label_color"], Fore.CYAN)
		self.assertEqual(by_name["TRACE"]["main_color"], Fore.MAGENTA)

	def test_round_trip_logs_and_levels(self):
		loaded = LogPile()
		loaded.terminal_output_enable = False
		self.assertTrue(loaded.load_json(self.path))

		self.assertTrue(are_equivalent_piles(self.pile, loaded))

		self.assertEqual(len(loaded.log_levels), len(self.custom_levels))
		for got, exp in zip(loaded.log_levels, self.custom_levels):
			self.assertEqual(got.level_int, exp.level_int)
			self.assertEqual(got.level_name, exp.level_name)
			self.assertEqual(got.main_color, exp.main_color)
			self.assertEqual(got.label_color, exp.label_color)

	def test_round_trip_matches_plflog_v1_content(self):
		""" save_json() is documented to carry the same data as
		save_plflog(file_version="1.0") - verify both round trip to
		equivalent LogPiles. """
		plf_path = os.path.join(self.tmpdir.name, "test.plflog")
		self.pile.save_plflog(plf_path, file_version="1.0")

		from_json = LogPile()
		from_json.terminal_output_enable = False
		from_json.load_json(self.path)

		from_plflog = LogPile()
		from_plflog.terminal_output_enable = False
		from_plflog.load_plflog(plf_path)

		self.assertTrue(are_equivalent_piles(from_json, from_plflog))
		self.assertEqual(
			[ld.level_name for ld in from_json.log_levels],
			[ld.level_name for ld in from_plflog.log_levels],
		)


class TestJsonValidation(unittest.TestCase):
	def test_rejects_missing_file_info(self):
		import json
		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "old_schema.json")
			with open(path, "w") as fh:
				json.dump({"logs": []}, fh)

			lp = LogPile()
			lp.terminal_output_enable = False
			with self.assertRaises(ValueError):
				lp.load_json(path)

	def test_rejects_wrong_encoding(self):
		import json
		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "wrong_encoding.json")
			with open(path, "w") as fh:
				json.dump({
					"file_info": {"file_standard": "pylogfile.logpile", "encoding": "not-json"},
					"log_levels": [],
					"logs": [],
				}, fh)

			lp = LogPile()
			lp.terminal_output_enable = False
			with self.assertRaises(ValueError):
				lp.load_json(path)


class TestAutosaveRemoved(unittest.TestCase):
	def test_no_autosave_attributes(self):
		lp = LogPile()
		for attr in ("autosave_enable", "autosave_period_s", "autosave_level", "autosave_format", "filename"):
			self.assertFalse(hasattr(lp, attr), f"LogPile still has removed attribute '{attr}'")

	def test_no_autosave_methods(self):
		self.assertFalse(hasattr(LogPile, "begin_autosave"))

	def test_no_class_format_constants(self):
		self.assertFalse(hasattr(LogPile, "JSON"))
		self.assertFalse(hasattr(LogPile, "TXT"))

	def test_constructor_has_no_filename_or_autosave_params(self):
		import inspect
		sig = inspect.signature(LogPile.__init__)
		self.assertNotIn("filename", sig.parameters)
		self.assertNotIn("autosave", sig.parameters)


class TestHdfMethodsRemoved(unittest.TestCase):
	def test_no_save_hdf_or_load_hdf(self):
		lp = LogPile()
		self.assertFalse(hasattr(lp, "save_hdf"))
		self.assertFalse(hasattr(lp, "load_hdf"))


if __name__ == "__main__":
	unittest.main()
