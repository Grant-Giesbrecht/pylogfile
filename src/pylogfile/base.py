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

#TODO: Save only certain log levels
#TODO: Autosave
#TODO: Log more info
#TODO: Log to string etc
#TODO: Integrate with logger

xDEBUG = -10
xINFO = -20
xWARNING = -30
xERROR = -40
xCRITICAL = -50

RECORD = -25
CORE = -30

NOTSET = 0
LOWDEBUG = 5	# For when you're having a really bad day
DEBUG = 10		# Used for debugging
INFO = 20		# Used for reporting basic high-level program functioning (that does not involve an error)
WARNING = 30 	# Warning for software
ERROR = 40		# Software error
CRITICAL = 50	# Critical error

class SortConditions:
	""" Class used to define the conditions of a LogEntry sort request."""
	
	time_start = None
	time_end = None
	contains_and = []
	contains_or = []
	index_start = None
	index_end = None

class DummyMutex:
	def __init__(self):
		pass
	def __enter__(self):
		return
	def __exit__(self, exc_type, exc_value, traceback):
		return

#TODO: Make the keys in color_overrides match the variables in LogEntry (currently undefined)
@dataclass
class LogFormat:
	""" Class used to describe the cosmetic formatting of LogEntries printed to 
	standard output. """
	
	show_detail:bool = False
	use_color:bool = True
	default_color:dict = field(default_factory=lambda: {"main": Fore.WHITE+Back.RESET, "bold": Fore.LIGHTBLUE_EX, "quiet": Fore.LIGHTBLACK_EX, "alt": Fore.YELLOW, "label": Fore.GREEN})
	color_overrides:dict = field(default_factory=lambda: { LOWDEBUG: {"label": Fore.WHITE},
														DEBUG: {"label": Fore.LIGHTBLACK_EX},
														INFO: {},
														WARNING: {"label": Fore.YELLOW},
														ERROR: {"label": Fore.LIGHTRED_EX},
														CRITICAL: {"label": Fore.RED},
														RECORD: {"label": Fore.CYAN},
														CORE: {"label": Fore.CYAN}
	})
	detail_indent:str = "\t "
	strip_newlines:bool = True

def str_to_level(lvl:str) -> int:
	"""
	Converts a log level string to its associated int code.
	
	Args:
		lvl (str): Log level string, case-insensitive
	
	Returns:
		int: The log level int code
	"""
	
	lvl = lvl.upper()
	
	# Set level
	if lvl == "LOWDEBUG":
		return LOWDEBUG
	elif lvl == "DEBUG":
		return DEBUG
	elif lvl == "RECORD":
		return RECORD
	elif lvl == "INFO":
		return INFO
	elif lvl == "CORE":
		return CORE
	elif lvl == "WARNING":
		return WARNING
	elif lvl == "ERROR":
		return ERROR
	elif lvl == "CRITICAL":
		return CRITICAL
	else:
		return False

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
		
		# Set level
		if level not in [LOWDEBUG, DEBUG, INFO, WARNING, ERROR, CRITICAL]:
			self.level = INFO
		else:
			self.level = level
		
		# Set message
		self.message = message
		self.detail = detail
	

	
	def init_dict(self, data_dict:dict) -> bool:
		"""
		Initializes a provided dictionary with the data from the LogEntry. Used when
		preparing to save logs to file.
		
		Parameters:
			data_dict (dict): Dictionary to populate with data
			
		Returns:
			(bool): Success status in converting class contents to dict
		"""
		
		# Extract data from dict
		try:
			lvl = data_dict['level']
			msg = data_dict['message']
			dtl = data_dict['detail']
			ts = data_dict['timestamp']
		except:
			return False
		
		# Set level
		self.level = str_to_level(lvl)
		if self.level is None:
			return False
		
		self.message = msg # Set message
		self.detail = dtl
		self.timestamp = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
		
		return True
	
	def get_level_str(self) -> str:
		"""
		Converts the log's level to a string
		
		Returns:
			(str): Log level represented as a string.
		"""
		
		if self.level == LOWDEBUG:
			return "LOWDEBUG"
		elif self.level == DEBUG:
			return "DEBUG"
		elif self.level == RECORD:
			return "RECORD"
		elif self.level == INFO:
			return "INFO"
		elif self.level == CORE:
			return "CORE"
		elif self.level == WARNING:
			return "WARNING"
		elif self.level == ERROR:
			return "ERROR"
		elif self.level == CRITICAL:
			return "CRITICAL"
		else:
			return "??"
		
	def get_dict(self) -> dict:
		""" Returns the contents of the log as a dictionary.
		
		Returns:
			(dict): Dictionary containing log entry data
		"""
		return {"message":self.message, "detail":self.detail, "timestamp":str(self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')) , "level":self.get_level_str()}
	
	def get_json(self) -> str:
		"""
		Returns the class as a JSON string.
		
		Returns:
			(str): All class data in JSON form
		"""
		return json.dumps(self.get_dict())
	
	def str(self, str_fmt:LogFormat=None) -> str:
		""" Represent the log entry as a formatted string suitable for printing.
		
		Parameters:
			str_fmt (LogFormat): Format specification
		
		Returns:
			(str): String representation of class
		"""
		
		# Get format specifier
		if str_fmt is None:
			str_fmt = LogEntry.default_format
		
		# Apply or wipe colors
		if str_fmt.use_color:
			c_main = str_fmt.default_color['main']
			c_bold = str_fmt.default_color['bold']
			c_quiet = str_fmt.default_color['quiet']
			c_alt = str_fmt.default_color['alt']
			c_label = str_fmt.default_color['label']
			
			# Apply log-level color-overrides
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
		s = f"{c_alt}[{c_label}{self.get_level_str()}{c_alt}]{c_main} {markdown(message, str_fmt)} {c_quiet}| {self.timestamp}{Style.RESET_ALL}"
		
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
				if (targ not in self.message) and (targ not in self.detail):
					return False
		
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
			
			idx += 2 # Skip next character - restart
			continue
		
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
				elif msg[idx+2].upper() in ['5', 'F']:
					
					# Check if lock is being set
					if idx+8 < len(msg) and msg[idx:idx+9].upper() == ">:FREEZE>":
						
						# Set lock
						lock_is_set = True
						
						# Remove sequence
						replacements.append({'text': '', 'idx_start': idx, 'idx_end': idx+8})
						is_invalid = True # Call code "invalid" color code so it doesnt trigger color replacement

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
		elif msg[idx] == '<':
			
			# Check if lock is being set
			if idx+8 < len(msg) and msg[idx:idx+9].upper() == "<:FREEZE<":
				
				# Set lock
				lock_is_set = False
				
				# Remove sequence
				replacements.append({'text': '', 'idx_start': idx, 'idx_end': idx+8})
			elif (not lock_is_set):
				replacements.append({'text': return_color, 'idx_start': idx, 'idx_end': idx})
		
		# Increment counter
		idx += 1
		
	# Apply replacements
	rich_msg = msg
	for rpl in reversed(replacements):
		rich_msg = rich_msg[:rpl['idx_start']] + rpl['text'] + rich_msg[rpl['idx_end']+1:]
	
	return rich_msg
		

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
		autosave_enable (bool): Tracks if autosave is enabled
		filename (str): Name to autosave
		autosave_period_s (float): Time between autosaves in seconds
		autosave_level (int): Minimum log level to save. 
		autosave_format (str): File format for autosave. Options are 'format-json' and 'format-txt'.
		str_fmt (LogFormat): LogFormat settings
		logs (list): List of LogEntries contained in the LogPile.
		log_mutex (Lock): Used to protect the `logs` attribute and allow the \
			creation of logs across multiple threads.
		run_mutex (Lock): Used to protect
	
	"""
	
	#TODO: Add HDF
	JSON = "format-json"
	TXT = "format-txt"
	
	#TODO: Implement autosave. and autosave settigns.  
	def __init__(self, filename:str="", autosave:bool=False, str_fmt:LogFormat=None, use_mutex:bool=True):
		"""
		Constructor for LogPile class. 
		
		Parameters:
			filename (str): Name of file to autosave to.
			autosave (bool): Enable or disable autosave
			str_fmt (LogFormat): Optional logformat settings.
		
		"""
		
		# Initialize format with defautl
		if str_fmt is None:
			str_fmt = LogFormat()
		
		self.terminal_output_enable = True
		self.terminal_level = INFO
		
		self.autosave_enable = autosave
		self.filename = filename
		self.autosave_period_s = 300
		self.autosave_level = INFO
		self.autosave_format = LogPile.JSON
		
		self.str_format = str_fmt
		
		self.logs = []
		
		# mutexes
		self.log_mutex = None
		self.run_mutex = None
		self.set_enable_mutex(use_mutex)
	
	def set_enable_mutex(self, enabled:bool):
		
		if enabled:
			self.log_mutex = threading.Lock()
			self.run_mutex = threading.Lock()
		else:
			self.log_mutex = DummyMutex()
			self.run_mutex = DummyMutex()
	
	def set_terminal_level(self, level_str:str):
		"""
		Sets the terminal display level from a level name string.
		
		Parameters:
			level_str (str): Level to set
		
		Returns:
			None
		"""
		
		self.terminal_level = str_to_level(level_str)
	
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
				print(f"{nl.str(self.str_format)}{Style.RESET_ALL}")
	
	def to_dict(self):
		"""
		Returns a dictionary representing the logs in the LogPile.
		"""
		
		with self.log_mutex:
			return [x.get_dict() for x in self.logs]
	
	def save_json(self, save_filename:str):
		"""Saves all log data to a JSON file.
		
		Parameters:
			save_filename (str): filename to save
		
		Returns:
			None
		"""
		
		ad = self.to_dict()
		
		# Open file
		with open(save_filename, 'w') as fh:
			json.dump({"logs":ad}, fh, indent=4)
	
	def load_json(self, read_filename:str, clear_previous:bool=True) -> bool:
		"""
		Reads logs from a JSON file.
		
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
		
		with self.log_mutex:
			
			# Clear old logs
			if clear_previous:
				self.logs = []
			
			# Populate logs
			for led in ad['logs']:
				nl = LogEntry()
				if nl.init_dict(led):
					self.logs.append(nl)
				else:
					all_success = False
		
		return all_success
	
	def save_hdf(self, save_filename):
		"""
		Saves all logs to an HDF5 file.
		
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
		
		# Create HDF data types
		for de in ad:
			
			message_list.append(de['message'])
			detail_list.append(de['detail'])
			timestamp_list.append(de['timestamp'])
			level_list.append(de['level'])
		
		# Write file
		with h5py.File(save_filename, 'w') as fh:
			fh.create_group("logs")
			fh['logs'].create_dataset('message', data=message_list)
			fh['logs'].create_dataset('detail', data=detail_list)
			fh['logs'].create_dataset('timestamp', data=timestamp_list)
			fh['logs'].create_dataset('level', data=level_list)
	
	def load_hdf(self, read_filename:str, clear_previous:bool=True):
		"""
		Reads logs from an HDF5 file.
		
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
			
			# Convert to dictionary
			for nm,nd,nt,nl in zip(message_list, detail_list, timestamp_list, level_list):
				
				# Create dictionary
				dd = {'message': nm.decode('utf-8'), 'detail':nd.decode('utf-8'), 'timestamp': nt.decode('utf-8'), 'level':nl.decode('utf-8')}
				
				# Create LogEntry
				nl = LogEntry(message=nm, detail=nd)
				if nl.init_dict(dd):
					self.logs.append(nl)
				else:
					all_success = False
		
		return all_success
			
	
	#TODO: Implement or remove this
	def save_txt(self):
		pass
	
	# TODO: Implement or remove this
	def begin_autosave(self):
		pass
	
	def show_logs(self, min_level:int=DEBUG, max_level:int=CRITICAL, max_number:int=None, from_beginning:bool=False, show_index:bool=True, sort_orders:SortConditions=None, str_fmt:LogFormat=None):
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
					print(f"{idx_str}{lg.str(self.str_format)}{Style.RESET_ALL}")
				else:
					print(f"{idx_str}{lg.str(str_fmt)}{Style.RESET_ALL}")
				
				# Run counter if specified
				if max_number is not None:
					
					# Decrement
					max_number -= 1
					
					# Check for end
					if max_number < 1:
						cq = self.str_format.default_color['quiet']
						print(f"\t{cq}...{Style.RESET_ALL}")
						break