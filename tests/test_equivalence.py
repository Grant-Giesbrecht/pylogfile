import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import LogEntry, LogPile, are_equivalent_entries, are_equivalent_piles, INFO, WARNING


def make_entry(message="msg", detail="dtl", level=INFO, timestamp=None):
	e = LogEntry(level=level, message=message, detail=detail)
	if timestamp is not None:
		e.timestamp = timestamp
	return e


class TestAreEquivalentEntries(unittest.TestCase):
	def test_identical_entries_match(self):
		now = datetime.datetime.now()
		a = make_entry(timestamp=now)
		b = make_entry(timestamp=now)
		self.assertTrue(are_equivalent_entries(a, b))

	def test_different_message_fails(self):
		now = datetime.datetime.now()
		a = make_entry(message="one", timestamp=now)
		b = make_entry(message="two", timestamp=now)
		self.assertFalse(are_equivalent_entries(a, b))

	def test_different_detail_fails(self):
		now = datetime.datetime.now()
		a = make_entry(detail="one", timestamp=now)
		b = make_entry(detail="two", timestamp=now)
		self.assertFalse(are_equivalent_entries(a, b))

	def test_different_level_fails(self):
		now = datetime.datetime.now()
		a = make_entry(level=INFO, timestamp=now)
		b = make_entry(level=WARNING, timestamp=now)
		self.assertFalse(are_equivalent_entries(a, b))

	def test_timestamp_within_default_tolerance_matches(self):
		now = datetime.datetime.now()
		a = make_entry(timestamp=now)
		b = make_entry(timestamp=now + datetime.timedelta(microseconds=5))
		self.assertTrue(are_equivalent_entries(a, b))

	def test_timestamp_beyond_default_tolerance_fails(self):
		now = datetime.datetime.now()
		a = make_entry(timestamp=now)
		b = make_entry(timestamp=now + datetime.timedelta(microseconds=50))
		self.assertFalse(are_equivalent_entries(a, b))

	def test_custom_tolerance_widens_acceptance(self):
		now = datetime.datetime.now()
		a = make_entry(timestamp=now)
		b = make_entry(timestamp=now + datetime.timedelta(microseconds=50))
		self.assertTrue(are_equivalent_entries(a, b, time_tol_us=100))

	def test_timestamp_exactly_at_boundary_is_excluded(self):
		# Implementation uses strict `>` for the "fails" case, so a delta
		# exactly equal to the tolerance should still count as equivalent.
		now = datetime.datetime.now()
		a = make_entry(timestamp=now)
		b = make_entry(timestamp=now + datetime.timedelta(microseconds=10))
		self.assertTrue(are_equivalent_entries(a, b, time_tol_us=10))


class TestAreEquivalentPiles(unittest.TestCase):
	def _pile_from_entries(self, entries):
		lp = LogPile()
		lp.terminal_output_enable = False
		lp.logs = entries
		return lp

	def test_identical_piles_match(self):
		now = datetime.datetime.now()
		entries = [make_entry(message=f"m{i}", timestamp=now) for i in range(3)]
		lp1 = self._pile_from_entries(entries)
		lp2 = self._pile_from_entries([make_entry(message=f"m{i}", timestamp=now) for i in range(3)])
		self.assertTrue(are_equivalent_piles(lp1, lp2))

	def test_different_lengths_fail(self):
		now = datetime.datetime.now()
		lp1 = self._pile_from_entries([make_entry(timestamp=now)])
		lp2 = self._pile_from_entries([make_entry(timestamp=now), make_entry(timestamp=now)])
		self.assertFalse(are_equivalent_piles(lp1, lp2))

	def test_one_mismatched_entry_fails_whole_pile(self):
		now = datetime.datetime.now()
		lp1 = self._pile_from_entries([make_entry(message="a", timestamp=now), make_entry(message="b", timestamp=now)])
		lp2 = self._pile_from_entries([make_entry(message="a", timestamp=now), make_entry(message="different", timestamp=now)])
		self.assertFalse(are_equivalent_piles(lp1, lp2))

	def test_order_matters(self):
		now = datetime.datetime.now()
		lp1 = self._pile_from_entries([make_entry(message="a", timestamp=now), make_entry(message="b", timestamp=now)])
		lp2 = self._pile_from_entries([make_entry(message="b", timestamp=now), make_entry(message="a", timestamp=now)])
		self.assertFalse(are_equivalent_piles(lp1, lp2))

	def test_both_empty_matches(self):
		lp1 = self._pile_from_entries([])
		lp2 = self._pile_from_entries([])
		self.assertTrue(are_equivalent_piles(lp1, lp2))


if __name__ == "__main__":
	unittest.main()
