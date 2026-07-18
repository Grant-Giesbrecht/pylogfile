import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import (
	find_level_in_list, get_default_levels, LogLevelDefinition,
	_level_definition_to_dict, _level_definition_from_dict,
	LOWDEBUG, DEBUG, INFO, WARNING, ERROR, CRITICAL,
)
from colorama import Fore


class TestFindLevelInList(unittest.TestCase):
	def setUp(self):
		self.levels = get_default_levels()

	def test_find_by_int(self):
		idx = find_level_in_list(WARNING, self.levels)
		self.assertEqual(self.levels[idx].level_name, "WARNING")

	def test_find_by_str(self):
		idx = find_level_in_list("WARNING", self.levels)
		self.assertEqual(self.levels[idx].level_int, WARNING)

	def test_str_lookup_is_case_sensitive(self):
		# level_name comparison is a plain ==, so this is expected to miss.
		self.assertIsNone(find_level_in_list("warning", self.levels))

	def test_int_not_found_returns_none(self):
		self.assertIsNone(find_level_in_list(99999, self.levels))

	def test_str_not_found_returns_none(self):
		self.assertIsNone(find_level_in_list("NOT_A_LEVEL", self.levels))

	def test_none_level_list_returns_none(self):
		self.assertIsNone(find_level_in_list(INFO, None))
		self.assertIsNone(find_level_in_list("INFO", None))

	def test_empty_level_list_returns_none(self):
		self.assertIsNone(find_level_in_list(INFO, []))


class TestGetDefaultLevels(unittest.TestCase):
	def test_returns_six_levels_in_ascending_order(self):
		levels = get_default_levels()
		self.assertEqual(len(levels), 6)
		ints = [ld.level_int for ld in levels]
		self.assertEqual(ints, sorted(ints))

	def test_names_and_ints_match_module_constants(self):
		levels = get_default_levels()
		by_name = {ld.level_name: ld.level_int for ld in levels}
		self.assertEqual(by_name["LOWDEBUG"], LOWDEBUG)
		self.assertEqual(by_name["DEBUG"], DEBUG)
		self.assertEqual(by_name["INFO"], INFO)
		self.assertEqual(by_name["WARNING"], WARNING)
		self.assertEqual(by_name["ERROR"], ERROR)
		self.assertEqual(by_name["CRITICAL"], CRITICAL)

	def test_each_call_returns_independent_list(self):
		a = get_default_levels()
		b = get_default_levels()
		a.append(LogLevelDefinition(1, "EXTRA"))
		self.assertEqual(len(b), 6)


class TestLogLevelDefinition(unittest.TestCase):
	def test_construction_defaults(self):
		ld = LogLevelDefinition(20, "INFO")
		self.assertEqual(ld.level_int, 20)
		self.assertEqual(ld.level_name, "INFO")
		self.assertEqual(ld.main_color, "")
		self.assertEqual(ld.bold_color, "")
		self.assertEqual(ld.quiet_color, "")
		self.assertEqual(ld.alt_color, "")
		self.assertEqual(ld.label_color, "")

	def test_construction_with_colors(self):
		ld = LogLevelDefinition(
			25, "NOTICE",
			main_color=Fore.RED, bold_color=Fore.GREEN, quiet_color=Fore.BLUE,
			alt_color=Fore.YELLOW, label_color=Fore.CYAN,
		)
		self.assertEqual(ld.main_color, Fore.RED)
		self.assertEqual(ld.bold_color, Fore.GREEN)
		self.assertEqual(ld.quiet_color, Fore.BLUE)
		self.assertEqual(ld.alt_color, Fore.YELLOW)
		self.assertEqual(ld.label_color, Fore.CYAN)


class TestLevelDefinitionDictSerialization(unittest.TestCase):
	def test_to_dict_has_all_fields(self):
		ld = LogLevelDefinition(25, "NOTICE", label_color=Fore.CYAN)
		d = _level_definition_to_dict(ld)
		self.assertEqual(d, {
			"level_int": 25,
			"level_name": "NOTICE",
			"main_color": "",
			"bold_color": "",
			"quiet_color": "",
			"alt_color": "",
			"label_color": Fore.CYAN,
		})

	def test_from_dict_round_trip(self):
		original = LogLevelDefinition(25, "NOTICE", main_color=Fore.RED, label_color=Fore.CYAN)
		restored = _level_definition_from_dict(_level_definition_to_dict(original))
		self.assertEqual(restored.level_int, original.level_int)
		self.assertEqual(restored.level_name, original.level_name)
		self.assertEqual(restored.main_color, original.main_color)
		self.assertEqual(restored.label_color, original.label_color)

	def test_from_dict_tolerates_missing_color_keys(self):
		ld = _level_definition_from_dict({"level_int": 5, "level_name": "TRACE"})
		self.assertEqual(ld.level_int, 5)
		self.assertEqual(ld.level_name, "TRACE")
		self.assertEqual(ld.main_color, "")


if __name__ == "__main__":
	unittest.main()
