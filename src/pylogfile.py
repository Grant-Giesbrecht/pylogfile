import datetime
import json
from dataclasses import dataclass, field
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
	default_color:dict = field(default_factory=lambda: {"main": Fore.WHITE+Back.RESET, "bold": Fore.LIGHTBLUE_EX, "quiet": Fore.LIGHTBLACK_EX, "alt": Fore.YELLOW, "label": Fore.GREEN})
	detail_indent:str = "\L "

class LogEntry:
	
	default_format = LogFormat()
	
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
		
		if format is None:
			format = LogEntry.default_format
		
		c_main = format.default_color['main']
		c_bold = format.default_color['bold']
		c_quiet = format.default_color['quiet']
		c_alt = format.default_color['alt']
		c_label = format.default_color['label']
		
		s = f"{c_alt}[{c_label}{self.get_level_str()}{c_alt}]{c_main} {self.message} {c_quiet}| {self.timestamp}"
		
		if format.show_detail:
			s = s + f"\n{format.detail_indent}{c_quiet}{self.detail}"
	
	def color_markdown(self, msg:str, format:LogFormat=None):
		""" Logs a message. Applys rules:
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
		
		if format is None:
			format = LogEntry.default_format
		
		# Create local variables for color
		c_main = format.default_color['main']
		c_bold = format.default_color['bold']
		c_quiet = format.default_color['quiet']
		c_alt = format.default_color['alt']
		c_label = format.default_color['label']
		
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