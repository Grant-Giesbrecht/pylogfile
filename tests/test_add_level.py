import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pylogfile.base import LogPile, LogLevelDefinition, find_level_in_list


class TestAddLevel(unittest.TestCase):
	def setUp(self):
		self.lp = LogPile()
		self.lp.terminal_output_enable = False

	def test_add_level_registers_definition(self):
		self.lp.add_level(25, "NOTICE")
		idx = find_level_in_list(25, self.lp.log_levels)
		self.assertIsNotNone(idx)
		self.assertEqual(self.lp.log_levels[idx].level_name, "NOTICE")

	def test_convenience_method_logs_at_correct_level(self):
		self.lp.add_level(25, "NOTICE")
		self.lp.notice("something notice-worthy", detail="extra")
		self.assertEqual(len(self.lp.logs), 1)
		self.assertEqual(self.lp.logs[0].level, 25)
		self.assertEqual(self.lp.logs[0].message, "something notice-worthy")
		self.assertEqual(self.lp.logs[0].detail, "extra")

	def test_method_name_is_lowercased(self):
		self.lp.add_level(25, "NOTICE")
		self.assertTrue(hasattr(self.lp, "notice"))
		self.assertFalse(hasattr(LogPile, "notice"))  # instance-only, not class-level

	def test_other_instances_do_not_get_the_method(self):
		self.lp.add_level(25, "NOTICE")
		other = LogPile()
		other.terminal_output_enable = False
		self.assertFalse(hasattr(other, "notice"))

	def test_invalid_identifier_name_rejected(self):
		with self.assertRaises(ValueError):
			self.lp.add_level(25, "not valid!")

	def test_collision_with_existing_attribute_rejected(self):
		with self.assertRaises(ValueError):
			self.lp.add_level(99, "add_log")
		with self.assertRaises(ValueError):
			self.lp.add_level(99, "logs")

	def test_recalling_add_level_updates_definition_without_duplicating(self):
		from colorama import Fore
		self.lp.add_level(25, "NOTICE")
		self.lp.add_level(25, "NOTICE", label_color=Fore.CYAN)

		matches = [ld for ld in self.lp.log_levels if ld.level_name == "NOTICE"]
		self.assertEqual(len(matches), 1)
		self.assertEqual(matches[0].label_color, Fore.CYAN)

		# The rebound method should still work correctly.
		self.lp.notice("still works")
		self.assertEqual(self.lp.logs[-1].level, 25)

	def test_recalling_add_level_with_new_int_moves_method(self):
		self.lp.add_level(25, "NOTICE")
		self.lp.add_level(26, "NOTICE")

		matches = [ld for ld in self.lp.log_levels if ld.level_name == "NOTICE"]
		self.assertEqual(len(matches), 1)
		self.assertEqual(matches[0].level_int, 26)

		self.lp.notice("moved")
		self.assertEqual(self.lp.logs[-1].level, 26)

	def test_returns_the_level_definition(self):
		ld = self.lp.add_level(25, "NOTICE")
		self.assertIsInstance(ld, LogLevelDefinition)
		self.assertEqual(ld.level_int, 25)
		self.assertEqual(ld.level_name, "NOTICE")


if __name__ == "__main__":
	unittest.main()
