import datetime
import json
from dataclasses import dataclass, field
from colorama import Fore, Style, Back
import re
import h5py

#TODO: Save only certain log levels
#TODO: Autosave
#TODO: Log more info
#TODO: Log to string etc
#TODO: Integrate with logger

@dataclass
class LogFormat:
	
	show_detail:bool = False
	use_color:bool = True
	default_color:dict = field(default_factory=lambda: {"main": Fore.WHITE+Back.RESET, "bold": Fore.LIGHTBLUE_EX, "quiet": Fore.LIGHTBLACK_EX, "alt": Fore.YELLOW, "label": Fore.GREEN})
	detail_indent:str = "\t "

class LogEntry:
	
	default_format = LogFormat()
	
	RECORD = -15		# (Special) Used for recording the status of an experiment for scientific integrity. Useful for record keeping, but shouldn't need to be viewed unless verifying details of an experiment.
	CORE = -25		# (Special) Used for reporting core scientific changes and results
	
	DEBUG = 10		# Used for debugging
	INFO = 20		# Used for reporting basic high-level program functioning (that does not involve an error)
	WARNING = 30 	# Warning for software
	ERROR = 40		# Software error
	CRITICAL = 50	# Critical error
	
	def __init__(self, level:int=0, message:str="", detail:str=None):
		
		# Set timestamp
		self.timestamp = datetime.datetime.now()
		
		# Set level
		if level not in [LogEntry.DEBUG, LogEntry.INFO, LogEntry.WARNING, LogEntry.ERROR, LogEntry.CRITICAL]:
			self.level = LogEntry.INFO
		else:
			self.level = level
		
		# Set message
		self.message = message
		self.detail = detail
	
	def init_dict(self, data_dict:dict) -> bool:
		
		# Extract data from dict
		try:
			lvl = data_dict['level']
			msg = data_dict['message']
			dtl = data_dict['detail']
			ts = data_dict['timestamp']
		except:
			return False
		
		# Set level
		if lvl == "DEBUG":
			self.level = LogEntry.DEBUG
		elif lvl == "RECORD":
			self.level = LogEntry.RECORD
		elif lvl == "INFO":
			self.level = LogEntry.INFO
		elif lvl == "CORE":
			self.level = LogEntry.CORE
		elif lvl == "WARNING":
			self.level = LogEntry.WARNING
		elif lvl == "ERROR":
			self.level = LogEntry.ERROR
		elif lvl == "CRITICAL":
			self.level = LogEntry.CRITICAL
		else:
			return False
		
		self.message = msg # Set message
		self.detail = dtl
		self.timestamp = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
		
		return True
	
	def get_level_str(self):
		
		if self.level == LogEntry.DEBUG:
			return "DEBUG"
		elif self.level == LogEntry.RECORD:
			return "RECORD"
		elif self.level == LogEntry.INFO:
			return "INFO"
		elif self.level == LogEntry.CORE:
			return "CORE"
		elif self.level == LogEntry.WARNING:
			return "WARNING"
		elif self.level == LogEntry.ERROR:
			return "ERROR"
		elif self.level == LogEntry.CRITICAL:
			return "CRITICAL"
		else:
			return "??"
		
	def get_dict(self):
		return {"message":self.message, "detail":self.detail, "timestamp":str(self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')) , "level":self.get_level_str()}
	
	def get_json(self):
		return json.dumps(self.get_dict())
	
	def str(self, str_fmt:LogFormat=None) -> str:
		''' Represent the log entry as a string.'''
		
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
		else:
			c_main = ''
			c_bold = ''
			c_quiet = ''
			c_alt = ''
			c_label = ''
		
		# Create base string
		s = f"{c_alt}[{c_label}{self.get_level_str()}{c_alt}]{c_main} {markdown(self.message, str_fmt)} {c_quiet}| {self.timestamp}{Style.RESET_ALL}"
		
		# Add detail if requested
		if str_fmt.show_detail and self.detail is not None:
			s = s + f"\n{str_fmt.detail_indent}{c_quiet}{self.detail}"
		
		return s
	
def markdown(msg:str, str_fmt:LogFormat=None) -> str:
	""" Applys Pylogfile markdown
		> Temporarily change to bold
		< Revert to previous color
		
		>:n Temporariliy change to color 'n'. n-codes: Case insensitive
			1 or m: Main
			2 or b: Bold
			3 or q: Quiet
			4 or a: Alt
			5 or l: Label
		
		>> Permanently change to bold
		>>:n Permanently change to color n
		
		\\>, \\<, Type character without color adjustment. So to get >>:3
			to appear you'd type \\>\\>:3.
		
		If you want to type > followed by a character
		
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
	while idx < len(msg):
		
		# Look for escape character
		if msg[idx] == '\\':
			
			# If next character is > or <, remove the escape
			if idx+1 < len(msg) and msg[idx+1] == '>':
				replacements.append({'text': '>', 'idx_start': idx, 'idx_end': idx+1})
			elif idx+1 < len(msg) and msg[idx+1] == '<':
				replacements.append({'text': '<', 'idx_start': idx, 'idx_end': idx+1})
			
			idx += 2 # Skip next character - restart
			continue
		
		# Look for non-escaped >
		elif msg[idx] == '>':
			
			idx_start = idx
			is_permanent = False
			color_spec = c_bold
			is_invalid = False
			
			# Check for permanent change
			if idx+1 < len(msg) and msg[idx+1] == '>': # Permanent change
				is_permanent = True
				idx += 1
			
			# Check for color specifier
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
			
			replacements.append({'text': return_color, 'idx_start': idx, 'idx_end': idx})
		
		# Increment counter
		idx += 1
		
	# Apply replacements
	rich_msg = msg
	for rpl in reversed(replacements):
		rich_msg = rich_msg[:rpl['idx_start']] + rpl['text'] + rich_msg[rpl['idx_end']+1:]
	
	return rich_msg
		

class LogPile:
	
	JSON = "format-json"
	TXT = "format-txt"
	
	def __init__(self, filename:str="", autosave:bool=False, str_fmt:LogFormat=None):
		
		# Initialize format with defautl
		if str_fmt is None:
			str_fmt = LogFormat()
		
		self.terminal_output_enable = True
		self.terminal_output_details = False
		self.terminal_level = LogEntry.INFO
		
		self.autosave_enable = autosave
		self.filename = filename
		self.autosave_period_s = 300
		self.autosave_level = LogEntry.INFO
		self.autosave_format = LogPile.JSON
		
		self.str_format = str_fmt
		
		self.logs = []
	
	def debug(self, message:str, detail:str=None):
		''' Logs data at DEBUG level. '''
		
		self.add_log(LogEntry.DEBUG, message, detail=detail)
	
	def info(self, message:str, detail:str=None):
		''' Logs data at INFO level. '''
		
		self.add_log(LogEntry.INFO, message, detail=detail)
	
	def warning(self, message:str, detail:str=None):
		''' Logs data at WARNING level. '''
		
		self.add_log(LogEntry.WARNING, message, detail=detail)
	
	def error(self, message:str, detail:str=None):
		''' Logs data at ERROR level. '''
		
		self.add_log(LogEntry.ERROR, message, detail=detail)

	def critical(self, message:str, detail:str=None):
		''' Logs data at CRITICAL level. '''
		
		self.add_log(LogEntry.CRITICAL, message, detail=detail)
	
	def add_log(self, level:int, message:str, detail:str=None):
		
		# Create new log object
		nl = LogEntry(level, message, detail=detail)
		
		# Add to list
		self.logs.append(nl)
		
		# Process new log with any auto-running features
		self.run_new_log(nl)
	
	def run_new_log(self, nl:LogEntry):
		
		# Print to terminal
		if self.terminal_output_enable:
			print(nl.str(self.str_format))
	
	def get_json(self):
		pass
	
	def save_json(self, save_filename:str):
		''' Saves all log data to a JSON file '''
		
		ad = [x.get_dict() for x in self.logs]
		
		# Open file
		with open(save_filename, 'w') as fh:
			json.dump({"logs":ad}, fh, indent=4)
	
	def load_json(self, read_filename:str):
		
		all_success = True
		
		# Read JSON dictionary
		with open(read_filename, 'r') as fh:
			ad = json.load(fh)
			
		print(ad)
		
		# Populate logs
		for led in ad['logs']:
			nl = LogEntry()
			if nl.init_dict(led):
				self.logs.append(nl)
			else:
				all_success = False
		
		return all_success
	
	def save_txt(self):
		pass
	
	def begin_autosave(self):
		pass
	
	def read_json(self):
		pass
	
	def save_hdf5(self, filename:str):
		pass
		# # Open hdf5 file
		# with h5py.File(filename, 'w') as f:
			
		# 	dslog = f.create_dataset('log')