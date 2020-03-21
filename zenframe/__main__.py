#!/usr/bin/env python3
# coding:utf-8

import os
import sys
import time
import runpy

import pickle
import sys, traceback
import argparse
import subprocess
import threading
import multiprocessing
import base64
import psutil
import signal

import zenframe.configure
import zenframe.sandbox
import zenframe.agent
from zenframe.util import print_to_stderr

def split_on(lst):
	delim = None
	for i, l in enumerate(lst):
		if l == "--":
			delim = i

	if delim is None:
		raise Exception("delimiter -- not found")

	else:
		return lst[:delim], lst[delim+1:]

def parse_args(args):
	parser = argparse.ArgumentParser()
	parser.add_argument('-v', "--debug", action="store_true")
	parser.add_argument("--sleeped", action="store_true")
	parser.add_argument("--sandbox", action="store_true")
	parser.add_argument("--agent", action="store_true")
	parser.add_argument("--session_id")
	pargs = parser.parse_args(args)
	return pargs

def main():
	zenargs, tgtargs = split_on(sys.argv[1:]) 
	
	print_to_stderr(sys.argv)
	print_to_stderr(zenargs)
	print_to_stderr(tgtargs)
	pargs = parse_args(zenargs)

	if pargs.agent:
		print_to_stderr("start_agent")
		zenframe.agent.start_agent(
			starter_mode=False, 
			sleeped_mode=pargs.sleeped, 
			command=tgtargs,
			session_id=int(pargs.session_id))
	
	if pargs.sandbox:
		print_to_stderr("start sandbox")
		zenframe.sandbox.exec_sandbox(prestart_command=tgtargs)

	print("unresolved mode")

if __name__ == "__main__":
	main()
	
