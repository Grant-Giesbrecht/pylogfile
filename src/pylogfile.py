import datetime
import json
from dataclasses import dataclass
from colorama import Fore, Style, Back
import re

#TODO: Save only certain log levels
#TODO: Autosave
#TODO: Log more info
#TODO: Log to string etc
#TODO: Integrate with logger

@dataclass
class LogFormat:
	
	show_detail:bool = False
	default_color:dict = {"main": Fore.WHITE+Back.RESET, "bold": Fore.GREEN, "quiet": Fore.LIGHTBLACK_EX, "alt": Fore.YELLOW, "label": Fore.GREEN}
	detail_indent:str = "\L "

class LogEntry:
	
	DEBUG = 10
	INFO = 20
	WARNING = 30
	ERROR = 40
	CRITICAL = 50
	
	def __init__(self, level:int, message:str, detail:str=None):
		
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
	
	def get_level_str(self):
		
		if self.level == LogEntry.DEBUG:
			return "DEBUG"
		elif self.level == LogEntry.INFO:
			return "INFO"
		elif self.level == LogEntry.WARNING:
			return "WARNING"
		elif self.level == LogEntry.ERROR:
			return "ERROR"
		elif self.level == LogEntry.CRITICAL:
			return "CRITICAL"
		else:
			return "??"
		
	def get_dict(self):
		return {"message":self.message, "detail":self.detail, "timestamp":str(self.timestamp), "level":self.get_level_str()}
	
	def get_json(self):
		return json.dumps(self.get_dict())
	
	def str(self, format:LogFormat):
		
		c_main = format.default_color['main']
		c_bold = format.default_color['bold']
		c_quiet = format.default_color['quiet']
		c_alt = format.default_color['alt']
		c_label = format.default_color['label']
		
		s = f"{c_alt}[{c_label}{self.get_level_str()}{c_alt}]{c_main} {self.message} {c_quiet}| {self.timestamp}"
		
		if format.show_detail:
			s = s + f"\n{format.detail_indent}{c_quiet}{self.detail}"
	
	def color_markdown(self, msg:str):
		""" Logs a message. Applys rules:
			> Temporarily changes color to bold
			< retursn color to that prior to priming (uses standard if not specified in msg string).
			>1 < main
			>>1 permanent to main
			>2
			\\>, \\<, Type character without color adjustment.
			
		"""
		
		main_color = Fore.LIGHTBLACK_EX
		prime_color = Fore.WHITE
		
		rich_msg = f"{main_color}{msg}{Style.RESET_ALL}"
		
		# Replace > < that are not escaped with color
		rich_msg = re.sub("(?<!\\\\)>", f"{prime_color}", rich_msg)
		rich_msg = re.sub("(?<!\\\\)<", f"{main_color}", rich_msg)
		
		# Remove escape characters
		rich_msg = rich_msg.replace("\\>", f">")
		rich_msg = rich_msg.replace("\\<", f"<")
		
		return rich_msg
		

class LogPile:
	
	JSON = "format-json"
	TXT = "format-txt"
	
	def __init__(self, filename:str="", autosave:bool=False):
		
		self.terminal_output_enable = True
		self.terminal_output_details = False
		self.terminal_level = LogEntry.INFO
		
		self.autosave_enable = autosave
		self.filename = filename
		self.autosave_period_s = 300
		self.autosave_level = LogEntry.INFO
		self.autosave_format = LogPile.JSON
		
		self.logs = []
	
	def debug(self, message:str):
		''' Logs data at DEBUG level. '''
		
		# Create new log object
		nl = LogEntry(LogEntry.DEBUG, message)
		
		# Add to list
		self.logs.append(nl)
	
	def info(self, message:str):
		''' Logs data at INFO level. '''
		
		# Create new log object
		nl = LogEntry(LogEntry.INFO, message)
		
		# Add to list
		self.logs.append(nl)
	
	def warning(self, message:str):
		''' Logs data at WARNING level. '''
		
		# Create new log object
		nl = LogEntry(LogEntry.WARNING, message)
		
		# Add to list
		self.logs.append(nl)
	
	def error(self, message:str):
		''' Logs data at ERROR level. '''
		
		# Create new log object
		nl = LogEntry(LogEntry.ERROR, message)
		
		# Add to list
		self.logs.append(nl)

	def critical(self, message:str):
		''' Logs data at CRITICAL level. '''
		
		# Create new log object
		nl = LogEntry(LogEntry.CRITICAL, message)
		
		# Add to list
		self.logs.append(nl)
	
	def handle_new_log(self, nl:LogEntry):
		
		if self.terminal_output_enable:
			self.print(nl.str())
	
	def get_json(self):
		pass
	
	def get_arraydict(self):
		''' Returns an array of dictionaries for each log'''
		return [x.get_dict() for x in self.logs]
	
	def save_json(self, save_filename:str):
		''' Saves all log data to a JSON file '''
		
		# Open file
		with open(save_filename, 'w') as fh:
			json.dump({"logs":self.get_arraydict()}, fh, indent=4)
	
	def save_txt(self):
		pass
	
	def begin_autosave(self):
		pass
	
	def read_json(self):
		pass