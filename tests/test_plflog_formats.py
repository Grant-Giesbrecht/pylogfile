import datetime
import os
import sys
import tempfile
import unittest

import h5py
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import (
	LogPile, LogLevelDefinition, UnknownLogFileFormat,
	are_equivalent_piles, get_default_levels,
	INFO, WARNING, ERROR,
)


def make_pile():
	lp = LogPile()
	lp.terminal_output_enable = False
	lp.info("first message", detail="first detail")
	lp.warning("second message")
	lp.error("first message", detail="repeated message text for dedup check")
	return lp


class TestV1RoundTrip(unittest.TestCase):
	def setUp(self):
		self.pile = make_pile()
		self.tmpdir = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmpdir.cleanup)
		self.path = os.path.join(self.tmpdir.name, "v1.plflog")
		self.pile.save_plflog(self.path, file_version="1.0")

	def test_content_round_trips(self):
		loaded = LogPile()
		loaded.terminal_output_enable = False
		self.assertTrue(loaded.load_plflog(self.path))
		self.assertTrue(are_equivalent_piles(self.pile, loaded))

	def test_default_levels_round_trip(self):
		loaded = LogPile()
		loaded.terminal_output_enable = False
		loaded.load_plflog(self.path)
		self.assertEqual(
			[ld.level_name for ld in loaded.log_levels],
			[ld.level_name for ld in get_default_levels()],
		)

	def test_default_file_version_is_v1(self):
		path2 = os.path.join(self.tmpdir.name, "default_version.plflog")
		self.pile.save_plflog(path2)  # no file_version given
		with h5py.File(path2, "r") as fh:
			self.assertEqual(fh["_file_info_"].attrs["encoding"], "compressed")

	def test_unrecognized_file_version_defaults_to_v1(self):
		path2 = os.path.join(self.tmpdir.name, "weird_version.plflog")
		self.pile.save_plflog(path2, file_version="9.9")
		with h5py.File(path2, "r") as fh:
			self.assertEqual(fh["_file_info_"].attrs["encoding"], "compressed")

	def test_message_table_deduplicates_repeated_messages(self):
		with h5py.File(self.path, "r") as fh:
			msg_table = fh["logs"]["message_table"][...]
			msg_ids = fh["logs"]["message_id"][...]
		# "first message" appears twice (entries 0 and 2) but should only take
		# one slot in the dictionary-encoded table.
		self.assertEqual(len(msg_table), 2)
		self.assertEqual(len(msg_ids), 3)
		self.assertEqual(msg_ids[0], msg_ids[2])

	def test_file_info_attrs(self):
		with h5py.File(self.path, "r") as fh:
			mfi = fh["_file_info_"]
			self.assertEqual(mfi.attrs["file_standard"], "pylogfile.logpile")
			self.assertEqual(mfi.attrs["format_version"], "1.0")
			self.assertEqual(mfi.attrs["encoding"], "compressed")

	def test_timestamps_preserved_to_microsecond(self):
		loaded = LogPile()
		loaded.terminal_output_enable = False
		loaded.load_plflog(self.path)
		for original, restored in zip(self.pile.logs, loaded.logs):
			delta = abs((original.timestamp - restored.timestamp).total_seconds())
			self.assertLess(delta, 1e-5)

	def test_clear_previous_true_replaces_existing_logs(self):
		loaded = LogPile()
		loaded.terminal_output_enable = False
		loaded.info("pre-existing log that should be wiped")
		loaded.load_plflog(self.path, clear_previous=True)
		self.assertEqual(len(loaded.logs), len(self.pile.logs))
		self.assertFalse(any(l.message == "pre-existing log that should be wiped" for l in loaded.logs))

	def test_clear_previous_false_appends(self):
		loaded = LogPile()
		loaded.terminal_output_enable = False
		loaded.info("pre-existing log that should survive")
		loaded.load_plflog(self.path, clear_previous=False)
		self.assertEqual(len(loaded.logs), len(self.pile.logs) + 1)
		self.assertTrue(any(l.message == "pre-existing log that should survive" for l in loaded.logs))


class TestV1CustomLevelsRoundTrip(unittest.TestCase):
	def test_custom_levels_and_colors_survive(self):
		from colorama import Fore
		custom = [
			LogLevelDefinition(1, "TRACE", label_color=Fore.MAGENTA),
			LogLevelDefinition(25, "NOTICE", main_color=Fore.CYAN, label_color=Fore.CYAN),
		]
		pile = LogPile(level_list=custom)
		pile.terminal_output_enable = False
		pile.add_log(1, "trace entry")
		pile.add_log(25, "notice entry")

		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "custom.plflog")
			pile.save_plflog(path, file_version="1.0")

			loaded = LogPile()
			loaded.terminal_output_enable = False
			loaded.load_plflog(path)

			self.assertEqual(len(loaded.log_levels), 2)
			by_name = {ld.level_name: ld for ld in loaded.log_levels}
			self.assertEqual(by_name["NOTICE"].level_int, 25)
			self.assertEqual(by_name["NOTICE"].main_color, Fore.CYAN)
			self.assertEqual(by_name["TRACE"].label_color, Fore.MAGENTA)


class TestV0RoundTrip(unittest.TestCase):
	def setUp(self):
		self.pile = make_pile()
		self.tmpdir = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmpdir.cleanup)
		self.path = os.path.join(self.tmpdir.name, "v0.plflog")
		self.pile.save_plflog(self.path, file_version="0.0")

	def test_content_round_trips(self):
		loaded = LogPile()
		loaded.terminal_output_enable = False
		self.assertTrue(loaded.load_plflog(self.path))
		self.assertTrue(are_equivalent_piles(self.pile, loaded))

	def test_layout_is_legacy_flat_datasets(self):
		with h5py.File(self.path, "r") as fh:
			self.assertNotIn("_file_info_", fh)
			self.assertIn("logs", fh)
			for key in ("message", "detail", "timestamp", "level"):
				self.assertIn(key, fh["logs"])

	def test_custom_levels_are_not_preserved_by_v0(self):
		custom = [LogLevelDefinition(25, "NOTICE")]
		pile = LogPile(level_list=custom)
		pile.terminal_output_enable = False
		pile.add_log(25, "notice entry")

		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "custom_v0.plflog")
			pile.save_plflog(path, file_version="0.0")

			loaded = LogPile()
			loaded.terminal_output_enable = False

			import io
			from contextlib import redirect_stdout
			buf = io.StringIO()
			with redirect_stdout(buf):
				loaded.load_plflog(path)

			# v0 always resolves against the 6 built-in default levels.
			self.assertEqual(
				[ld.level_name for ld in loaded.log_levels],
				[ld.level_name for ld in get_default_levels()],
			)

			# The unregistered level (25) was saved as the raw number "25"
			# (see _save_v0_plflog's fallback), which then can't be resolved
			# back to an int against the default level names on load, so
			# LogEntry.init_dict() falls back to level 0 and prints a notice
			# rather than crashing - this documents that full lossy chain.
			self.assertEqual(loaded.logs[0].level, 0)
			self.assertIn("Failed to initialize log entry", buf.getvalue())


class TestFormatAutoDetection(unittest.TestCase):
	def test_load_plflog_dispatches_v1_correctly(self):
		pile = make_pile()
		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "auto_v1.plflog")
			pile.save_plflog(path, file_version="1.0")
			loaded = LogPile()
			loaded.terminal_output_enable = False
			self.assertTrue(loaded.load_plflog(path))
			self.assertTrue(are_equivalent_piles(pile, loaded))

	def test_load_plflog_dispatches_v0_correctly(self):
		pile = make_pile()
		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "auto_v0.plflog")
			pile.save_plflog(path, file_version="0.0")
			loaded = LogPile()
			loaded.terminal_output_enable = False
			self.assertTrue(loaded.load_plflog(path))
			self.assertTrue(are_equivalent_piles(pile, loaded))

	def test_unrecognized_hdf5_file_raises(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "not_a_plflog.h5")
			with h5py.File(path, "w") as fh:
				fh.create_dataset("unrelated_data", data=np.arange(10))

			loaded = LogPile()
			with self.assertRaises(UnknownLogFileFormat):
				loaded.load_plflog(path)

	def test_non_hdf5_file_raises(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			path = os.path.join(tmpdir, "not_hdf5_at_all.plflog")
			with open(path, "w") as fh:
				fh.write("this is not an hdf5 file")

			loaded = LogPile()
			with self.assertRaises(Exception):
				loaded.load_plflog(path)


if __name__ == "__main__":
	unittest.main()
