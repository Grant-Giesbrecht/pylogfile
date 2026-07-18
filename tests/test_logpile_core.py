import io
import os
import sys
import threading
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import (
	LogPile, LogLevelDefinition, DummyMutex, get_default_levels,
	LOWDEBUG, DEBUG, INFO, WARNING, ERROR, CRITICAL,
)


class TestLogPileConstruction(unittest.TestCase):
	def test_default_uses_real_locks(self):
		lp = LogPile()
		self.assertIsInstance(lp.log_mutex, type(threading.Lock()))
		self.assertIsInstance(lp.run_mutex, type(threading.Lock()))

	def test_use_mutex_false_uses_dummy_mutex(self):
		lp = LogPile(use_mutex=False)
		self.assertIsInstance(lp.log_mutex, DummyMutex)
		self.assertIsInstance(lp.run_mutex, DummyMutex)

	def test_no_level_list_uses_defaults(self):
		lp = LogPile()
		names = [ld.level_name for ld in lp.log_levels]
		self.assertEqual(names, ["LOWDEBUG", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

	def test_valid_level_list_is_used_verbatim(self):
		custom = [LogLevelDefinition(1, "TRACE")]
		lp = LogPile(level_list=custom)
		self.assertIs(lp.log_levels, custom)

	def test_invalid_level_list_silently_falls_back_to_defaults(self):
		# Documented current behavior: if any element isn't a
		# LogLevelDefinition, the whole list is rejected with no warning.
		bad = [LogLevelDefinition(1, "TRACE"), "not a LogLevelDefinition"]
		lp = LogPile(level_list=bad)
		names = [ld.level_name for ld in lp.log_levels]
		self.assertEqual(names, ["LOWDEBUG", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

	def test_default_terminal_level_is_info(self):
		lp = LogPile()
		self.assertEqual(lp.terminal_level, INFO)

	def test_starts_with_no_logs(self):
		lp = LogPile()
		self.assertEqual(lp.logs, [])


class TestSetEnableMutex(unittest.TestCase):
	def test_toggle_to_dummy_and_back(self):
		lp = LogPile(use_mutex=True)
		lp.set_enable_mutex(False)
		self.assertIsInstance(lp.log_mutex, DummyMutex)
		lp.set_enable_mutex(True)
		self.assertIsInstance(lp.log_mutex, type(threading.Lock()))

	def test_dummy_mutex_context_manager_does_not_raise(self):
		lp = LogPile(use_mutex=False)
		lp.terminal_output_enable = False
		lp.info("works fine without a real lock")
		self.assertEqual(len(lp.logs), 1)


class TestSetShowDetail(unittest.TestCase):
	def test_toggles_str_format_show_detail(self):
		lp = LogPile()
		self.assertFalse(lp.str_format.show_detail)
		lp.set_show_detail(True)
		self.assertTrue(lp.str_format.show_detail)
		lp.set_show_detail(False)
		self.assertFalse(lp.str_format.show_detail)


class TestConvenienceLoggingMethods(unittest.TestCase):
	def setUp(self):
		self.lp = LogPile()
		self.lp.terminal_output_enable = False

	def test_lowdebug(self):
		self.lp.lowdebug("m", detail="d")
		self.assertEqual((self.lp.logs[-1].level, self.lp.logs[-1].message, self.lp.logs[-1].detail), (LOWDEBUG, "m", "d"))

	def test_debug(self):
		self.lp.debug("m", detail="d")
		self.assertEqual(self.lp.logs[-1].level, DEBUG)

	def test_info(self):
		self.lp.info("m", detail="d")
		self.assertEqual(self.lp.logs[-1].level, INFO)

	def test_warning(self):
		self.lp.warning("m", detail="d")
		self.assertEqual(self.lp.logs[-1].level, WARNING)

	def test_error(self):
		self.lp.error("m", detail="d")
		self.assertEqual(self.lp.logs[-1].level, ERROR)

	def test_critical(self):
		self.lp.critical("m", detail="d")
		self.assertEqual(self.lp.logs[-1].level, CRITICAL)

	def test_add_log_appends_in_order(self):
		self.lp.info("first")
		self.lp.warning("second")
		self.assertEqual([l.message for l in self.lp.logs], ["first", "second"])


class TestTerminalOutputGating(unittest.TestCase):
	def test_terminal_output_disabled_prints_nothing(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		buf = io.StringIO()
		with redirect_stdout(buf):
			lp.critical("should not print")
		self.assertEqual(buf.getvalue(), "")
		self.assertEqual(len(lp.logs), 1)  # still recorded

	def test_level_below_terminal_level_is_recorded_but_not_printed(self):
		lp = LogPile()
		lp.terminal_output_enable = True
		lp.terminal_level = WARNING
		buf = io.StringIO()
		with redirect_stdout(buf):
			lp.info("below threshold")
		self.assertEqual(buf.getvalue(), "")
		self.assertEqual(len(lp.logs), 1)

	def test_level_at_or_above_terminal_level_is_printed(self):
		lp = LogPile()
		lp.terminal_output_enable = True
		lp.terminal_level = WARNING
		buf = io.StringIO()
		with redirect_stdout(buf):
			lp.warning("at threshold")
			lp.error("above threshold")
		output = buf.getvalue()
		self.assertIn("at threshold", output)
		self.assertIn("above threshold", output)


class TestToDict(unittest.TestCase):
	def test_matches_each_entrys_get_dict(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.info("a")
		lp.error("b", detail="d")

		d = lp.to_dict()
		self.assertEqual(d, [lp.logs[0].get_dict(), lp.logs[1].get_dict()])

	def test_empty_pile_returns_empty_list(self):
		lp = LogPile()
		self.assertEqual(lp.to_dict(), [])


if __name__ == "__main__":
	unittest.main()
