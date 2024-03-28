import datetime
import json

#TODO: Save only certain log levels
#TODO: Autosave
#TODO: Log more info
#TODO: Log to string etc
#TODO: Integrate with logger

class Log:
	
	DEBUG = 10
	INFO = 20
	WARNING = 30
	ERROR = 40
	CRITICAL = 50
	
	def __init__(self, level:int, message:str):
		
		# Set timestamp
		self.timestamp = datetime.datetime.now()
		
		# Set level
		if level not in [Log.DEBUG, Log.INFO, Log.WARNING, Log.ERROR, Log.CRITICAL]:
			self.level = Log.INFO
		else:
			self.level = level
		
		# Set message
		self.message = message
	
	def get_level_str(self):
		
		if self.level == Log.DEBUG:
			return "DEBUG"
		elif self.level == Log.INFO:
			return "INFO"
		elif self.level == Log.WARNING:
			return "WARNING"
		elif self.level == Log.ERROR:
			return "ERROR"
		elif self.level == Log.CRITICAL:
			return "CRITICAL"
		else:
			return "??"
		
	
	def get_dict(self):
		return {"message":self.message, "timestamp":str(self.timestamp), "level":self.get_level_str()}
	
	def get_json(self):
		return json.dumps(self.get_dict())
		

class LogFile:
	
	def __init__(self, filename:str="", autosave:bool=False):
		
		self.filename = filename
		self.autosave = autosave
		self.autosave_period_s = 300
		
		self.logs = []
	
	def info(self, message:str):
		''' Logs data at INFO level. '''
		
		# Create new log object
		nl = Log(Log.INFO, message)
		
		# Add to list
		self.logs.append(nl)
	
	def error(self, message:str):
		''' Logs data at ERROR level. '''
		
		# Create new log object
		nl = Log(Log.ERROR, message)
		
		# Add to list
		self.logs.append(nl)
	
	def get_json(self):
		
		return [x.get_dict() for x in self.logs]
	
	def save(self, save_filename:str):
		''''''
		
		# Open file
		with open(save_filename, 'w') as fh:
			json.dump({"logs":self.get_json()}, fh)
			