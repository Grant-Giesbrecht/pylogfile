#!/usr/bin/env python

import os
import sys
from colorama import Fore, Style
from pylogfile import *
import argparse
from itertools import groupby, count, filterfalse

#TODO: Reintroduce argparse
#TODO: Replace first, last, all with SHOW and --first, --last, 
#TODO: Search by keyword
#TODO: Search by timestamp
#TODO: Search by index
#TODO: Option to print index of log with SHOW (to make sorting easier)

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
	
	min_level = DEBUG
	max_level = CRITICAL
	head_len = 15
	
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
		log.show_logs(max_number=head_len, from_beginning=True, min_level=min_level, max_level=max_level)
	elif args.last:
		log.show_logs(max_number=head_len, min_level=min_level, max_level=max_level)
	
	# Run CLI
	running = not args.nocli
	while running:
		
		cmd_raw = input(f"{Fore.GREEN}LUMBERJACK > {Style.RESET_ALL}")
		
		words = parseIdx(cmd_raw, " \t")
		
		if len(words) < 1:
			continue
		cmd = words[0].str.upper()
		
		cmd_code = ensureWhitespace(cmd_raw, "[],")
		words_code = parseIdx(cmd_code, " \t")
		
		
		
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
		elif cmd == "ALL":
			log.show_logs(min_level=min_level, max_level=max_level)
		elif cmd == "FIRST":
			head_len_local = head_len
			if len(words) > 2 and (words[1].str == "-n" or words[1].str == "--num"):
				try:
					head_len_local = int(words[2].str)
				except:
					w2 = words[2]
					print(f"{Fore.LIGHTRED_EX}Failed to interpret number provided, '{w2}'.{Style.RESET_ALL}")
			
			log.show_logs(max_number=head_len_local, from_beginning=True, min_level=min_level, max_level=max_level)
		elif cmd == "LAST":
			head_len_local = head_len
			if len(words) > 2 and (words[1].str == "-n" or words[1].str == "--num"):
				try:
					head_len_local = int(words[2].str)
				except:
					w2 = words[2]
					print(f"{Fore.LIGHTRED_EX}Failed to interpret number provided, '{w2}'.{Style.RESET_ALL}")
			
			log.show_logs(max_number=head_len_local, from_beginning=False, min_level=min_level, max_level=max_level)
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
		elif cmd == "STATE":
			print(f"{Fore.CYAN}Lumberjack-CLI State:{Style.RESET_ALL}")
			print(f"    {Fore.YELLOW}MIN-LEVEL: {Style.RESET_ALL}{min_level}")
			print(f"    {Fore.YELLOW}MAX-LEVEL: {Style.RESET_ALL}{max_level}")
			print(f"    {Fore.YELLOW}NUM-PRINT: {Style.RESET_ALL}{head_len}")
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
		