#!/usr/bin/env python

import sys
from colorama import Fore, Style
from pylogfile import *

def show_help():
	print(f"{Fore.RED}Requires name of file to analyze.{Style.RESET_ALL}")

def main():
	
	# Print help if no arguments provided
	if len(sys.argv) == 1:
		show_help()
		sys.exit()
	
	# Create logpile object
	log = LogPile()
	
	# Create format object
	fmt = LogFormat()
	fmt.show_detail = True
	
	# Get filename from arguments
	filename = sys.argv[1]
	
	# Read file
	if filename[-4:].upper() == ".HDF":
		if not log.load_hdf(filename):
			print("\tFailed to read HDF")
	elif filename[-5:].upper() == ".JSON":
		if not log.load_hdf(filename):
			print("\tFailed to read JSON file.")
	
	log.show_logs()