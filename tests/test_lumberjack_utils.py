import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# lumberjack.py parses sys.argv (and loads its help JSON) as a *module-level*
# side effect on import - it has no `if __name__ == "__main__":` guard, and
# `main()` must be called explicitly. A valid argv must be in place before
# the first import anywhere in the process, or the import itself raises
# SystemExit via argparse.
sys.argv = ["lumber", "dummy.plflog", "--nocli"]

from pylogfile.scripts.lumberjack import (
	barstr, str_to_bool, StringIdx, parseTwoIdx, parseIdx, ensureWhitespace, help_data,
)


class TestBarstr(unittest.TestCase):
	def test_default_width_pads_both_sides(self):
		result = barstr("Hi")
		self.assertEqual(len(result), 80)
		self.assertTrue(result.startswith("*"))
		self.assertTrue(result.endswith("*"))
		self.assertIn(" Hi ", result)

	def test_custom_width(self):
		self.assertEqual(barstr("Hi", width=10), "*** Hi ***")

	def test_pad_false_omits_space_padding(self):
		self.assertEqual(barstr("Hi", width=10, pad=False), "****Hi****")

	def test_custom_bar_character(self):
		self.assertEqual(barstr("Hi", width=10, bc="-"), "--- Hi ---")

	def test_text_already_at_or_over_width_only_gets_space_padding(self):
		text = "a very long piece of text indeed"
		self.assertEqual(barstr(text, width=10), f" {text} ")


class TestStrToBool(unittest.TestCase):
	def test_recognizes_true_values(self):
		self.assertTrue(str_to_bool("1"))
		self.assertTrue(str_to_bool("ON"))
		self.assertTrue(str_to_bool("on"))
		self.assertTrue(str_to_bool("true"))
		self.assertTrue(str_to_bool("TRUE"))

	def test_recognizes_false_values(self):
		self.assertFalse(str_to_bool("0"))
		self.assertFalse(str_to_bool("off"))
		self.assertFalse(str_to_bool("OFF"))
		self.assertFalse(str_to_bool("false"))
		self.assertFalse(str_to_bool("FALSE"))

	def test_unrecognized_value_strict_returns_none(self):
		self.assertIsNone(str_to_bool("bogus", strict=True))

	def test_unrecognized_value_non_strict_returns_false(self):
		self.assertFalse(str_to_bool("bogus", strict=False))

	def test_substring_matching_quirk(self):
		# str_to_bool checks '1' in val / 'ON' in val.upper() etc as plain
		# substring tests, not equality - so a value like "off10" matches the
		# '1' in val branch (checked first) and is treated as True, even
		# though a human would read it as "off". Documenting current behavior.
		self.assertTrue(str_to_bool("off10"))


class TestStringIdx(unittest.TestCase):
	def test_str_and_repr(self):
		si = StringIdx("hello", 3)
		self.assertEqual(str(si), '[3]"hello"')
		self.assertEqual(repr(si), '[3]"hello"')

	def test_default_idx_end(self):
		si = StringIdx("hello", 3)
		self.assertEqual(si.idx_end, -1)

	def test_explicit_idx_end(self):
		si = StringIdx("hello", 3, idx_end=8)
		self.assertEqual(si.idx_end, 8)


class TestParseTwoIdx(unittest.TestCase):
	def test_splits_on_single_delimiter(self):
		self.assertEqual(list(parseTwoIdx("a b c", " ")), [(0, 1), (2, 3), (4, 5)])

	def test_collapses_consecutive_delimiters(self):
		self.assertEqual(list(parseTwoIdx("a b  c", " ")), [(0, 1), (2, 3), (5, 6)])

	def test_no_delimiters_present_yields_whole_string(self):
		self.assertEqual(list(parseTwoIdx("hello", " ")), [(0, 5)])

	def test_empty_string_yields_nothing(self):
		self.assertEqual(list(parseTwoIdx("", " ")), [])

	def test_multiple_delimiter_characters(self):
		self.assertEqual(list(parseTwoIdx("a,b c", ", ")), [(0, 1), (2, 3), (4, 5)])


class TestParseIdx(unittest.TestCase):
	def test_splits_into_string_idx_objects(self):
		result = parseIdx("hello world foo")
		self.assertEqual([r.str for r in result], ["hello", "world", "foo"])
		self.assertEqual([r.idx for r in result], [0, 6, 12])
		self.assertEqual([r.idx_end for r in result], [5, 11, 15])

	def test_custom_delimiters(self):
		result = parseIdx("a,b,c", delims=",")
		self.assertEqual([r.str for r in result], ["a", "b", "c"])

	def test_empty_input(self):
		self.assertEqual(parseIdx(""), [])


class TestEnsureWhitespace(unittest.TestCase):
	def test_adds_missing_whitespace_around_target(self):
		self.assertEqual(ensureWhitespace("a>b", ">"), "a > b")

	def test_leaves_already_spaced_target_unchanged(self):
		self.assertEqual(ensureWhitespace("a > b", ">"), "a > b")

	def test_multiple_target_characters(self):
		self.assertEqual(ensureWhitespace(">a<", "><"), "> a <")

	def test_adjacent_targets_each_get_padded(self):
		self.assertEqual(ensureWhitespace("a>>b", ">"), "a > > b")

	def test_target_at_string_boundaries(self):
		self.assertEqual(ensureWhitespace(">start", ">"), "> start")
		self.assertEqual(ensureWhitespace("end>", ">"), "end >")


class TestHelpDataLoaded(unittest.TestCase):
	""" Regression coverage for the packaging bug fixed earlier this session:
	lumberjack_help.json must actually be importable via importlib.resources,
	not silently fall back to an empty dict. """

	def test_help_data_is_not_empty(self):
		self.assertGreater(len(help_data), 0)

	def test_help_data_has_expected_commands(self):
		for cmd in ("HELP", "EXIT", "SHOW", "INFO", "MIN-LEVEL", "MAX-LEVEL"):
			self.assertIn(cmd, help_data)

	def test_show_command_has_documented_flags(self):
		flags = {f["long"] for f in help_data["SHOW"]["flags"]}
		self.assertIn("--min", flags)
		self.assertIn("--max", flags)
		self.assertIn("--contains", flags)


if __name__ == "__main__":
	unittest.main()
