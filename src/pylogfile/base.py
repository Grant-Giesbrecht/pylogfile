""" Provides the basic functionality of the package. Most of the functionality of this
module is contained in the `LogPile` and `LogEntry` classes.
"""


import datetime
import json
from dataclasses import dataclass, field
from colorama import Fore, Style, Back
import numpy as np
import h5py
import threading
import sys
import types

__all__ = [
	"NOTSET", "LOWDEBUG", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL",
	"UnknownLogFileFormat",
	"SortConditions",
	"LogFormat",
	"LogEntry",
	"LogLevelDefinition",
	"LogPile",
	"str_to_level",
	"level_to_str",
	"find_level_in_list",
	"markdown",
	"mdprint",
	"get_default_levels",
	"are_equivalent_entries",
	"are_equivalent_piles",
]

#TODO: Save only certain log levels
#NOTE: Currently, if info() or etc is called, and those levels are NOT defined, it will still record logs. It just saves them with a hard coded number. I think this is good?
#TODO: Add validate() function to see if any logs have undefined log levels.

NOTSET = 0
LOWDEBUG = 5	# For when you're having a really bad day
DEBUG = 10		# Used for debugging
INFO = 20		# Used for reporting basic high-level program functioning (that does not involve an error)
WARNING = 30 	# Warning for software
ERROR = 40		# Software error
CRITICAL = 50	# Critical error

def _to_epoch_ns(x) -> int:
	# 1) Already numeric? Treat as seconds unless it's obviously ns.
	if isinstance(x, (int, np.integer)):
		# Heuristic: if it's > 1e14 it's probably already ns
		return int(x) if x > 10**14 else int(x) * 1_000_000_000
	if isinstance(x, (float, np.floating)):
		return int(float(x) * 1_000_000_000)

	# 2) datetime object?
	if isinstance(x, datetime.datetime):
		dt = x
	else:
		# 3) string parse
		s = str(x).strip()
		# fromisoformat handles "YYYY-MM-DD HH:MM:SS.ffffff" and many ISO strings
		dt = datetime.datetime.fromisoformat(s)

	# If naive, assume local time; if aware, use its tzinfo.
	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=datetime.timezone.utc)  # or local timezone if you prefer

	return int(dt.timestamp() * 1_000_000_000)

def _epoch_ns_to_datetime(ns: int) -> datetime:
	"""Convert int64 epoch nanoseconds to an aware UTC datetime."""
	# Avoid float precision loss for large ns by using integer arithmetic
	sec, nsec = divmod(int(ns), 1_000_000_000)
	return datetime.datetime.fromtimestamp(sec, tz=datetime.timezone.utc).replace(microsecond=nsec // 1000)

class UnknownLogFileFormat(ValueError):
	pass

def _detect_pylogfile_format(fh: h5py.File) -> str:
	"""
	Return one of: "compressed", "legacy"
	Raise UnknownLogFileFormat if it doesn't look like either.
	"""
	
	# ---- New format: explicit metadata ----
	if "_file_info_" in fh:
		mfi = fh["_file_info_"]
		file_standard = mfi.attrs.get("file_standard", None)
		encoding = mfi.attrs.get("encoding", None)

		# Strong positive ID for your format
		if file_standard == "pylogfile.logpile":
			if encoding == "compressed":
				return "1.0"
			# If you later add other encodings, handle them here.
			# For now, if it's your standard but not compressed, treat as legacy-ish.
			return "0.0"
	
	# ---- Heuristic detection for old format ----
	# Your old saver wrote:
	# /logs/message, /logs/detail, /logs/timestamp, /logs/level
	if "logs" in fh:
		g = fh["logs"]
		legacy_keys = {"message", "detail", "timestamp", "level"}
		if legacy_keys.issubset(set(g.keys())):
			return "0.0"

		# Your compressed format has these:
		compressed_keys = {
			"message_table", "detail_table",
			"message_id", "detail_id",
			"timestamp_ns", "level",
		}
		if compressed_keys.issubset(set(g.keys())):
			return "1.0"
	
	raise UnknownLogFileFormat(
		"Unrecognized HDF5 layout: not a pylogfile .plflog file (legacy v0 or compressed v1)."
	)

class SortConditions:
	""" Class used to define the conditions of a LogEntry sort request."""

	def __init__(self):
		self.time_start = None
		self.time_end = None
		self.contains_and = []
		self.contains_or = []
		self.index_start = None
		self.index_end = None

class DummyMutex:
	def __init__(self):
		pass
	def __enter__(self):
		return
	def __exit__(self, exc_type, exc_value, traceback):
		return

@dataclass
class LogFormat:
	""" Class used to describe the cosmetic formatting of LogEntries printed to 
	standard output. 
	
	To use color_overrides, provide a dictoinary that uses the format:
	{<INT-LEVEL-CODE>:{<lowercase-string-markdown-color>:<colorama-color>}}
	
	For example, {10:{'main':Fore.GREEN}}
	
	"""
	
	show_detail:bool = False
	use_color:bool = True
	default_color:dict = field(default_factory=lambda: {"main": Fore.WHITE+Back.RESET, "bold": Fore.LIGHTBLUE_EX, "quiet": Fore.LIGHTBLACK_EX, "alt": Fore.YELLOW, "label": Fore.GREEN})
	color_overrides:dict = field(default_factory=lambda: {})
	detail_indent:str = "\t "
	strip_newlines:bool = True
	
	show_color_help:bool = False

def str_to_level(lvl:str, level_list:list) -> int:
	"""
	Converts a log level string to its associated int code.

	Args:
		lvl (str): Log level string, case-insensitive

	Returns:
		int: The log level int code. Returns None if not found.
	"""

	idx = find_level_in_list(lvl, level_list)
	if idx is None:
		return None

	return level_list[idx].level_int

def level_to_str(lvl:int, level_list:list) -> str:
	"""
	Converts a log level int to its associated string code.

	Args:
		lvl (str): Log level string

	Returns:
		str: The log level string code. Returns None if not found.
	"""

	idx = find_level_in_list(lvl, level_list)
	if idx is None:
		return None

	return level_list[idx].level_name



def find_level_in_list(level, level_list:list):
	'''
	Returns the index of the level object in the level_list which matches
	the specified level, either as a string (level_name) or int (level_int).
	Returns None (not found) if level_list is None or empty.
	'''

	if not level_list:
		return None

	if isinstance(level, str):
		for idx, ll in enumerate(level_list):
			if ll.level_name == level:
				return idx
	else:
		for idx, ll in enumerate(level_list):
			if ll.level_int == level:
				return idx
	
	return None

class LogEntry:
	""" Defines a single entry in the log. Contains log messages, levels, additional
	detail, etc. 
	
	Attributes:
		level (int): Log level int code
		timestamp (datetime): Time at which log was created
		message (str): Primary log message
		detail (str): Additional log message detail
	"""
	
	default_format = LogFormat()
	
	def __init__(self, level:int=0, message:str="", detail:str=""):
		"""
		Constructor for LogEntry class.
		
		Parameters:
			level (int): Log level of the entry
			message (str): Logging message
			detail (str): Additional detail for message
		"""
		# Set timestamp
		self.timestamp = datetime.datetime.now()
		
		if detail is None:
			detail = ""
		if message is None:
			message = ""
		
		# Set level (Saved as integer)
		self.level = level
		
		# Set message
		self.message = message
		self.detail = detail
	
	def init_dict(self, data_dict:dict) -> bool:
		"""
		Initializes from a provided dictionar.
		"""
		
		# Extract data from dict
		try:
			lvl_src = data_dict['level']
			msg = data_dict['message']
			dtl = data_dict['detail']
			ts = data_dict['timestamp']
		except:
			return False
		
		# Set level
		try:
			lvl = int(lvl_src)
		except:
			lvl = 0
			print(f"Failed to initialize log entry from dictionary (value={lvl_src}). Could not convert level to int. Setting level to zero.")
		self.level = lvl
		
		self.message = msg # Set message
		self.detail = dtl
		self.timestamp = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
		
		return True
		
	def get_dict(self) -> dict:
		""" Returns the contents of the log as a dictionary.
		
		Returns:
			(dict): Dictionary containing log entry data
		"""
		return {"message":self.message, "detail":self.detail, "timestamp":str(self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')) , "level":self.level}
	
	def get_json(self) -> str:
		"""
		Returns the class as a JSON string.
		
		Returns:
			(str): All class data in JSON form
		"""
		return json.dumps(self.get_dict())
	
	def str(self, str_fmt:LogFormat=None, level_list:list=None, show_color_help:bool=False) -> str:
		""" Represent the log entry as a formatted string suitable for printing.
		
		Parameters:
			str_fmt (LogFormat): Format specification
			show_color_help (bool): Prints each color to command line from each override level to 
				help the user debug why logs appear in the color they do.
		
		Returns:
			(str): String representation of class
		"""
		
		# Get format specifier
		if str_fmt is None:
			str_fmt = LogEntry.default_format
		
		if str_fmt.show_color_help:
			show_color_help = True
		
		# Apply or wipe colors
		if str_fmt.use_color:
			
			# Start with default colors
			c_main = str_fmt.default_color['main']
			c_bold = str_fmt.default_color['bold']
			c_quiet = str_fmt.default_color['quiet']
			c_alt = str_fmt.default_color['alt']
			c_label = str_fmt.default_color['label']
			
			if show_color_help:
				print(f"\tDefault colors, from LogFormat object:")
				sra = Style.RESET_ALL
				print(f"\t\t{c_main}main{sra}, {c_bold}bold{sra}, {c_quiet}quiet{sra}, {c_alt}alt{sra}, {c_label}label{sra}", flush=True)
			
			# Apply level specific changes
			if level_list is not None:
				l_idx = find_level_in_list(self.level, level_list)
				if l_idx is not None:
					if level_list[l_idx].main_color is not None and level_list[l_idx].main_color != "":
						c_main = level_list[l_idx].main_color
					if level_list[l_idx].bold_color is not None and level_list[l_idx].bold_color != "":
						c_bold = level_list[l_idx].bold_color
					if level_list[l_idx].quiet_color is not None and level_list[l_idx].quiet_color != "":
						c_quiet = level_list[l_idx].quiet_color
					if level_list[l_idx].alt_color is not None and level_list[l_idx].alt_color != "":
						c_alt = level_list[l_idx].alt_color
					if level_list[l_idx].label_color is not None and level_list[l_idx].label_color != "":
						c_label = level_list[l_idx].label_color
			
			if show_color_help: 
				print(f"\tAfter override from LogLevelDefinition: level={self.level}")
				sra = Style.RESET_ALL
				print(f"\t\t{c_main}main{sra}, {c_bold}bold{sra}, {c_quiet}quiet{sra}, {c_alt}alt{sra}, {c_label}label{sra}", flush=True)
			
			# Apply color-overrides
			if self.level in str_fmt.color_overrides:
				if 'main' in str_fmt.color_overrides[self.level]:
					c_main = str_fmt.color_overrides[self.level]['main']
				if 'bold' in str_fmt.color_overrides[self.level]:
					c_bold = str_fmt.color_overrides[self.level]['bold']
				if 'quiet' in str_fmt.color_overrides[self.level]:
					c_quiet = str_fmt.color_overrides[self.level]['quiet']
				if 'alt' in str_fmt.color_overrides[self.level]:
					c_alt = str_fmt.color_overrides[self.level]['alt']
				if 'label' in str_fmt.color_overrides[self.level]:
					c_label = str_fmt.color_overrides[self.level]['label']
			
			if show_color_help: 
				print(f"\tAfter override from LogFormat Overrides: level={self.level}")
				sra = Style.RESET_ALL
				print(f"\t\t{c_main}main{sra}, {c_bold}bold{sra}, {c_quiet}quiet{sra}, {c_alt}alt{sra}, {c_label}label{sra}", flush=True)
			
		else:
			c_main = ''
			c_bold = ''
			c_quiet = ''
			c_alt = ''
			c_label = ''
		
		# If requested, remove all newlines
		if str_fmt.strip_newlines:
			message = self.message.replace("\n", "")
			detail = self.detail.replace("\n", "")
			
		
		# Create base string
		level_str = level_to_str(self.level, level_list)
		if level_str is None:
			level_str = str(self.level)
		s = f"{c_alt}[{c_label}{level_str}{c_alt}]{c_main} {markdown(message, str_fmt)} {c_quiet}| {self.timestamp}{Style.RESET_ALL}"
		
		# Add detail if requested
		if str_fmt.show_detail and len(detail) > 0:
			s = s + f"\n{str_fmt.detail_indent}{c_quiet}{detail}"
		
		return s
	
	def matches_sort(self, orders:SortConditions) -> bool:
		""" Checks if the entry matches the conditions specified by the SortConditions 'orders'. Returns true if they match and false if they don't. NOTE: Does not check index, that is only valid in a LogPile context.
		
		Parameters:
			orders (SortConditions): Sort conditions to check against
		
		Returns:
			(bool): True if matched sort conditions
		"""
		# Check if time conditions are specified
		if (orders.time_start is not None) and (orders.time_end is not None):
			
			# Check if conditions agree
			if self.timestamp < orders.time_start or self.timestamp > orders.time_end:
				return False
		
		# Check if contains_and is specified
		if len(orders.contains_and) > 0:
			
			# Check if all are hits
			for targ in orders.contains_and:
				# print(f"Searching for target: {targ} in {self.message} and {self.detail}.")
				if (targ not in self.message) and (targ not in self.detail):
					# print(f"  -> Failed to find target")
					return False
				# print(f"  -> Found target")
		
		# Check if contains_or is specified
		if len(orders.contains_or) > 0:
			
			found_or = False
			
			# Check if any are hits
			for targ in orders.contains_or:
				if (targ in self.message) or (targ in self.detail):
					found_or = True
					break
			
			# Return negative if none matched
			if not found_or:
				return False
		
		# All matched!
		return True
	
def markdown(msg:str, str_fmt:LogFormat=None) -> str:
	"""
	Applys Pylogfile markdown to a string. Pylogfile markdown uses a series of characters
	to change the color of the output text. 
	
	List of escape characters to alter text color:
	
	- `>` Temporarily change to bold
	- `<` Revert to previous color
	- `>:n` Temporariliy change to color 'n' (See list of 'n'-codes below)
	- `>>` Permanently change to bold
	- `>>:n` Permanently change to color 'n' (See list of 'n'-codes below)
	
	\\>, \\<, Type character without color adjustment. So to get >>:3
		to appear you'd type \\>\\>:3. Similarly, to type a lock character
		without setting or remove the lock, type \\>:L\\> or 
		\\<:L\\<
	
	List of escape characters used to lock markdown: (Case-sensitive)
	- `@:LOCK` Enables the lock, ignoring all markdown except `@:UNLOCK`
	- `@:UNLOCK` Disables the lock, re-enabling all markdown.
	To Preface either of these sequences with `\\` (ie. a single backslash) to
	interpret them as text rather than a lock character. 
	
	A backslash can be used to escape angle brackets and forgoe applying color
	adjustment. For example, `"\\>"` and `"\\<"` would render `">"` and `"<"`, respectively
	once processed through pylogfile markdown. So as an example, to render `">>:3"`, 
	you would need to input `"\\>\\>:3"`.
	
	List of 'n'-codes: (Case insensitive)
	
	- `1` or `m`: Main
	- `2` or `b`: Bold
	- `3` or `q`: Quiet
	- `4` or `a`: Alt
	- `5` or `l`: Label
	
	So for example, `">:3Test<"` or `">:qTest<"` would change the color to 'Quiet', print
	`'Test'`, and return to the original color.
	 
	Parameters:
		msg (str): String to process with pylogfile markdown.
		str_fmt (LogFormat): Optional formatting specification to apply
	
	Returns:
		(str): Formatted text
	"""
	
	# Get default format
	if str_fmt is None:
		str_fmt = LogEntry.default_format
	
	# Apply or wipe colors
	if str_fmt.use_color:
		c_main = str_fmt.default_color['main']
		c_bold = str_fmt.default_color['bold']
		c_quiet = str_fmt.default_color['quiet']
		c_alt = str_fmt.default_color['alt']
		c_label = str_fmt.default_color['label']
	else:
		c_main = ''
		c_bold = ''
		c_quiet = ''
		c_alt = ''
		c_label = ''
	
	# This is the color that a return character will restore
	return_color = c_main
	
	# Get every index of '>', '<', and '\\'
	idx = 0
	replacements = []
	lock_is_set = False
	while idx < len(msg):
		
		# Look for escape character
		if (not lock_is_set) and msg[idx] == '\\':
			
			# If next character is > or <, remove the escape
			if idx+1 < len(msg) and msg[idx+1] == '>':
				replacements.append({'text': '>', 'idx_start': idx, 'idx_end': idx+1})
			elif idx+1 < len(msg) and msg[idx+1] == '<':
				replacements.append({'text': '<', 'idx_start': idx, 'idx_end': idx+1})
			
			# If next character is @, check for lock/unlock and remove escape
			elif idx+6 < len(msg) and msg[idx+1:idx+7] == "@:LOCK":
				replacements.append({'text': '@:LOCK', 'idx_start': idx, 'idx_end': idx+6})
			elif idx+8 < len(msg) and msg[idx+1:idx+9] == "@:UNLOCK":
				replacements.append({'text': '@:UNLOCK', 'idx_start': idx, 'idx_end': idx+8})
			
			idx += 2 # Skip next character - restart
			continue
		
		elif msg[idx] == "@":
			
			# Check for lock character
			if (not lock_is_set) and idx+5 < len(msg) and msg[idx+1:idx+6] == ':LOCK': # Set lock
				# Set lock
				lock_is_set = True
						
				# Remove sequence
				replacements.append({'text': '', 'idx_start': idx, 'idx_end': idx+5})
				is_invalid = True # Call code "invalid" color code so it doesnt trigger color replacement
			
			elif idx+7 < len(msg) and msg[idx+1:idx+8] == ":UNLOCK": # Remove lock
				# Remove lock
				lock_is_set = False
				
				# Remove sequence
				replacements.append({'text': '', 'idx_start': idx, 'idx_end': idx+7})
				is_invalid = True # Call code "invalid" color code so it doesnt trigger color replacement
			
		# Look for non-escaped >
		elif (not lock_is_set) and msg[idx] == '>':
			
			idx_start = idx
			is_permanent = False
			color_spec = c_bold
			is_invalid = False
			
			# Check for permanent change
			if idx+1 < len(msg) and msg[idx+1] == '>': # Permanent change
				is_permanent = True
				idx += 1
			
			# Check for color specifier or lock
			if idx+2 < len(msg) and msg[idx+1] == ':': # Found color specifier
				
				if msg[idx+2].upper() in ['1', 'M']:
					color_spec = c_main
				elif msg[idx+2].upper() in ['2', 'B']:
					color_spec = c_bold
				elif msg[idx+2].upper() in ['3', 'Q']:
					color_spec = c_quiet
				elif msg[idx+2].upper() in ['4', 'A']:
					color_spec = c_alt
				elif msg[idx+2].upper() in ['5', 'L']:
					color_spec = c_label
				# elif msg[idx+2].upper() == "F":
					
				# 	# Check if lock is being set
				# 	if idx+8 < len(msg) and msg[idx:idx+9].upper() == ">:FREEZE>":
						
				# 		# Set lock
				# 		lock_is_set = True
						
				# 		# Remove sequence
				# 		replacements.append({'text': '', 'idx_start': idx, 'idx_end': idx+8})
				# 		is_invalid = True # Call code "invalid" color code so it doesnt trigger color replacement

				else:
					# Unrecognized code, do not modify
					is_invalid = True
				
				idx += 2
			
			# Apply changes and text replacements
			if not is_invalid:
				replacements.append({'text': color_spec, 'idx_start': idx_start, 'idx_end':idx})
				
				# If permanent apply change
				if is_permanent:
					return_color = color_spec
		
		# Look for non-escaped <
		elif (not lock_is_set) and msg[idx] == '<':
			
			# # Check if lock is being set
			# if idx+8 < len(msg) and msg[idx:idx+9].upper() == "<:FREEZE<":
				
			# 	# Set lock
			# 	lock_is_set = False
				
			# 	# Remove sequence
			# 	replacements.append({'text': '', 'idx_start': idx, 'idx_end': idx+8})
			# elif :
			replacements.append({'text': return_color, 'idx_start': idx, 'idx_end': idx})
		
		# Increment counter
		idx += 1
		
	# Apply replacements
	rich_msg = msg
	for rpl in reversed(replacements):
		rich_msg = rich_msg[:rpl['idx_start']] + rpl['text'] + rich_msg[rpl['idx_end']+1:]
	
	return rich_msg
		

def mdprint(x:str, flush:bool=False, file=sys.stdout, end:str='\n', str_fmt:LogFormat=None) -> None:
	''' Calls print using markdown syntax.
	
	Args:
		x (str): String to print. Unlike the standard print function, x must be a string.
		flush (bool): (Optional) Sets if output is flushed immediately. Default=False.
		file: (Optional) file-like object to which the output should be written. Default is
			sys.stdout.
		end (str): (Optional) Defines what is printed at the end of the output. Default is
			newline.
		str_fmt (LogFormat): (Optional) Markdown format options.
	
	Returns
		None
	'''
	
	s = markdown(x, str_fmt=str_fmt)
	print(s, flush=flush, file=file, end=end)

class LogLevelDefinition:
	
	def __init__(self, lvl_int:int, lvl_name:str, main_color:str="", bold_color:str="", quiet_color:str="", alt_color:str="", label_color:str=""):
		
		# Define level name string, and level int.
		self.level_int = lvl_int
		self.level_name = lvl_name
		
		# Define color overrides. If NONE, will use LogPile defaults.
		self.main_color = main_color
		self.bold_color = bold_color
		self.quiet_color = quiet_color
		self.alt_color = alt_color
		self.label_color = label_color

def get_default_levels():
	"""
	Creates default log levels.
	"""
	
	log_levels = []
	
	log_levels.append(LogLevelDefinition(LOWDEBUG, "LOWDEBUG", label_color=Fore.LIGHTBLACK_EX))
	log_levels.append(LogLevelDefinition(DEBUG, "DEBUG", label_color=Fore.LIGHTBLACK_EX))
	log_levels.append(LogLevelDefinition(INFO, "INFO", label_color=Fore.GREEN))
	log_levels.append(LogLevelDefinition(WARNING, "WARNING", label_color=Fore.YELLOW))
	log_levels.append(LogLevelDefinition(ERROR, "ERROR", label_color=Fore.LIGHTRED_EX))
	log_levels.append(LogLevelDefinition(CRITICAL, "CRITICAL", label_color=Fore.RED))
	
	return log_levels

def _level_definition_to_dict(ld:LogLevelDefinition) -> dict:
	""" Serializes a LogLevelDefinition to a plain dict, for use in JSON (and
	similar) log level tables. """

	return {
		"level_int": ld.level_int,
		"level_name": ld.level_name,
		"main_color": ld.main_color,
		"bold_color": ld.bold_color,
		"quiet_color": ld.quiet_color,
		"alt_color": ld.alt_color,
		"label_color": ld.label_color,
	}

def _level_definition_from_dict(d:dict) -> LogLevelDefinition:
	""" Reconstructs a LogLevelDefinition from a dict produced by
	_level_definition_to_dict(). """

	return LogLevelDefinition(
		d["level_int"],
		d["level_name"],
		main_color=d.get("main_color", ""),
		bold_color=d.get("bold_color", ""),
		quiet_color=d.get("quiet_color", ""),
		alt_color=d.get("alt_color", ""),
		label_color=d.get("label_color", ""),
	)

class LogPile:
	"""
	Organizes a collection of LogEntries and creates new ones. All functions
	are thread safe.
	
	use_mutex allows the user to specify that the mutex should or should not be 
	used. Because mutexes are not serializable, if the LogPile object will need
	to be deepcopied, use_mutex should be set to false.
	
	Attributes:
	
		terminal_output_enable (bool): Enables or disables automatically \
			printing each log to the standard output.
		terminal_level (int): Log level, at or above, which logs will print to \
			the standard output.
		str_fmt (LogFormat): LogFormat settings
		logs (list): List of LogEntries contained in the LogPile.
		log_mutex (Lock): Used to protect the `logs` attribute and allow the \
			creation of logs across multiple threads.
		run_mutex (Lock): Used to protect

	"""

	def __init__(self, str_fmt:LogFormat=None, use_mutex:bool=True, level_list:list=None):
		"""
		Constructor for LogPile class.

		Parameters:
			str_fmt (LogFormat): Optional logformat settings.

		"""

		# Initialize format with defautl
		if str_fmt is None:
			str_fmt = LogFormat()

		self.terminal_output_enable = True
		self.terminal_level = INFO

		self.str_format = str_fmt
		
		self.logs = []
		
		# mutexes
		self.log_mutex = None
		self.run_mutex = None
		self.set_enable_mutex(use_mutex)
		
		# Try to initialize log_levels from arguments
		self.log_levels = None
		if level_list is not None:
			
			_ll_valid = True
			for li in level_list:
				if not isinstance(li, LogLevelDefinition):
					_ll_valid = False
					break
			
			if _ll_valid:
				self.log_levels = level_list
		
		# If log_level could not be init from arugments, use default
		if self.log_levels is None:

			self.log_levels = get_default_levels()

		# Tracks convenience-method names bound by add_level(), so a repeat
		# add_level() call for the same level name is allowed to rebind it.
		self._custom_level_methods = set()


	def set_enable_mutex(self, enabled:bool):
		
		if enabled:
			self.log_mutex = threading.Lock()
			self.run_mutex = threading.Lock()
		else:
			self.log_mutex = DummyMutex()
			self.run_mutex = DummyMutex()
	
	def set_show_detail(self, show_detail:bool):
		"""
		Sets whether the detail string is displayed in addition to the
		log message whenever logs are displayed.
		
		Parameters:
			show_detail (bool): Enable/disable detail
		
		Returns:
			None
		"""
		
		self.str_format.show_detail = show_detail
	
	def set_terminal_level(self, level):
		"""
		Sets the terminal display level from a level name string.
		
		Parameters:
			level_str (str/int): Level to set
		
		Returns:
			None
		"""
		
		if isinstance(level, str):
			lvl_int = str_to_level(level, self.log_levels)
			if lvl_int is None:
				print(f"Unrecognized log level '{level}'. Terminal level unchanged.")
				return
			self.terminal_level = lvl_int
		elif isinstance(level, int) or isinstance(level, float):
			self.terminal_level = int(level)

	def add_level(self, lvl_int:int, lvl_name:str, main_color:str="", bold_color:str="", quiet_color:str="", alt_color:str="", label_color:str="") -> LogLevelDefinition:
		"""
		Registers a custom log level on this LogPile and binds a matching
		convenience method to it, e.g. `pile.add_level(25, "NOTICE")` creates
		`pile.notice(message, detail="")`, mirroring the built-in `.info()`,
		`.warning()`, etc. methods.

		Calling this again with a `lvl_name` that was already added (case
		insensitive) updates that level's definition (e.g. to change its
		colors) and rebinds the same convenience method rather than adding a
		duplicate entry to `log_levels`.

		NOTE: The convenience method is bound to this specific LogPile
		*instance*, not the LogPile class. It will not appear in IDE
		autocomplete or pass static type checking, and it will not exist on
		any other LogPile instance. If you don't want a dynamic method, just
		append a LogLevelDefinition to `pile.log_levels` directly instead, and
		log at that level with `pile.add_log(lvl_int, message)`.

		Parameters:
			lvl_int (int): Log level int code
			lvl_name (str): Log level name. Must be a valid Python identifier
				once lower-cased, since it becomes the convenience method's
				name, and must not collide with an existing LogPile attribute
				(e.g. "logs", "add_log", or another built-in level name).
			main_color (str): Optional markdown 'main' color override
			bold_color (str): Optional markdown 'bold' color override
			quiet_color (str): Optional markdown 'quiet' color override
			alt_color (str): Optional markdown 'alt' color override
			label_color (str): Optional markdown 'label' color override

		Returns:
			(LogLevelDefinition): The level definition that was registered
		"""

		method_name = lvl_name.lower()

		if not method_name.isidentifier():
			raise ValueError(f"Cannot create a convenience method for level name '{lvl_name}': '{method_name}' is not a valid Python identifier.")

		# Guard against clobbering a real LogPile attribute/method. dir(self),
		# not dir(type(self)), because attributes like `logs`/`log_levels`/
		# `terminal_level` are set on the instance in __init__, not the class.
		# Names this same call previously bound are exempt, so re-calling
		# add_level() to update a level's colors is allowed.
		reserved_names = set(dir(self))
		if method_name in reserved_names and method_name not in self._custom_level_methods:
			raise ValueError(f"'{method_name}' collides with an existing LogPile attribute and cannot be used as a custom level name.")

		# Register (or replace, if this name was already registered) the level definition
		ld = LogLevelDefinition(lvl_int, lvl_name, main_color=main_color, bold_color=bold_color, quiet_color=quiet_color, alt_color=alt_color, label_color=label_color)
		existing_idx = find_level_in_list(lvl_name, self.log_levels)
		if existing_idx is not None:
			self.log_levels[existing_idx] = ld
		else:
			self.log_levels.append(ld)

		# Bind the convenience method to this instance
		def _log_at_custom_level(inst, message:str="", detail:str=""):
			inst.add_log(lvl_int, message, detail=detail)

		setattr(self, method_name, types.MethodType(_log_at_custom_level, self))
		self._custom_level_methods.add(method_name)

		return ld

	def lowdebug(self, message:str, detail:str=""):
		"""
		Logs data at LOWDEBUG level.
		
		Parameters:
			message (str): Message to add to log
			detail (str): Additional detail to add to log
		Returns:
			None
		"""
		
		self.add_log(LOWDEBUG, message, detail=detail)
	
	def debug(self, message:str, detail:str=""):
		"""
		Logs data at DEBUG level.
		
		Parameters:
			message (str): Message to add to log
			detail (str): Additional detail to add to log
		Returns:
			None
		"""
		
		self.add_log(DEBUG, message, detail=detail)
	
	def info(self, message:str, detail:str=""):
		"""
		Logs data at INFO level.
		
		Parameters:
			message (str): Message to add to log
			detail (str): Additional detail to add to log
		Returns:
			None
		"""
		
		self.add_log(INFO, message, detail=detail)
	
	def warning(self, message:str, detail:str=""):
		"""
		Logs data at WARNING level.
		
		Parameters:
			message (str): Message to add to log
			detail (str): Additional detail to add to log
		Returns:
			None
		"""
		
		self.add_log(WARNING, message, detail=detail)
	
	def error(self, message:str, detail:str=""):
		"""
		Logs data at ERROR level.
		
		Parameters:
			message (str): Message to add to log
			detail (str): Additional detail to add to log
		Returns:
			None
		"""
		
		self.add_log(ERROR, message, detail=detail)

	def critical(self, message:str, detail:str=""):
		"""
		Logs data at CRITICAL level.
		
		Parameters:
			message (str): Message to add to log
			detail (str): Additional detail to add to log
		Returns:
			None
		"""
		
		self.add_log(CRITICAL, message, detail=detail)
	
	def add_log(self, level:int, message:str, detail:str=""):
		"""
		Adds a log.
		
		Parameters:
			level (int): Level int code at which to add log
			message (str): Message to add to log
			detail (str): Additional detail to add to log
		Returns:
			None
		"""
		
		# Create new log object
		nl = LogEntry(level, message, detail=detail)
		
		# Add to list
		with self.log_mutex:
			self.logs.append(nl)
		
		# Process new log with any auto-running features
		with self.run_mutex:
			self.run_new_log(nl)
	
	def run_new_log(self, nl:LogEntry):
		"""
		Runs a new log, processing any instructions therein. Typically this just
		entails printing the log, formatted, to standard output.
		
		Parameters:
			nl (LogEntry): Log to run
		
		Returns:
			None
		"""
		
		# Print to terminal
		if self.terminal_output_enable:
			if nl.level >= self.terminal_level:
				print(f"{nl.str(self.str_format, self.log_levels)}{Style.RESET_ALL}")
	
	def to_dict(self):
		"""
		Returns a dictionary representing the logs in the LogPile.
		"""
		
		with self.log_mutex:
			return [x.get_dict() for x in self.logs]
	
	def save_json(self, save_filename:str):
		""" Saves the LogPile to a JSON file, carrying the same data as
		save_plflog(file_version="1.0"): every log entry, plus the full log
		level definitions (names and colors) needed to restore an equivalent
		LogPile on load. JSON is far less compact than a compressed .plflog
		file, but is human-readable and doesn't require h5py to read.

		Parameters:
			save_filename (str): filename to save

		Returns:
			None
		"""

		out = {
			"file_info": {
				"file_standard": "pylogfile.logpile",
				"format_version": "1.0",
				"encoding": "json",
			},
			"log_levels": [_level_definition_to_dict(ld) for ld in self.log_levels],
			"logs": self.to_dict(),
		}

		with open(save_filename, 'w') as fh:
			json.dump(out, fh, indent=4)

	def load_json(self, read_filename:str, clear_previous:bool=True) -> bool:
		"""
		Reads a LogPile from a JSON file previously written by save_json(),
		including its log level definitions.

		Parameters:
			read_filename (str): Name of file to read
			clear_previous (bool): Sets whether previous logs contained in the \
				LogPile shouold be erased before reading the file.

		Returns:
			(bool): True if successfully read file
		"""

		all_success = True

		# Read JSON dictionary
		with open(read_filename, 'r') as fh:
			ad = json.load(fh)

		# --- Validate file identity / version (mirrors _load_v1_plflog) ---
		file_info = ad.get('file_info', {})
		file_standard = file_info.get('file_standard')
		encoding = file_info.get('encoding')

		if file_standard != "pylogfile.logpile":
			raise ValueError(f"Unsupported or missing file_standard={file_standard!r} (expected a JSON file produced by LogPile.save_json()).")
		if encoding != "json":
			raise ValueError(f"Unsupported encoding={encoding!r} (expected 'json').")

		new_log_levels = [_level_definition_from_dict(d) for d in ad.get('log_levels', [])]

		with self.log_mutex:

			# Clear old logs
			if clear_previous:
				self.logs = []

			# Restore the log level definitions, if any were saved
			if new_log_levels:
				self.log_levels = new_log_levels

			# Populate logs
			for led in ad.get('logs', []):
				nl = LogEntry()
				if nl.init_dict(led):
					self.logs.append(nl)
				else:
					all_success = False

		return all_success
	
	def save_plflog(self, filename:str, file_version:str="1.0"):
		""" Saves the log data to a PLF file.
		
		Parameters:
			filename (str): File to save
			file_version (str): File version to save. Options are 0.0 and 1.0.
		
		"""
		
		if file_version == "1.0":
			return self._save_v1_plflog(filename)
		elif file_version == "0.0":
			return self._save_v0_plflog(filename)
		else: # Default to newest version
			return self._save_v1_plflog(filename)
	
	def _save_v0_plflog(self, save_filename):
		"""
		Saves all logs to a legacy (v0) .plflog file (HDF5-based).
		
		Parameters:
			save_filename (str): Name of file to save to
		
		Returns:
			None
		"""
		
		#TODO: This should return a bool for success
		
		ad = self.to_dict()
		
		message_list = []
		detail_list = []
		timestamp_list = []
		level_list = []
		
		#NOTE: Unlike v1, v0 files cannot save default levels. As such, the objects
		# level list is ignored in favor of the v0 defaults. 
		default_levels = get_default_levels()
		
		# Build the column data for the HDF5 datasets
		for de in ad:

			message_list.append(de['message'])
			detail_list.append(de['detail'])
			timestamp_list.append(de['timestamp'])

			# Fall back to the raw level number (as a string) if it isn't one of
			# the v0 default levels, so an unregistered custom level can't crash
			# the save (see NOTE above: v0 can't represent custom levels anyway).
			lvl_str = level_to_str( de['level'], default_levels)
			if lvl_str is None:
				lvl_str = str(de['level'])
			level_list.append(lvl_str)
		
		# Write file
		with h5py.File(save_filename, 'w') as fh:
			fh.create_group("logs")
			fh['logs'].create_dataset('message', data=message_list)
			fh['logs'].create_dataset('detail', data=detail_list)
			fh['logs'].create_dataset('timestamp', data=timestamp_list)
			fh['logs'].create_dataset('level', data=level_list)

	def _save_v1_plflog(self, save_filename):
		ad = self.to_dict()
		
		# Pull columns
		messages  = [de.get("message", "") for de in ad]
		details   = [de.get("detail",  "") for de in ad]
		timestamps = [de.get("timestamp", 0) for de in ad]

		# Canonicalize each level against self.log_levels where possible, but
		# fall back to the raw level number if it isn't registered (custom/
		# hardcoded levels are allowed to be logged without being registered -
		# see NOTE near the top of this file).
		levels = []
		for de in ad:
			raw_level = de.get("level", 0)
			resolved = str_to_level(raw_level, self.log_levels)
			levels.append(resolved if resolved is not None else raw_level)

		# ---- Ensure timestamp is compact ----
		# If timestamps are already numeric (recommended): keep as int64.
		# If they're datetime objects, convert to int64 ns.
		# If they're ISO strings, consider converting BEFORE this point.
		ts = np.fromiter((_to_epoch_ns(t) for t in timestamps), dtype=np.int64, count=len(timestamps))


		# ---- Dictionary-encode repeating strings ----
		# message table
		msg_to_id = {}
		msg_ids = np.empty(len(messages), dtype=np.int32)
		msg_table = []
		for i, s in enumerate(messages):
			# normalize to str
			if s is None:
				s = ""
			else:
				s = str(s)
			
			# Check if message is new or prev. recorded
			j = msg_to_id.get(s)
			
			# If message is new, add to table
			if j is None:
				j = len(msg_table)
				msg_to_id[s] = j
				msg_table.append(s)
			
			# Add ID to list of IDs
			msg_ids[i] = j

		# detail table
		det_to_id = {}
		det_ids = np.empty(len(details), dtype=np.int32)
		det_table = []
		for i, s in enumerate(details):
			if s is None:
				s = ""
			else:
				s = str(s)
			j = det_to_id.get(s)
			if j is None:
				j = len(det_table)
				det_to_id[s] = j
				det_table.append(s)
			det_ids[i] = j
		
		lvl = np.asarray(levels, dtype=np.int16)
		
		# ---- Write file with compression ----
		# gzip gives best size; lzf is faster. shuffle often helps gzip.
		compression = "gzip"
		compression_opts = 6
		shuffle = True
		
		# Chunk by rows; pick something reasonable for append/read patterns.
		n = len(ad)
		chunk_rows = min(max(1024, n // 100 if n else 1024), 16384)
		
		# Use UTF-8 variable-length strings for tables
		str_dt = h5py.string_dtype(encoding="utf-8")
		
		# ---- Log level definitions ----
		level_defs = self.log_levels if self.log_levels is not None else []
		level_ints = np.asarray([ld.level_int for ld in level_defs], dtype=np.int32)
		level_names = ["" if ld.level_name is None else str(ld.level_name) for ld in level_defs]
		level_main = ["" if ld.main_color is None else str(ld.main_color) for ld in level_defs]
		level_bold = ["" if ld.bold_color is None else str(ld.bold_color) for ld in level_defs]
		level_quiet = ["" if ld.quiet_color is None else str(ld.quiet_color) for ld in level_defs]
		level_alt = ["" if ld.alt_color is None else str(ld.alt_color) for ld in level_defs]
		level_label = ["" if ld.label_color is None else str(ld.label_color) for ld in level_defs]
		
		# Write file
		with h5py.File(save_filename, "w") as fh:
			
			mfi = fh.create_group("_file_info_")
			mfi.attrs["file_standard"] = "pylogfile.logpile"
			mfi.attrs["format_version"] = "1.0"
			mfi.attrs["encoding"] = "compressed"
			
			mfi.attrs["compression"] = compression
			mfi.attrs["compression_opts"] = compression_opts
			mfi.attrs["shuffle"] = shuffle
			
			g = fh.create_group("logs")
			
			# Tables of unique strings (usually small)
			g.create_dataset(
				"message_table", data=np.asarray(msg_table, dtype=object),
				dtype=str_dt, compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			g.create_dataset(
				"detail_table", data=np.asarray(det_table, dtype=object),
				dtype=str_dt, compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			
			# Per-log columns (highly compressible)
			try:
				g.create_dataset(
					"message_id", data=msg_ids,
					compression=compression, compression_opts=compression_opts,
					shuffle=shuffle, chunks=(chunk_rows,)
				)
				g.create_dataset(
					"detail_id", data=det_ids,
					compression=compression, compression_opts=compression_opts,
					shuffle=shuffle, chunks=(chunk_rows,)
				)
				g.create_dataset(
					"timestamp_ns", data=ts,
					compression=compression, compression_opts=compression_opts,
					shuffle=shuffle, chunks=(chunk_rows,)
				)
				g.create_dataset(
					"level", data=lvl,
					compression=compression, compression_opts=compression_opts,
					shuffle=shuffle, chunks=(chunk_rows,)
				)
			except:
				g.create_dataset(
				"message_id", data=msg_ids,
				compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
				)
				g.create_dataset(
					"detail_id", data=det_ids,
					compression=compression, compression_opts=compression_opts,
					shuffle=shuffle, chunks=True
				)
				g.create_dataset(
					"timestamp_ns", data=ts,
					compression=compression, compression_opts=compression_opts,
					shuffle=shuffle, chunks=True
				)
				g.create_dataset(
					"level", data=lvl,
					compression=compression, compression_opts=compression_opts,
					shuffle=shuffle, chunks=True
				)
			
			# Log level definitions (for round-tripping custom levels)
			gl = fh.create_group("log_levels")
			gl.create_dataset(
				"level_int", data=level_ints,
				compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			gl.create_dataset(
				"level_name", data=np.asarray(level_names, dtype=object),
				dtype=str_dt, compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			gl.create_dataset(
				"main_color", data=np.asarray(level_main, dtype=object),
				dtype=str_dt, compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			gl.create_dataset(
				"bold_color", data=np.asarray(level_bold, dtype=object),
				dtype=str_dt, compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			gl.create_dataset(
				"quiet_color", data=np.asarray(level_quiet, dtype=object),
				dtype=str_dt, compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			gl.create_dataset(
				"alt_color", data=np.asarray(level_alt, dtype=object),
				dtype=str_dt, compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			gl.create_dataset(
				"label_color", data=np.asarray(level_label, dtype=object),
				dtype=str_dt, compression=compression, compression_opts=compression_opts,
				shuffle=shuffle, chunks=True
			)
			
			# # Optional: store metadata for humans
			# g.attrs["timestamp_unit"] = "ns"
	
	def _load_v1_plflog(self, filename: str, clear_previous:bool=True):
		"""
		Load logs from the compressed (v1) .plflog file (HDF5-based) created by _save_v1_plflog().
		
		This populates the current LogPile instance (clears existing logs) and returns self.
		
		Expected layout:
		/_file_info_  (group with attrs)
		/logs/message_table, /logs/detail_table (string tables)
		/logs/message_id, /logs/detail_id, /logs/timestamp_ns, /logs/level (columns)
		"""
		
		with h5py.File(filename, "r") as fh:
			# --- Validate file identity / version (best-effort, but strict by default) ---
			if "_file_info_" not in fh:
				raise ValueError("Not a pylogfile compressed LogPile file: missing '/_file_info_'.")
			mfi = fh["_file_info_"]
			
			file_standard = mfi.attrs.get("file_standard", None)
			encoding = mfi.attrs.get("encoding", None)
			fmt_ver = mfi.attrs.get("format_version", None)
			
			if file_standard != "pylogfile.logpile":
				raise ValueError(f"Unsupported file_standard={file_standard!r}.")
			if encoding != "compressed":
				raise ValueError(f"Unsupported encoding={encoding!r} (expected 'compressed').")
			# If you want to support multiple versions later, loosen this check.
			if fmt_ver not in ("1.0", 1.0):
				raise ValueError(f"Unsupported format_version={fmt_ver!r}.")
			
			if "logs" not in fh:
				raise ValueError("Invalid file: missing '/logs' group.")
			g = fh["logs"]
			
			# --- Load required datasets ---
			required = [
				"message_table", "detail_table",
				"message_id", "detail_id",
				"timestamp_ns", "level",
			]
			missing = [k for k in required if k not in g]
			if missing:
				raise ValueError(f"Invalid file: missing datasets in '/logs': {missing}")
			
			# --- Decode tables to Python str (h5py may return bytes depending on dtype) ---
			def _to_str_array(a):
				# a may be dtype=object bytes, numpy bytes_, or str
				out = []
				for x in a:
					if isinstance(x, (bytes, np.bytes_)):
						out.append(x.decode("utf-8", errors="replace"))
					else:
						out.append(str(x))
				return out
			
			msg_table = g["message_table"][...]
			det_table = g["detail_table"][...]
			msg_id = g["message_id"][...]
			det_id = g["detail_id"][...]
			ts_ns = g["timestamp_ns"][...]
			lvl = g["level"][...]
			
			# --- Log level definitions (optional) ---
			if "log_levels" in fh:
				gl = fh["log_levels"]
				required_levels = [
					"level_int", "level_name",
					"main_color", "bold_color",
					"quiet_color", "alt_color", "label_color",
				]
				if not all(k in gl for k in required_levels):
					raise ValueError("Invalid file: '/log_levels' missing required datasets.")
				
				level_ints = gl["level_int"][...]
				level_names = _to_str_array(gl["level_name"][...])
				level_main = _to_str_array(gl["main_color"][...])
				level_bold = _to_str_array(gl["bold_color"][...])
				level_quiet = _to_str_array(gl["quiet_color"][...])
				level_alt = _to_str_array(gl["alt_color"][...])
				level_label = _to_str_array(gl["label_color"][...])
				
				if level_ints.ndim != 1:
					raise ValueError("Invalid file: '/log_levels/level_int' must be 1D.")
				
				n_levels = len(level_ints)
				if not all(len(x) == n_levels for x in [level_names, level_main, level_bold, level_quiet, level_alt, level_label]):
					raise ValueError("Invalid file: '/log_levels' datasets have inconsistent lengths.")
				
				self.log_levels = [
					LogLevelDefinition(
						int(level_ints[i]),
						level_names[i],
						main_color=level_main[i],
						bold_color=level_bold[i],
						quiet_color=level_quiet[i],
						alt_color=level_alt[i],
						label_color=level_label[i],
					)
					for i in range(n_levels)
				]
			
			# --- Basic shape sanity ---
			n = len(msg_id)
			if not (len(det_id) == len(ts_ns) == len(lvl) == n):
				raise ValueError(
					"Invalid file: column lengths differ "
					f"(message_id={len(msg_id)}, detail_id={len(det_id)}, "
					f"timestamp_ns={len(ts_ns)}, level={len(lvl)})."
				)
			
			msg_table_py = _to_str_array(msg_table)
			det_table_py = _to_str_array(det_table)
			
			# --- Bounds check IDs (defensive; avoids IndexError with corrupted files) ---
			if n:
				if msg_id.min() < 0 or msg_id.max() >= len(msg_table_py):
					raise ValueError("Invalid file: message_id contains out-of-range indices.")
				if det_id.min() < 0 or det_id.max() >= len(det_table_py):
					raise ValueError("Invalid file: detail_id contains out-of-range indices.")
			
			# --- Reconstruct per-record fields ---
			messages = [msg_table_py[int(i)] for i in msg_id]
			details = [det_table_py[int(i)] for i in det_id]

			# Levels: you stored int16 already (via str_to_level(...)).
			# If you have a level_to_str helper, you can optionally decode later.
			levels = lvl # [ level_to_str(int(x), self.log_levels) for x in lvl]
			
			# Timestamps: you stored epoch ns. Convert to datetime (UTC).
			# If your LogEntry expects a string timestamp instead, swap this to .isoformat().
			timestamps = [_epoch_ns_to_datetime(x) for x in ts_ns]
		
		with self.log_mutex:
			
			# Clear old logs
			if clear_previous:
				self.logs = []
			
			# Convert to dictionary
			for nm,nd,nt,nl in zip(messages, details, timestamps, levels):
				
				# Create dictionary
				dd = {'message': nm, 'detail':nd, 'timestamp': str(nt.strftime('%Y-%m-%d %H:%M:%S.%f')), 'level':nl}
				
				# Create LogEntry
				nl = LogEntry(message=nm, detail=nd)
				if nl.init_dict(dd):
					self.logs.append(nl)
				# else:
				# 	all_success = False
		
		return True
	
	def _load_v0_plflog(self, read_filename:str, clear_previous:bool=True):
		"""
		Reads logs from a legacy (v0) .plflog file (HDF5-based).
		
		Parameters:
			read_filename (str): Name of file to read
			clear_previous (bool): Sets whether previous logs contained in the \
				LogPile shouold be erased before reading the file.
		
		Returns:
			(bool): Success status
		"""
		
		all_success = True
		
		# Load file contents
		with h5py.File(read_filename, 'r') as fh:
			message_list = fh['logs']['message'][()]
			detail_list = fh['logs']['detail'][()]
			timestamp_list = fh['logs']['timestamp'][()]
			level_list = fh['logs']['level'][()]
			
		with self.log_mutex:
			
			# Clear old logs
			if clear_previous:
				self.logs = []
			
			#v0 files dont suppport custom log levels, so the default is always used.
			self.log_levels = get_default_levels()
			
			# Convert to dictionary
			for nm,nd,nt,nl in zip(message_list, detail_list, timestamp_list, level_list):
				
				# Create dictionary
				
				# Note that unlike saving a v1+ file, the levels are saved as a string, not an int. They must be translated.
				dd = {'message': nm.decode('utf-8'), 'detail':nd.decode('utf-8'), 'timestamp': nt.decode('utf-8'), 'level': str_to_level(nl.decode('utf-8'), self.log_levels)}
				
				# Create LogEntry
				nl = LogEntry(message=nm, detail=nd)
				if nl.init_dict(dd):
					self.logs.append(nl)
				else:
					all_success = False
		
		return all_success
	
	def load_plflog(self, filename:str, clear_previous:bool=True):
		"""
		Load any pylogfile .plflog file (legacy v0 or compressed v1) by auto-detecting its format.

		Returns:
			(bool): Success status
		"""

		with h5py.File(filename, "r") as fh:
			fmt = _detect_pylogfile_format(fh)

		# Re-open inside the chosen loader (simpler; avoids keeping handles around)
		if fmt == "1.0":
			return self._load_v1_plflog(filename, clear_previous=clear_previous)
		elif fmt == "0.0":
			return self._load_v0_plflog(filename, clear_previous=clear_previous)

		# Should never happen
		raise UnknownLogFileFormat(f"Internal error: unknown format tag {fmt!r}")
	
	#TODO: Implement or remove this
	def save_txt(self):
		pass

	def show_logs(self, min_level:int=LOWDEBUG, max_level:int=CRITICAL, max_number:int=None, from_beginning:bool=False, show_index:bool=True, sort_orders:SortConditions=None, str_fmt:LogFormat=None):
		"""
		Prints to standard output the logs matching the specified conditions.
		
		Args:
			min_level (int): Minimum logging level to display
			max_level (int): Maximum logging level to display
			max_number (int): Maximum number of logs to show
			from_beginning (bool): Show logs starting from beginning.
			show_index (bool): Show or hide the index of the log entry by each entry.
		
		Returns:
			None
		"""
		
		# Check max number is zero or less
		if max_number is not None and max_number < 1:
			return
		
		with self.log_mutex:
		
			# Get list order
			if not from_beginning:
				log_list = reversed(self.logs)
				idx_list = reversed(list(np.linspace(0, len(self.logs)-1, len(self.logs))))
			else:
				log_list = self.logs
				idx_list = list(np.linspace(0, len(self.logs)-1, len(self.logs)))
			
			# Scan over logs
			idx_str = ""
			for idx, lg in zip(idx_list, log_list):
				
				# Check log level
				if lg.level < min_level or lg.level > max_level:
					continue
				
				# If sort orders are provided, perform check
				if (sort_orders is not None):
					
					# If time and contents searches dont hit, skip entry
					if (not lg.matches_sort(sort_orders)):
						continue
					
					# Check if index filter is requested
					if (sort_orders.index_start is not None) and (sort_orders.index_end is not None):
						
						# If entry doesn't hit, skip it
						if (idx < sort_orders.index_start) or (idx > sort_orders.index_end):
							continue
				
				# Print log
				if show_index:
					# idx_str = f"{Fore.LIGHTBLACK_EX}[{Fore.YELLOW}{int(idx)}{Fore.LIGHTBLACK_EX}] "
					idx_str = f"{Fore.WHITE}[{Fore.WHITE}{int(idx)}{Fore.WHITE}] "
				
				if str_fmt is None:
					print(f"{idx_str}{lg.str(self.str_format, self.log_levels)}{Style.RESET_ALL}")
				else:
					print(f"{idx_str}{lg.str(str_fmt, self.log_levels)}{Style.RESET_ALL}")
				
				# Run counter if specified
				if max_number is not None:
					
					# Decrement
					max_number -= 1
					
					# Check for end
					if max_number < 1:
						cq = self.str_format.default_color['quiet']
						print(f"\t{cq}...{Style.RESET_ALL}")
						break

def are_equivalent_entries(log1:LogEntry, log2:LogEntry, time_tol_us:float=10):
	'''
	Compares two LogEntry objects. Returns true if they contain equivalent data.
	'''
	
	if log1.message != log2.message:
		return False
	if log1.detail != log2.detail:
		return False
	if log1.level != log2.level:
		return False
	
	tol = datetime.timedelta(microseconds=time_tol_us)
	if abs(log1.timestamp - log2.timestamp) > tol:
		return False
	
	return True

def are_equivalent_piles(lp1:LogPile, lp2:LogPile, time_tol_us:float=10):
	"""
	Compares two LogPile objects. Returns true if they contain equivalent logs.
	"""
	
	if len(lp1.logs) != len(lp2.logs):
		return False
	
	for idx, l in enumerate(lp1.logs):
		if not are_equivalent_entries(l, lp2.logs[idx]):
			return False
	
	return True