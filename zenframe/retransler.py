import threading
import os
import sys
import io
import zenframe
import signal
import psutil

from zenframe.util import print_to_stderr
from threading import Timer
import threading


class ConsoleRetransler(threading.Thread):
	def __init__(self, stdout, new_desc=None):
		super().__init__()

		self.do_retrans(old_file=stdout, new_desc=new_desc)
		self.stop_token = False

	def run(self):
		try:
			self.pid = os.getpid()
			self.readFile = self.r_file
		except Exception as ex:
			sys.stderr.write("console_retransler::rdopen error: ", ex, self.ipipe)
			sys.stderr.write("\r\n")
			sys.stderr.flush()
			exit(0)
		
		while(True):
			if self.stop_token:
				if zenframe.configure.CONFIGURE_DEBUG_MODE:
					print_to_stderr("finish console retransler... ok")
				return
			try:
				inputdata = self.readFile.readline()
			except:
				if zenframe.configure.CONFIGURE_DEBUG_MODE:
					print_to_stderr("finish console retransler... except")
				return
			
			self.communicator.send({"cmd":"console","data":inputdata})

	def finish(self):
		if zenframe.configure.CONFIGURE_DEBUG_MODE:
			print_to_stderr("finish console retransler... started")
			
		self.stop_token = True

	def do_retrans(self, old_file, new_desc=None):
		if zenframe.configure.CONFIGURE_DEBUG_MODE:
			print_to_stderr("do_retrans old:{} new:{}".format(old_file, new_desc))

		old_desc = old_file.fileno()
		if new_desc:
			os.dup2(old_desc, new_desc)
		else:
			new_desc = os.dup(old_desc)
		
		r, w = os.pipe()
		self.r_file = os.fdopen(r, "r")
		self.w_file = os.fdopen(w, "w")
		self.old_desc = old_desc
		self.new_desc = new_desc
		self.new_file = os.fdopen(new_desc, "w")
		old_file.close()
		os.close(old_desc)
		os.dup2(w, old_desc)

		sys.stdout = io.TextIOWrapper(os.fdopen(old_desc, "wb"), line_buffering=True)
