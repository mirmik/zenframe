from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import os
import io
import sys

from zenframe.guard import ZenFrameGuard
import zenframe.util


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

		subproc = self.start_zenframe_sandbox_subprocess(command)

		stdout = io.TextIOWrapper(subproc.stdout, line_buffering=True)
		stdin = io.TextIOWrapper(subproc.stdin, line_buffering=True)

		self.main_communicator = zenframe.communicator.Communicator(
			ifile=stdout, ofile=stdin)

		self.main_communicator.subproc = subproc

	def bind_widget(self, wdg):
		pass

	def bind_window(self, winid):
		self.main_communicator.send({
			"cmd":"bindwin", 
			"id":int(winid), 
			"pid":os.getpid(), 
			"session_id":0
		})
		pass

instance = None
def get_agent(starter_mode=True):
	global instance

	command = sys.argv

	if instance is None:
		instance = ZenFrameAgent(starter_mode=starter_mode, command=command)
	
	return instance

def start_agent(starter_mode, sleeped_mode, command):
	agent = get_agent()