#!/usr/bin/env python

import os
import sys
from colorama import Fore, Style
from pylogfile import *
import argparse
from itertools import groupby, count, filterfalse

try:
	
	# Requires Python >= 3.9
	import importlib.resources
	
	mod_path = importlib.resources.files(__package__)
	inp_file = (mod_path / 'assets' / 'lumberjack_help.json')
	with inp_file.open("r") as f:  # or "rt" as text file with universal newlines
		file_contents = f.read()
	
	help_data = json.loads(file_contents)
except AttributeError:
	help_data = {}
	print(f"{Fore.LIGHTRED_EX}Upgrade to Python >= 3.9 for access to importlib and CLI help data.")


def barstr(text:str, width:int=80, bc:str='*', pad:bool=True):

		s = text

		# Pad input if requested
		if pad:
			s = " " + s + " "

		pad_back = False
		while len(s) < width:
			if pad_back:
				s = s + bc
			else:
				s = bc + s
			pad_back = not pad_back

		return s

#TODO: Way to print detail
#TODO: Make it so you can apply search strings to only details or only message or both
#TODO: Modify keyword search to preserve strings so phrass can be searched
#TODO: Search by keyword
#TODO: Search by timestamp
#TODO: Search by index
#TODO: Automatically sort help --list keys (port to * as well)
#TODO: Options to turn On/Off: Elipses between incongruous logs, log index #s, color-print, option to pad index number so always same number of digits

##================================================================
# Read commandline Arguments

parser = argparse.ArgumentParser()
parser.add_argument('filename')
parser.add_argument('--last', help="Show last X number of logs", action='store_true')
parser.add_argument('--first', help="Show first X number of logs", action='store_true')
parser.add_argument('-g', '--gui', help="Use graphical interface", action='store_true')
parser.add_argument('-a', '--all', help="Print all logs", action='store_true')
parser.add_argument('-nc', '--nocli', help="Skip the CLI", action='store_true')
args = parser.parse_args()

if args.gui:
	print(f"{Fore.RED}GUI has not been implemented. Continuing with CLI.{Style.RESET_ALL}")

##================================================================


class LJSettings:
	
	def __init__(self, s=None):
		self.from_beginning:bool = True
		self.num_print:int = 15
		self.min_level = DEBUG
		self.max_level = CRITICAL
		
		if s is not None:
			self.get_vals(s)
	
	def get_vals(self, s):
		self.from_beginning = s.from_beginning
		self.num_print = s.num_print
		self.min_level = s.min_level
		self.max_level = s.max_level
	

class StringIdx():
	def __init__(self, val:str, idx:int, idx_end:int=-1):
		self.str = val
		self.idx = idx
		self.idx_end = idx_end;

	def __str__(self):
		return f"[{self.idx}]\"{self.str}\""

	def __repr__(self):
		return self.__str__()

# Looks for characters in 'delims' in string 'input'. Supposing the string is to
# be broken up at each character in 'delims', the function returns a generator
# with the start and end+1 indecies of each section.
#
def parseTwoIdx(input:str, delims:str):
	p = 0
	for k, g in groupby(input, lambda x:x in delims):
		q = p + sum(1 for i in g)
		if not k:
			yield (p, q) # or p, q-1 if you are really sure you want that
		p = q

def parseIdx(input:str, delims:str=" ", keep_delims:str=""):
	""" Parses a string, breaking it up into an array of words. Separates at delims. """
	
	out = []
	
	sections = list(parseTwoIdx(input, delims))
	for s in sections:
		out.append(StringIdx(input[s[0]:s[1]], s[0], s[1]))
	return out

def ensureWhitespace(s:str, targets:str, whitespace_list:str=" \t", pad_char=" "):
	""" """
	
	# Remove duplicate targets
	targets = "".join(set(targets))
	
	# Add whitespace around each target
	for tc in targets:
		
		start_index = 0
		
		# Find all instances of target
		while True:
			
			# Find next instance of target
			try:
				idx = s[start_index:].index(tc)
				idx += start_index
			except ValueError as e:
				break # Break when no more instances
			
			# Update start index
			start_index = idx + 1
			
			# Check if need to pad before target
			add0 = True
			if idx == 0:
				add0 = False
			elif s[idx-1] in whitespace_list:
				add0 = False
			
			# Check if need to pad after target
			addf = True
			if idx >= len(s)-1:
				addf = False
			elif s[idx+1] in whitespace_list:
				addf = False
			
			# Add required pad characters
			if addf:
				s = s[:idx+1] + pad_char + s[idx+1:]
				start_index += 1 # Don't scan pad characters
			if add0:
				s = s[:idx] + pad_char + s[idx:]
	return s

def show_help():
	print(f"{Fore.RED}Requires name of file to analyze.{Style.RESET_ALL}")

def main():
	
	settings = LJSettings()
	
	# Create logpile object
	log = LogPile()
	
	# Create format object
	fmt = LogFormat()
	fmt.show_detail = True
	
	# Get filename from arguments
	filename = args.filename
	
	# Read file
	if filename[-4:].upper() == ".HDF":
		if not log.load_hdf(filename):
			print("\tFailed to read HDF")
	elif filename[-5:].upper() == ".JSON":
		if not log.load_hdf(filename):
			print("\tFailed to read JSON file.")
	
	# Show all logs if requested
	if args.all:
		log.show_logs()
	elif args.first:
		log.show_logs(max_number=settings.num_print, from_beginning=True, min_level=settings.min_level, max_level=settings.max_level)
	elif args.last:
		log.show_logs(max_number=settings.num_print, min_level=settings.min_level, max_level=settings.max_level)
	
	# Run CLI
	running = not args.nocli
	while running:
		
		# Get user input
		cmd_raw = input(f"{Fore.GREEN}LUMBERJACK > {Style.RESET_ALL}")
		
		# Break into words
		words = parseIdx(cmd_raw, " \t")
		
		# Skip empty lines
		if len(words) < 1:
			continue
		
		# Get command string
		cmd = words[0].str.upper()
		
		# Process commands
		if cmd == "EXIT":
			running = False
		elif cmd == "CLS" or cmd == "CLEAR":
			if os.name == 'nt':
				os.system("cls")
			else:
				os.system("clear")
		elif cmd == "MIN-LEVEL":
			
			# Check number of arguments
			if len(words) < 2:
				print(f"{Fore.LIGHTRED_EX}MIN-LEVEL requires a level to be specified.{Style.RESET_ALL}")
				continue
			
			# Get level int
			lvl_str = words[1].str.upper()
			lvl_int = str_to_level(lvl_str)
			if lvl_int is None:
				print(f"{Fore.LIGHTRED_EX}Unrecognized level spcifier '{lvl_str}'.{Style.RESET_ALL}")
				continue
			
			# Assign min level
			min_level = lvl_int
		elif cmd == "MAX-LEVEL":
			
			# Check number of arguments
			if len(words) < 2:
				print(f"{Fore.LIGHTRED_EX}MAX-LEVEL requires a level to be specified.{Style.RESET_ALL}")
				continue
			
			# Get level int
			lvl_str = words[1].upper()
			lvl_int = str_to_level(lvl_str)
			if lvl_int is None:
				print(f"{Fore.LIGHTRED_EX}Unrecognized level spcifier '{lvl_str}'.{Style.RESET_ALL}")
				continue
			
			# Assign min level
			max_level = lvl_int
		elif cmd == "SHOW":
			
			# Initialize local copies of show parameters, for local overrides
			local_settings = LJSettings(settings)
			show_all = False
			search_orders = SortConditions()
			do_search = False
			
			# Check for flags
			idx = 1
			while idx < len(words):
				if words[idx].str == "-n" or words[idx].str == "--num":
					
					# Verify argument is present
					if idx+1 >= len(words):
						print(f"{Fore.LIGHTRED_EX}Flag '--num' requires an argument (the number of logs to display).")
						break
					
					# Try to interpret argument
					try:
						local_settings.num_print = int(words[idx+1].str)
					except:
						w2 = words[idx+1]
						print(f"{Fore.LIGHTRED_EX}Failed to interpret number provided, '{w2}'.{Style.RESET_ALL}")
						idx += 1
						continue
					idx += 1
					
					# Check if num_print is zero (inf), and reassign to None
					if local_settings.num_print == 0:
						local_settings.num_print = None
					
				elif words[idx].str == "-a" or words[idx].str == "--all":
					show_all = True
				elif words[idx].str == "-f" or words[idx].str == "--first":
					local_settings.from_beginning = True
				elif words[idx].str == "-l" or words[idx].str == "--last":
					local_settings.from_beginning = False
				elif words[idx].str == "-m" or words[idx].str == "--min":
					
					# Verify argument is present
					if idx+1 >= len(words):
						print(f"{Fore.LIGHTRED_EX}Flag '--min' requires an argument (the minimum log level to display).")
						break
					
					# Get level int
					lvl_str = words[idx+1].str.upper()
					lvl_int = str_to_level(lvl_str)
					if lvl_int is None:
						print(f"{Fore.LIGHTRED_EX}Unrecognized level spcifier '{lvl_str}'.{Style.RESET_ALL}")
						idx += 1
						continue
					idx += 1
					
					# Assign value
					local_settings.min_level = lvl_int
					
				elif words[idx].str == "-x" or words[idx].str == "--max":
					
					# Verify argument is present
					if idx+1 >= len(words):
						print(f"{Fore.LIGHTRED_EX}Flag '--max' requires an argument (the maximum log level to display).")
						break
					
					# Get level int
					lvl_str = words[idx+1].str.upper()
					lvl_int = str_to_level(lvl_str)
					if lvl_int is None:
						print(f"{Fore.LIGHTRED_EX}Unrecognized level spcifier '{lvl_str}'.{Style.RESET_ALL}")
						idx += 1
						continue
					idx += 1
					
					# Assign value
					local_settings.max_level = lvl_int
					
				elif words[idx].str == "-c" or words[idx].str == "--contains":
					
					# Verify argument is present
					if idx+1 >= len(words):
						print(f"{Fore.LIGHTRED_EX}Flag '--contains' requires an argument (the string to search for).")
						break
					
					# Get level int
					search_orders.contains_or.append(words[idx+1].str)
					idx += 1
					do_search = True
				
				elif words[idx].str == "-cc" or words[idx].str == "--andcontains":
					
					# Verify argument is present
					if idx+1 >= len(words):
						print(f"{Fore.LIGHTRED_EX}Flag '--contains' requires an argument (the string to search for).")
						break
					
					# Get level int
					search_orders.contains_and.append(words[idx+1].str)
					idx += 1
					do_search = True
				
				idx += 1
			
			# If no searches were previded, set object to None
			if not do_search:
				search_orders = None
			
			# Show logs using local settings
			if show_all:
				log.show_logs(from_beginning=True)
			else:
				log.show_logs(max_number=local_settings.num_print, from_beginning=local_settings.from_beginning, min_level=local_settings.min_level, max_level=local_settings.max_level, sort_orders=search_orders)
				
		elif cmd == "NUM-PRINT":
			
			# Check number of arguments
			if len(words) < 2:
				print(f"{Fore.LIGHTRED_EX}NUM-PRINT requires a second argument (number of logs to print).{Style.RESET_ALL}")
				continue
			
			# interpret argument
			try:
				head_len = int(words[1].str)
			except Exception as e:
				w2 = words[1]
				print(f"{Fore.LIGHTRED_EX}Failed to interpret number provided, '{w2}' ({e}).{Style.RESET_ALL}")
		elif cmd == "HELP":
			
			HELP_WIDTH = 80
			TABC = "    "
			
			color1 = Fore.WHITE # Body text
			color2 = Fore.LIGHTYELLOW_EX # Titles/headers
			color3 = Fore.YELLOW # Type specifiers, etc
			color4 = Fore.LIGHTBLACK_EX # brackets and accents
			
			hstr = ""
			
			list_commands = False
			
			# Check for flags
			print_long = False
			if len(words) > 1:
				for tk in words:
					if tk.str == "-l" or tk.str == "--list":
						list_commands = True

			
			if list_commands:
				
				# title
				hstr += color2 + "-"*HELP_WIDTH + Style.RESET_ALL + "\n"
				hstr += color2 + barstr(f"ALL COMMANDS", HELP_WIDTH, "-", pad=True) + Style.RESET_ALL + "\n\n"
				
				for cmd in help_data.keys():
					desc = help_data[cmd]['description']
					hstr += f"{TABC}{Fore.CYAN}{cmd}{color1}: {desc}\n"
				
				print(hstr)
				continue
			
			# Check for number of arguments
			if len(words) < 2:
				hcmd = "HELP"
			else:
				hcmd = words[1].str.upper()
			
			cmd_list = help_data.keys()
			
			if hcmd in cmd_list: # HCMD is a COMMAND name
			
				## Print help data:
				try:
					# title
					hstr += color2 + "-"*HELP_WIDTH + Style.RESET_ALL + "\n"
					hstr += color2 + barstr(f"{hcmd} Help", HELP_WIDTH, "-", pad=True) + Style.RESET_ALL + "\n\n"
					
					# Description
					hstr += f"{color2}Description:\n"
					hstr += f"{color1}{TABC}" + help_data[hcmd]['description']+Style.RESET_ALL + "\n"
					
					# Arguments
					if len(help_data[hcmd]['arguments']) > 0:
						hstr += f"{color2}\nArguments:\n"
						for ar in help_data[hcmd]['arguments']:
							
							arg_name = ar['name']
							if ar['type'] in ["num", "str", "list", "cell", "list[cell]"]:
								type_name = ar['type']
							else:
								type_name = f"{Fore.RED}???"
							
							if ar['optional']:
								hstr += TABC + f"{color4}( {color1}{arg_name} {color4}[{color3}{type_name}{color4}]) "
							else:
								hstr += TABC + f"{color4}< {color1}{arg_name} {color4}[{color3}{type_name}{color4}]> "
							
							hstr += color1 + ar['description'] + "\n"
					
					# Flags
					if len(help_data[hcmd]['flags']) > 0:
						hstr += f"{color2}\nFlags:\n"
						for ar in help_data[hcmd]['flags']:
							
							if ar["short"] != "" and ar["long"] != "":
								hstr += TABC + color1 + ar['short'] + f"{color4}," + color1 + ar["long"] + color4 + ": "
							elif ar['short'] != "":
								hstr += TABC + color1 + ar['short'] + color4 + ": "
							else:
								hstr += TABC + color1 + ar['long'] + color4 + ": "
								
							
							hstr += color1 + ar['description'] + "\n"
					
					# Examples
					if len(help_data[hcmd]['examples']) > 0:
						hstr += f"{color2}\nExamples:\n"
						for ex_no, ar in enumerate(help_data[hcmd]['examples']):
							
							hstr += f"{color1}{TABC}Ex {ex_no}:\n"
							hstr += TABC + TABC + color4 + ">> " + color3 + ar['command'] + "\n"
							hstr += TABC + TABC + color1 + "Desc: " + color1 + ar['description'] + "\n"
						
						hstr += "\n"
					
					
					# See also
					if len(help_data[hcmd]['see_also']) > 0:
						hstr += f"{color2}\nSee Also:\n{TABC}{color1}"
						add_comma = False
						for ar in help_data[hcmd]['see_also']:
							
							if ar.upper() in cmd_list:
								
								if add_comma:
									hstr += ", "
								
								hstr += ar
								add_comma = True
					
					print(hstr)
				except Exception as e:
					print(f"Corrupt help data for selected entry '{hcmd}' ({e}).")
			
		elif cmd == "STATE":
			print(f"{Fore.CYAN}Lumberjack-CLI State:{Style.RESET_ALL}")
			print(f"    {Fore.YELLOW}Min. level: {Style.RESET_ALL}{settings.min_level}")
			print(f"    {Fore.YELLOW}Max. level: {Style.RESET_ALL}{settings.max_level}")
			print(f"    {Fore.YELLOW}Num. print: {Style.RESET_ALL}{settings.num_print}")
			print(f"    {Fore.YELLOW}Print from beginning: {Style.RESET_ALL}{settings.from_beginning}")
		elif cmd == "INFO":
			
			long_mode = False 
			
			# Check for additional arguments
			if len(words) > 1:
				
				# Scan over words
				for c in words[1:]:
					if c.str.upper() == "-L" or c.str.upper() == "--LONG":
						long_mode = True
					else:
						print(f"Unrecognized option '{c.str.upper()}'. Ignoring it.")
			
			print(f"{Fore.CYAN}Log Info: {Fore.LIGHTBLACK_EX}{filename}{Style.RESET_ALL}")
			print(f"    {Fore.YELLOW}number of Logs: {Style.RESET_ALL}{len(log.logs)}")
			if long_mode:
				# Count logs at each level
				ndebug, ninfo, nwarning, nerror, ncritical, nother = 0, 0, 0, 0, 0, 0
				for l in log.logs:
					if l.level == DEBUG:
						ndebug += 1
					elif l.level == INFO:
						ninfo += 1
					elif l.level == WARNING:
						nwarning += 1
					elif l.level == ERROR:
						nerror += 1
					elif l.level == CRITICAL:
						ncritical += 1
					else:
						nother += 1
				print(f"        {Fore.LIGHTBLACK_EX}Number of DEBUG: {Style.RESET_ALL}{ndebug}")
				print(f"        {Fore.LIGHTBLACK_EX}Number of INFO: {Style.RESET_ALL}{ninfo}")
				print(f"        {Fore.LIGHTBLACK_EX}Number of WARNING: {Style.RESET_ALL}{nwarning}")
				print(f"        {Fore.LIGHTBLACK_EX}Number of ERROR: {Style.RESET_ALL}{nerror}")
				print(f"        {Fore.LIGHTBLACK_EX}Number of CRITICAL: {Style.RESET_ALL}{ncritical}")
				print(f"        {Fore.LIGHTBLACK_EX}Number of other: {Style.RESET_ALL}{nother}")
			t_elapsed = log.logs[-1].timestamp - log.logs[0].timestamp
			print(f"    {Fore.YELLOW}Timespan: {Style.RESET_ALL}{t_elapsed}")
			if long_mode:
				ts_0 = log.logs[0].timestamp
				ts_1 = log.logs[-1].timestamp
				print(f"        {Fore.LIGHTBLACK_EX}First timestamp: {Style.RESET_ALL}{ts_0}")
				print(f"        {Fore.LIGHTBLACK_EX}Last timestamp: {Style.RESET_ALL}{ts_1}")
			# print(f"    {Fore.YELLOW}MAX-LEVEL: {Style.RESET_ALL}{max_level}")
			# print(f"    {Fore.YELLOW}NUM-PRINT: {Style.RESET_ALL}{head_len}")
		else:
			print(f"{Fore.LIGHTRED_EX}Unrecognized command '{cmd}'.{Style.RESET_ALL}")
		