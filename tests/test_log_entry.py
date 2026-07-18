import datetime
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import (
	LogEntry, LogFormat, SortConditions, LogLevelDefinition,
	INFO, WARNING, ERROR,
)


class TestLogEntryInit(unittest.TestCase):
	def test_defaults(self):
		e = LogEntry()
		self.assertEqual(e.level, 0)
		self.assertEqual(e.message, "")
		self.assertEqual(e.detail, "")
		self.assertIsInstance(e.timestamp, datetime.datetime)

	def test_explicit_values(self):
		e = LogEntry(level=INFO, message="hello", detail="world")
		self.assertEqual(e.level, INFO)
		self.assertEqual(e.message, "hello")
		self.assertEqual(e.detail, "world")

	def test_none_message_and_detail_become_empty_string(self):
		e = LogEntry(level=INFO, message=None, detail=None)
		self.assertEqual(e.message, "")
		self.assertEqual(e.detail, "")

	def test_timestamp_is_set_near_now(self):
		before = datetime.datetime.now()
		e = LogEntry()
		after = datetime.datetime.now()
		self.assertLessEqual(before, e.timestamp)
		self.assertLessEqual(e.timestamp, after)


class TestLogEntryDictRoundTrip(unittest.TestCase):
	def test_get_dict_contains_expected_keys(self):
		e = LogEntry(level=WARNING, message="msg", detail="dtl")
		d = e.get_dict()
		self.assertEqual(d["message"], "msg")
		self.assertEqual(d["detail"], "dtl")
		self.assertEqual(d["level"], WARNING)
		self.assertEqual(d["timestamp"], e.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'))

	def test_get_json_matches_get_dict(self):
		e = LogEntry(level=ERROR, message="boom", detail="stack trace")
		parsed = json.loads(e.get_json())
		self.assertEqual(parsed, e.get_dict())

	def test_init_dict_round_trip(self):
		original = LogEntry(level=INFO, message="round trip", detail="detail here")
		d = original.get_dict()

		restored = LogEntry()
		ok = restored.init_dict(d)

		self.assertTrue(ok)
		self.assertEqual(restored.level, original.level)
		self.assertEqual(restored.message, original.message)
		self.assertEqual(restored.detail, original.detail)
		# Sub-microsecond precision is lost by strftime/strptime, but should
		# match to the microsecond.
		self.assertEqual(restored.timestamp, original.timestamp)

	def test_init_dict_missing_key_returns_false(self):
		e = LogEntry()
		for missing in ("level", "message", "detail", "timestamp"):
			d = {"level": 10, "message": "m", "detail": "d", "timestamp": "2024-01-01 00:00:00.000000"}
			del d[missing]
			self.assertFalse(e.init_dict(d), f"expected failure when '{missing}' is missing")

	def test_init_dict_unconvertible_level_falls_back_to_zero(self):
		e = LogEntry()
		d = {"level": "not-a-number", "message": "m", "detail": "d", "timestamp": "2024-01-01 00:00:00.000000"}
		buf = io.StringIO()
		with redirect_stdout(buf):
			ok = e.init_dict(d)
		self.assertTrue(ok)  # still succeeds, just with level coerced to 0
		self.assertEqual(e.level, 0)
		self.assertIn("Failed to initialize log entry", buf.getvalue())

	def test_init_dict_level_as_numeric_string_converts(self):
		e = LogEntry()
		d = {"level": "25", "message": "m", "detail": "d", "timestamp": "2024-01-01 00:00:00.000000"}
		self.assertTrue(e.init_dict(d))
		self.assertEqual(e.level, 25)


class TestLogEntryStr(unittest.TestCase):
	def test_str_contains_message_and_level_name(self):
		levels = [LogLevelDefinition(INFO, "INFO")]
		e = LogEntry(level=INFO, message="hello there")
		rendered = e.str(LogFormat(use_color=False), levels)
		self.assertIn("INFO", rendered)
		self.assertIn("hello there", rendered)

	def test_str_hides_detail_by_default(self):
		levels = [LogLevelDefinition(INFO, "INFO")]
		e = LogEntry(level=INFO, message="msg", detail="secret detail")
		rendered = e.str(LogFormat(use_color=False, show_detail=False), levels)
		self.assertNotIn("secret detail", rendered)

	def test_str_shows_detail_when_enabled(self):
		levels = [LogLevelDefinition(INFO, "INFO")]
		e = LogEntry(level=INFO, message="msg", detail="visible detail")
		rendered = e.str(LogFormat(use_color=False, show_detail=True), levels)
		self.assertIn("visible detail", rendered)

	def test_str_strips_newlines_by_default(self):
		levels = [LogLevelDefinition(INFO, "INFO")]
		e = LogEntry(level=INFO, message="line1\nline2")
		rendered = e.str(LogFormat(use_color=False), levels)
		self.assertNotIn("\n", rendered.rstrip("\n"))
		self.assertIn("line1line2", rendered)

	def test_str_falls_back_to_raw_level_number_when_unregistered(self):
		e = LogEntry(level=12345, message="custom")
		rendered = e.str(LogFormat(use_color=False), [LogLevelDefinition(INFO, "INFO")])
		self.assertIn("12345", rendered)
		self.assertNotIn("None", rendered)

	def test_str_works_with_no_level_list(self):
		# level_list defaults to None; find_level_in_list treats that the same
		# as "not found", so str() falls back to the raw level number.
		e = LogEntry(level=INFO, message="msg")
		rendered = e.str(LogFormat(use_color=False))
		self.assertIn("msg", rendered)
		self.assertIn(str(INFO), rendered)


class TestMatchesSort(unittest.TestCase):
	def setUp(self):
		self.now = datetime.datetime.now()
		self.entry = LogEntry(level=INFO, message="the quick brown fox", detail="jumps over lazy dog")
		self.entry.timestamp = self.now

	def test_no_conditions_matches(self):
		self.assertTrue(self.entry.matches_sort(SortConditions()))

	def test_time_range_containing_entry_matches(self):
		sc = SortConditions()
		sc.time_start = self.now - datetime.timedelta(seconds=1)
		sc.time_end = self.now + datetime.timedelta(seconds=1)
		self.assertTrue(self.entry.matches_sort(sc))

	def test_time_range_excluding_entry_fails(self):
		sc = SortConditions()
		sc.time_start = self.now + datetime.timedelta(seconds=1)
		sc.time_end = self.now + datetime.timedelta(seconds=2)
		self.assertFalse(self.entry.matches_sort(sc))

	def test_only_one_time_bound_set_is_ignored(self):
		# Per matches_sort's implementation, both time_start AND time_end must
		# be set for time filtering to apply at all.
		sc = SortConditions()
		sc.time_start = self.now + datetime.timedelta(days=100)  # would exclude, if applied alone
		self.assertTrue(self.entry.matches_sort(sc))

	def test_contains_and_all_present_matches(self):
		sc = SortConditions()
		sc.contains_and = ["quick", "lazy"]
		self.assertTrue(self.entry.matches_sort(sc))

	def test_contains_and_one_missing_fails(self):
		sc = SortConditions()
		sc.contains_and = ["quick", "nonexistent"]
		self.assertFalse(self.entry.matches_sort(sc))

	def test_contains_and_checks_message_or_detail(self):
		sc = SortConditions()
		sc.contains_and = ["quick", "jumps"]  # "quick" in message, "jumps" in detail
		self.assertTrue(self.entry.matches_sort(sc))

	def test_contains_or_one_present_matches(self):
		sc = SortConditions()
		sc.contains_or = ["nonexistent", "quick"]
		self.assertTrue(self.entry.matches_sort(sc))

	def test_contains_or_none_present_fails(self):
		sc = SortConditions()
		sc.contains_or = ["nonexistent", "also-nonexistent"]
		self.assertFalse(self.entry.matches_sort(sc))

	def test_combined_time_and_contains_conditions(self):
		sc = SortConditions()
		sc.time_start = self.now - datetime.timedelta(seconds=1)
		sc.time_end = self.now + datetime.timedelta(seconds=1)
		sc.contains_and = ["quick"]
		sc.contains_or = ["fox", "nonexistent"]
		self.assertTrue(self.entry.matches_sort(sc))

		# Now make the time range fail; overall match should fail even though
		# the contains conditions are satisfied.
		sc.time_end = self.now - datetime.timedelta(seconds=1)
		self.assertFalse(self.entry.matches_sort(sc))


if __name__ == "__main__":
	unittest.main()
