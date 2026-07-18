import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import markdown, mdprint, LogFormat
from colorama import Fore, Back, Style

PLAIN = LogFormat(use_color=False)


class TestMarkdownPlain(unittest.TestCase):
	""" All of these use use_color=False, so a passing test proves the parser
	correctly identifies and strips each escape sequence, independent of what
	colorama codes get substituted in. """

	def test_no_markdown_passthrough(self):
		self.assertEqual(markdown("no markdown at all", PLAIN), "no markdown at all")

	def test_temporary_bold(self):
		self.assertEqual(markdown("Starting >bold< run", PLAIN), "Starting bold run")

	def test_permanent_change_persists_after_close(self):
		# >>:q permanently switches to quiet; with use_color=False every color
		# is "", so this mainly proves the tag itself is consumed correctly.
		self.assertEqual(markdown(">>:qpermanent quiet<", PLAIN), "permanent quiet")

	def test_numeric_color_codes(self):
		self.assertEqual(
			markdown(">:1main<>:2bold<>:3quiet<>:4alt<>:5label<", PLAIN),
			"mainboldquietaltlabel",
		)

	def test_letter_color_codes_case_insensitive(self):
		self.assertEqual(
			markdown(">:Mmain<>:Bbold<>:Qquiet<>:Aalt<>:Llabel<", PLAIN),
			"mainboldquietaltlabel",
		)
		self.assertEqual(
			markdown(">:mmain<>:bbold<>:qquiet<>:aalt<>:llabel<", PLAIN),
			"mainboldquietaltlabel",
		)

	def test_unrecognized_color_code_left_as_text_but_close_tag_still_consumed(self):
		self.assertEqual(
			markdown("unrecognized code >:Zdoes nothing<", PLAIN),
			"unrecognized code >:Zdoes nothing",
		)

	def test_unterminated_open_tag(self):
		self.assertEqual(
			markdown(">unterminated bold with no close", PLAIN),
			"unterminated bold with no close",
		)

	def test_backslash_escapes_angle_brackets(self):
		self.assertEqual(markdown(r"\>no color change\<", PLAIN), ">no color change<")

	def test_backslash_escapes_permanent_sequence(self):
		self.assertEqual(markdown(r"\>\>:3", PLAIN), ">>:3")
		self.assertEqual(markdown(r"\>\>:3no color change\<", PLAIN), ">>:3no color change<")

	def test_backslash_escapes_lock_sequence(self):
		self.assertEqual(markdown(r"\@:LOCK not a lock", PLAIN), "@:LOCK not a lock")
		self.assertEqual(markdown(r"\@:UNLOCK not an unlock", PLAIN), "@:UNLOCK not an unlock")

	def test_trailing_lone_backslash_is_left_untouched(self):
		self.assertEqual(markdown("trailing backslash at end\\", PLAIN), "trailing backslash at end\\")

	def test_lock_suppresses_markdown_until_unlock(self):
		msg = "@:LOCK ignored >bold< markdown @:UNLOCK back >bold< to normal"
		self.assertEqual(
			markdown(msg, PLAIN),
			" ignored >bold< markdown  back bold to normal",
		)

	def test_lock_with_no_matching_unlock_suppresses_to_end_of_string(self):
		msg = "@:LOCK >bold< stays literal forever"
		self.assertEqual(markdown(msg, PLAIN), " >bold< stays literal forever")

	def test_empty_string(self):
		self.assertEqual(markdown("", PLAIN), "")

	def test_default_str_fmt_is_used_when_none_given(self):
		# Should not raise, and should behave like LogEntry.default_format
		# (use_color=True by default), so markers get replaced with *something*.
		result = markdown("Starting >bold< run")
		self.assertNotIn(">", result)
		self.assertNotIn("<", result)


class TestMarkdownColored(unittest.TestCase):
	""" Exact-match tests against the real default LogFormat color palette, to
	pin down the substitution logic (not just tag stripping). """

	def setUp(self):
		self.fmt = LogFormat()  # use_color=True, default palette

	def test_temporary_bold_uses_bold_color_then_reverts_to_main(self):
		expected = f"Starting {Fore.LIGHTBLUE_EX}bold{Fore.WHITE}{Back.RESET} run"
		self.assertEqual(markdown("Starting >bold< run", self.fmt), expected)

	def test_permanent_change_updates_return_color(self):
		expected = f"{Fore.LIGHTBLACK_EX}permanent{Fore.LIGHTBLACK_EX}then default"
		self.assertEqual(markdown(">>:qpermanent<then default", self.fmt), expected)

	def test_quiet_color_code(self):
		expected = f"{Fore.LIGHTBLACK_EX}Test{Fore.WHITE}{Back.RESET}"
		self.assertEqual(markdown(">:3Test<", self.fmt), expected)

	def test_color_overrides_dict_not_used_by_markdown_directly(self):
		# markdown() only consults default_color; color_overrides is applied
		# by LogEntry.str() separately, so setting it should have no effect here.
		fmt = LogFormat()
		fmt.color_overrides = {20: {"bold": Fore.RED}}
		expected = f"Starting {Fore.LIGHTBLUE_EX}bold{Fore.WHITE}{Back.RESET} run"
		self.assertEqual(markdown("Starting >bold< run", fmt), expected)


class TestMdprint(unittest.TestCase):
	def test_writes_processed_text_and_newline_to_given_stream(self):
		buf = io.StringIO()
		mdprint("Starting >bold< run", file=buf, str_fmt=PLAIN)
		self.assertEqual(buf.getvalue(), "Starting bold run\n")

	def test_custom_end(self):
		buf = io.StringIO()
		mdprint("no markup", file=buf, end="", str_fmt=PLAIN)
		self.assertEqual(buf.getvalue(), "no markup")

	def test_default_file_param_is_a_writable_stream(self):
		# NOTE: `file=sys.stdout` is bound once at import time (standard
		# Python early-binding of default args), so reassigning sys.stdout
		# afterward does NOT redirect mdprint()'s default output stream.
		# This just confirms the bound default is a writable stream at all.
		import inspect
		default_file = inspect.signature(mdprint).parameters["file"].default
		self.assertTrue(hasattr(default_file, "write"))

	def test_omitting_file_argument_does_not_raise(self):
		mdprint("hi", str_fmt=PLAIN)


if __name__ == "__main__":
	unittest.main()
