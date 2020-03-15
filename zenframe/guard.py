import sys
import subprocess

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from zenframe.communicator import Communicator
from zenframe.retransler import ConsoleRetransler
import zenframe.signal_handling

from zenframe.util import print_to_stderr

INTERPRETER = sys.executable

class ZenFrameGuard(QObject):
	def __init__(self, starter_mode, sleeped_mode=False):
		super().__init__()
		self.starter_mode = starter_mode
		zenframe.signal_handling.setup_qt_interrupt_handling()
		if starter_mode:
			pass
		else:
			self.init_slave_mode(sleeped_mode=sleeped_mode)

	def init_slave_mode(self, sleeped_mode):
		self.init_console_retransler()

		if sleeped_mode:
			self.wait_unsleep()

		self.main_communicator = Communicator(
			ifile=sys.stdin, ofile=self.console_retransler.new_file)

	def init_console_retransler(self):
		self.console_retransler = ConsoleRetransler(sys.stdout)
		self.console_retransler.start()

	def wait_unsleep(self):
		readFile = os.fdopen(zenframe.gui.application.STDIN_FILENO)
		
		while 1:
			rawdata = readFile.readline()
			try:
				data = pickle.loads(base64.b64decode(bytes(rawdata, "utf-8")))
			
			except:
				print_to_stderr("Unpickle error", rawdata)
				sys.exit(0)			
		
			if "cmd" in data and data["cmd"] == "stopworld":
				sys.exit(0)
				return

	def start_zenframe_sandbox_subprocess(self, command):
		"""Запустить графическую оболочку в новом процессе."""

		#debugstr = "--debug" if zenframe.configure.DEBUG_MODE else "" 
		#debugcomm = "--debugcomm" if zenframe.configure.CONFIGURE_PRINT_COMMUNICATION_DUMP else ""
		#no_sleeped = "" if zenframe.configure.CONFIGURE_SLEEPED_OPTIMIZATION else "--no-sleeped"
	#	no_evalcache_notify = "--no-evalcache-notify" if zenframe.configure.CONFIGURE_WITHOUT_EVALCACHE_NOTIFIES else ""
		#interpreter = INTERPRETER
		cmdlst = [INTERPRETER,  '-m', 'zenframe', "--sandbox"]
		cmdlst.append("--")
		cmdlst.extend(command)
	
		print_to_stderr(cmdlst)
		subproc = subprocess.Popen(cmdlst, stdout=subprocess.PIPE, stdin=subprocess.PIPE, 
			close_fds=True)
		return subproc

	def start_zenframe_agent_subprocess(self, tgtargs):
		cmdlst = [INTERPRETER, '-m', 'zenframe', '--agent']
		
		if slepped: 
			cmdlst.append("--sleeped")

		cmdlst.append("--")
		cmdlst.extend(tgtargs)

		print_to_stderr(cmdlst)
		subproc = subprocess.Popen(cmdlst, stdout=subprocess.PIPE, stdin=subprocess.PIPE, 
			close_fds=True)

		return subproc