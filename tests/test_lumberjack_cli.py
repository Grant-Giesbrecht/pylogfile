import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import LogPile, WARNING
from colorama import Style

# These tests exercise the *installed* `lumber` console script as a real
# subprocess (input piped to stdin, exactly like a human would type into the
# REPL), rather than importing lumberjack.py in-process. That's deliberate:
# lumberjack.py parses sys.argv and loads its help JSON as *module-level*
# side effects with no `if __name__ == "__main__":` guard, so re-invoking
# main() in-process with different args/state is fragile. Subprocess
# isolation sidesteps all of that and matches how the CLI is actually used.
#
# Requires `pip install -e .` (or equivalent) so `lumber` resolves to this
# checkout - see CLAUDE.md.

LUMBER = "lumber"


def run_lumber(args, stdin_text=None, timeout=15):
	return subprocess.run(
		[LUMBER, *args],
		input=stdin_text,
		capture_output=True,
		text=True,
		timeout=timeout,
	)


def run_repl(path, commands, timeout=15):
	""" commands: list of REPL command lines; EXIT is appended automatically. """
	stdin_text = "\n".join([*commands, "EXIT"]) + "\n"
	return run_lumber([path], stdin_text=stdin_text, timeout=timeout)


@unittest.skipIf(shutil.which(LUMBER) is None,
				  "lumber console script not found on PATH - install with `pip install -e .`")
class LumberjackCliTestCase(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.tmpdir = tempfile.TemporaryDirectory()
		cls.path = os.path.join(cls.tmpdir.name, "probe.plflog")
		cls.json_path = os.path.join(cls.tmpdir.name, "probe.log.json")

		lp = LogPile()
		lp.terminal_output_enable = False
		lp.info("first info message")
		lp.warning("a warning happened")
		lp.error("an error occurred", detail="stack trace here")
		lp.debug("debug details")
		lp.save_plflog(cls.path, file_version="1.0")
		lp.save_json(cls.json_path)

	@classmethod
	def tearDownClass(cls):
		cls.tmpdir.cleanup()


class TestNonInteractiveFlags(LumberjackCliTestCase):
	def test_all_flag_shows_every_log(self):
		result = run_lumber([self.path, "--all", "--nocli"])
		self.assertEqual(result.returncode, 0)
		for msg in ("first info message", "a warning happened", "an error occurred", "debug details"):
			self.assertIn(msg, result.stdout)

	def test_first_flag_shows_oldest_first(self):
		result = run_lumber([self.path, "--first", "--nocli"])
		self.assertEqual(result.returncode, 0)
		self.assertLess(result.stdout.index("first info message"), result.stdout.index("debug details"))

	def test_last_flag_shows_newest_first(self):
		result = run_lumber([self.path, "--last", "--nocli"])
		self.assertEqual(result.returncode, 0)
		self.assertLess(result.stdout.index("debug details"), result.stdout.index("first info message"))

	def test_no_display_flag_loads_silently(self):
		result = run_lumber([self.path, "--nocli"])
		self.assertEqual(result.returncode, 0)
		self.assertNotIn("first info message", result.stdout)

	def test_json_file_loads_via_extension_detection(self):
		result = run_lumber([self.json_path, "--all", "--nocli"])
		self.assertEqual(result.returncode, 0)
		self.assertIn("first info message", result.stdout)

	def test_nonexistent_file_currently_crashes(self):
		# Documents current (buggy, already flagged via a #TODO in
		# lumberjack.py) behavior: load errors aren't caught in main(), so a
		# missing file raises instead of printing the intended
		# "Failed to read plflog file." message.
		result = run_lumber([os.path.join(self.tmpdir.name, "does_not_exist.plflog"), "--nocli"])
		self.assertNotEqual(result.returncode, 0)
		self.assertIn("FileNotFoundError", result.stderr)


class TestReplShow(LumberjackCliTestCase):
	def test_show_all(self):
		result = run_repl(self.path, ["SHOW --all"])
		for msg in ("first info message", "a warning happened", "an error occurred", "debug details"):
			self.assertIn(msg, result.stdout)

	def test_show_num_limits_count(self):
		# NOTE: the bare REPL `SHOW` command defaults to from_beginning=True
		# (per LJSettings), unlike the top-level --last/--first argparse
		# flags - so this shows the *oldest* entry, not the most recent.
		result = run_repl(self.path, ["SHOW -n 1"])
		self.assertIn("first info message", result.stdout)
		self.assertNotIn("debug details", result.stdout)

	def test_show_contains_filters(self):
		result = run_repl(self.path, ["SHOW -c error"])
		self.assertIn("an error occurred", result.stdout)
		self.assertNotIn("a warning happened", result.stdout)

	def test_show_min_max_level(self):
		result = run_repl(self.path, ["SHOW --min WARNING --max ERROR"])
		self.assertIn("a warning happened", result.stdout)
		self.assertIn("an error occurred", result.stdout)
		self.assertNotIn("first info message", result.stdout)
		self.assertNotIn("debug details", result.stdout)

	def test_show_index_range(self):
		result = run_repl(self.path, ["SHOW --index 0:1"])
		self.assertIn("first info message", result.stdout)
		self.assertIn("a warning happened", result.stdout)
		self.assertNotIn("an error occurred", result.stdout)
		self.assertNotIn("debug details", result.stdout)


class TestReplLevelCommands(LumberjackCliTestCase):
	def test_min_level_updates_state_and_filters_show(self):
		# NOTE: `SHOW --all` deliberately ignores level limits (that's its
		# documented job), so filtering must be checked via bare SHOW.
		result = run_repl(self.path, ["MIN-LEVEL WARNING", "STATE", "SHOW"])
		self.assertIn(f"Min. level: {Style.RESET_ALL}{WARNING}", result.stdout)
		self.assertIn("a warning happened", result.stdout)
		self.assertIn("an error occurred", result.stdout)
		self.assertNotIn("first info message", result.stdout)  # INFO < WARNING
		self.assertNotIn("debug details", result.stdout)  # DEBUG < WARNING

	def test_max_level_updates_state_and_filters_show(self):
		result = run_repl(self.path, ["MAX-LEVEL WARNING", "STATE", "SHOW"])
		self.assertIn(f"Max. level: {Style.RESET_ALL}{WARNING}", result.stdout)
		self.assertIn("first info message", result.stdout)
		self.assertIn("a warning happened", result.stdout)
		self.assertNotIn("an error occurred", result.stdout)  # ERROR > WARNING

	def test_min_level_invalid_prints_error_and_does_not_crash(self):
		result = run_repl(self.path, ["MIN-LEVEL BOGUS"])
		self.assertEqual(result.returncode, 0)
		self.assertIn("Unrecognized level spcifier 'BOGUS'", result.stdout)

	def test_max_level_invalid_prints_error_and_does_not_crash(self):
		result = run_repl(self.path, ["MAX-LEVEL BOGUS"])
		self.assertEqual(result.returncode, 0)
		self.assertIn("Unrecognized level spcifier 'BOGUS'", result.stdout)


class TestReplInfoAndState(LumberjackCliTestCase):
	def test_info_basic(self):
		result = run_repl(self.path, ["INFO"])
		self.assertIn("number of Logs: ", result.stdout)
		self.assertIn("4", result.stdout)

	def test_info_long_shows_per_level_counts(self):
		result = run_repl(self.path, ["INFO --long"])
		self.assertIn("Number of WARNING: ", result.stdout)
		self.assertIn("First timestamp:", result.stdout)
		self.assertIn("Last timestamp:", result.stdout)

	def test_state_shows_settings(self):
		result = run_repl(self.path, ["STATE"])
		self.assertIn("Lumberjack-CLI State:", result.stdout)
		self.assertIn("Min. level:", result.stdout)
		self.assertIn("Num. print:", result.stdout)


class TestReplHelp(LumberjackCliTestCase):
	def test_help_for_specific_command(self):
		result = run_repl(self.path, ["HELP SHOW"])
		self.assertIn("SHOW Help", result.stdout)
		self.assertIn("Shows a selection of log entries.", result.stdout)

	def test_help_list_shows_all_commands(self):
		result = run_repl(self.path, ["HELP --list"])
		self.assertIn("ALL COMMANDS", result.stdout)
		self.assertIn("EXIT", result.stdout)
		self.assertIn("SHOW", result.stdout)


class TestReplMisc(LumberjackCliTestCase):
	def test_unrecognized_command(self):
		result = run_repl(self.path, ["NOTACOMMAND"])
		self.assertIn("Unrecognized command 'NOTACOMMAND'", result.stdout)

	def test_blank_line_does_not_crash(self):
		result = run_repl(self.path, [""])
		self.assertEqual(result.returncode, 0)

	def test_exit_terminates_cleanly(self):
		result = run_lumber([self.path], stdin_text="EXIT\n")
		self.assertEqual(result.returncode, 0)

	def test_num_print_then_show_respects_new_limit(self):
		# Bare SHOW defaults to from_beginning=True, so the one entry let
		# through by NUM-PRINT 1 should be the oldest, not the newest.
		result = run_repl(self.path, ["NUM-PRINT 1", "SHOW"])
		self.assertIn("first info message", result.stdout)
		self.assertNotIn("a warning happened", result.stdout)
		self.assertNotIn("an error occurred", result.stdout)
		self.assertNotIn("debug details", result.stdout)


if __name__ == "__main__":
	unittest.main()
