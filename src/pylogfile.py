import datetime
import json

#TODO: Save only certain log levels
#TODO: Autosave
#TODO: Log more info
#TODO: Log to string etc
#TODO: Integrate with logger

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