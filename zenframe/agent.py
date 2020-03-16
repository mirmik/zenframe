from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import os
import io
import sys
import psutil
import threading

from zenframe.guard import ZenFrameGuard
import zenframe.util

from zenframe.util import print_to_stderr, trace

class ZenFrameAgent(ZenFrameGuard):
	"""
	Этот объект висит в памяти активного скрипта
	"""

	def __init__(self, starter_mode, command):
		super().__init__(starter_mode=starter_mode)
		if starter_mode:
			self.init_starter_mode(command)

	def init_starter_mode(self, command):
		zenframe.util.PROCNAME = f"st({os.getpid()})"
		self.console_retransler=None

		subproc = self.start_zenframe_sandbox_subprocess(command)

		stdout = io.TextIOWrapper(subproc.stdout, line_buffering=True)
		stdin = io.TextIOWrapper(subproc.stdin, line_buffering=True)

		self.main_communicator = zenframe.communicator.Communicator(
			ifile=stdout, ofile=stdin)

		self.main_communicator.subproc = subproc

		self.attach_stopworld_function()
		self.main_communicator.start_listen()

	def bind_widget(self, wdg):
		self.view_object = wdg

	def bind_window(self, winid):
		self.view_object = int(winid)
		self.main_communicator.send({
			"cmd":"bindwin", 
			"id":int(winid), 
			"pid":os.getpid(), 
			"session_id":0
		})
		
	def stop_visual_part(self):
		print_to_stderr("stop_visual_part")
		if isinstance(self.view_object, int):
			def on_terminate(proc):
				trace("process {} finished with exit code {}".format(proc, proc.returncode))
			procs = psutil.Process().children()
			print_to_stderr(procs)

			psutil.wait_procs(procs, callback=on_terminate)

			print_to_stderr("on_close")
			if self.on_close:
				self.on_close()

		elif isinstance(self.view_object, QObject):
			self.view_object.close()

			class final_waiter_thr(Thread):
				def run(self):
					print_to_stderr("run final_waiter_thr")
					procs = psutil.Process().children()
					trace(procs)
					psutil.wait_procs(procs, callback=on_terminate)
					app.quit()
			
			self.THREAD_FINALIZER = final_waiter_thr()
			self.THREAD_FINALIZER.start()
		else:
			print_to_stderr("unsupported", self.view_object)



instance = None
def make_agent(on_close=None, starter_mode=True):
	global instance

	command = sys.argv

	if instance is None:
		instance = ZenFrameAgent(starter_mode=starter_mode, command=command)

	instance.on_close=on_close
	
	return instance

def start_agent(starter_mode, sleeped_mode, command):
	agent = get_agent()