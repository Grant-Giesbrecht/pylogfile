import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import LogPile, LogFormat, SortConditions, INFO, WARNING, ERROR
from colorama import Fore

PLAIN = LogFormat(use_color=False)


def make_pile(n=5):
	lp = LogPile()
	lp.terminal_output_enable = False
	for i in range(n):
		lp.info(f"msg{i}", detail=f"detail{i}")
	return lp


def capture(lp, **kwargs):
	buf = io.StringIO()
	with redirect_stdout(buf):
		lp.show_logs(str_fmt=kwargs.pop("str_fmt", PLAIN), **kwargs)
	return buf.getvalue()


class TestShowLogsOrdering(unittest.TestCase):
	def test_default_order_is_most_recent_first(self):
		lp = make_pile(3)
		out = capture(lp)
		self.assertLess(out.index("msg2"), out.index("msg1"))
		self.assertLess(out.index("msg1"), out.index("msg0"))

	def test_from_beginning_shows_oldest_first(self):
		lp = make_pile(3)
		out = capture(lp, from_beginning=True)
		self.assertLess(out.index("msg0"), out.index("msg1"))
		self.assertLess(out.index("msg1"), out.index("msg2"))

	def test_empty_pile_prints_nothing_and_does_not_crash(self):
		lp = LogPile()
		out = capture(lp)
		self.assertEqual(out, "")


class TestShowLogsMaxNumber(unittest.TestCase):
	def test_zero_prints_nothing(self):
		lp = make_pile(3)
		out = capture(lp, max_number=0)
		self.assertEqual(out, "")

	def test_negative_prints_nothing(self):
		lp = make_pile(3)
		out = capture(lp, max_number=-1)
		self.assertEqual(out, "")

	def test_none_shows_all(self):
		lp = make_pile(5)
		out = capture(lp, max_number=None)
		for i in range(5):
			self.assertIn(f"msg{i}", out)

	def test_truncates_and_shows_ellipsis(self):
		lp = make_pile(5)
		out = capture(lp, max_number=2)
		# most-recent-first order: msg4, msg3 shown, then truncated
		self.assertIn("msg4", out)
		self.assertIn("msg3", out)
		self.assertNotIn("msg2", out)
		self.assertNotIn("msg1", out)
		self.assertNotIn("msg0", out)
		self.assertIn("...", out)


class TestShowLogsLevelFiltering(unittest.TestCase):
	def setUp(self):
		self.lp = LogPile()
		self.lp.terminal_output_enable = False
		self.lp.info("info msg")
		self.lp.warning("warning msg")
		self.lp.error("error msg")

	def test_min_level_excludes_lower(self):
		out = capture(self.lp, min_level=WARNING)
		self.assertNotIn("info msg", out)
		self.assertIn("warning msg", out)
		self.assertIn("error msg", out)

	def test_max_level_excludes_higher(self):
		out = capture(self.lp, max_level=WARNING)
		self.assertIn("info msg", out)
		self.assertIn("warning msg", out)
		self.assertNotIn("error msg", out)

	def test_min_and_max_level_narrows_to_range(self):
		out = capture(self.lp, min_level=WARNING, max_level=WARNING)
		self.assertNotIn("info msg", out)
		self.assertIn("warning msg", out)
		self.assertNotIn("error msg", out)


class TestShowLogsIndexDisplay(unittest.TestCase):
	# NOTE: the "[N]" index prefix is built with hardcoded Fore.WHITE codes
	# regardless of str_fmt.use_color, so even a "plain" str_fmt still gets
	# ANSI codes interspersed inside the brackets (e.g. "\x1b[37m[\x1b[37m0...").
	def _bracketed(self, n):
		return f"{Fore.WHITE}[{Fore.WHITE}{n}{Fore.WHITE}]"

	def test_show_index_true_includes_bracketed_index(self):
		lp = make_pile(2)
		out = capture(lp, show_index=True)
		self.assertIn(self._bracketed(0), out)
		self.assertIn(self._bracketed(1), out)

	def test_show_index_false_omits_index(self):
		lp = make_pile(2)
		out = capture(lp, show_index=False)
		self.assertNotIn(self._bracketed(0), out)
		self.assertNotIn(self._bracketed(1), out)


class TestShowLogsSortOrders(unittest.TestCase):
	def setUp(self):
		self.lp = LogPile()
		self.lp.terminal_output_enable = False
		self.lp.info("the quick brown fox")
		self.lp.info("jumps over the lazy dog")
		self.lp.info("pack my box with five dozen liquor jugs")

	def test_contains_or_filters(self):
		sc = SortConditions()
		sc.contains_or = ["fox"]
		out = capture(self.lp, sort_orders=sc)
		self.assertIn("quick brown fox", out)
		self.assertNotIn("lazy dog", out)
		self.assertNotIn("liquor jugs", out)

	def test_contains_and_requires_all_terms(self):
		sc = SortConditions()
		sc.contains_and = ["dozen", "jugs"]
		out = capture(self.lp, sort_orders=sc)
		self.assertIn("liquor jugs", out)
		self.assertNotIn("quick brown fox", out)
		self.assertNotIn("lazy dog", out)

	def test_index_range_filters_by_true_index_not_display_position(self):
		lp = make_pile(5)  # msg0..msg4
		sc = SortConditions()
		sc.index_start = 1
		sc.index_end = 3
		out = capture(lp, sort_orders=sc)
		self.assertNotIn("msg0", out)
		self.assertIn("msg1", out)
		self.assertIn("msg2", out)
		self.assertIn("msg3", out)
		self.assertNotIn("msg4", out)

	def test_only_one_index_bound_set_disables_index_filter(self):
		lp = make_pile(3)
		sc = SortConditions()
		sc.index_start = 1  # index_end left None
		out = capture(lp, sort_orders=sc)
		# Both must be set for the index filter to apply at all.
		for i in range(3):
			self.assertIn(f"msg{i}", out)


class TestShowLogsStrFmtOverride(unittest.TestCase):
	def test_override_shows_detail_even_if_default_format_hides_it(self):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.str_format.show_detail = False
		lp.info("msg", detail="hidden-by-default-but-overridden")

		# No override -> detail hidden
		out_default = capture(lp, str_fmt=None)
		self.assertNotIn("hidden-by-default-but-overridden", out_default)

		# Explicit override -> detail shown
		override_fmt = LogFormat(use_color=False, show_detail=True)
		out_override = capture(lp, str_fmt=override_fmt)
		self.assertIn("hidden-by-default-but-overridden", out_override)


if __name__ == "__main__":
	unittest.main()
