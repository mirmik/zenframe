#!/usr/bin/env python3

import os
import sys
import signal
import io
import time
import subprocess
import psutil

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import zenframe.signal_handling

import zenframe.configure
from zenframe.mainwindow import MainWindow 
from zenframe.communicator import Communicator
from zenframe.retransler import ConsoleRetransler
from zenframe.util import print_to_stderr

INTERPRETER = sys.executable
CONSOLE_RETRANS_THREAD = None
MAIN_COMMUNICATOR = None
IS_STARTER = False

class XQApplication(QApplication):
	def __init__(self,args):
		super().__init__(args)


#	def event(self, ev):
#		print_to_stderr(ev)
#		return QApplication.event(self,ev)
#
#	def notify(self, obj, ev):
#		print_to_stderr(obj, ev)
#		return QApplication.notify(self,obj,ev)
class KeyPressEater(QObject):
	def __init__(self, wdg):
		super().__init__()
		self.wdg = wdg

	def eventFilter(self, obj, event):
		if isinstance(event, (QHoverEvent, QPaintEvent, QTimerEvent, QHideEvent, QCloseEvent, QMouseEvent, QChildEvent)):
			return False

		if event.type() in (52,):
			return False

		print_to_stderr(event, event.type())
		#if event.type() == 99 or event.type() == 11 or event.type() == 183 or event.type() == 77:
		#	return True
		#print_to_stderr(event, event.type())

		if event.type() in ():
			return True

		return False

def start_zenframe_sandbox(tgtpath=None, display_mode=False, console_retrans=False):
	"""Запустить графический интерфейс в текущем потоке.

	Используются файловые дескрипторы по умолчанию, которые длжен открыть
	вызывающий поток."""

	global CONSOLE_RETRANS_THREAD
	global MAIN_COMMUNICATOR

	def signal_sigchild(a,b):
		os.wait()

	if sys.platform == "linux":
		signal.signal(signal.SIGCHLD, signal_sigchild) 

	qapp = XQApplication([])
	f = KeyPressEater(qapp)
	qapp.installEventFilter(f)
	zenframe.signal_handling.setup_qt_interrupt_handling()
	#app.setWindowIcon(QIcon(os.path.dirname(__file__) + "/../industrial-robot.svg"))

	communicator_out_file = sys.stdout

	if console_retrans:
		CONSOLE_RETRANS_THREAD = ConsoleRetransler(sys.stdout)
		CONSOLE_RETRANS_THREAD.start()
		communicator_out_file = CONSOLE_RETRANS_THREAD.new_file

		MAIN_COMMUNICATOR = Communicator(
			ifile=sys.stdin, ofile=communicator_out_file)

	main_widget = MainWindow(
		client_communicator = MAIN_COMMUNICATOR,
		display_mode = display_mode,
		openned_path = tgtpath)

	main_widget.show()
	qapp.exec()

	if MAIN_COMMUNICATOR:
		MAIN_COMMUNICATOR.stop_listen()

	time.sleep(0.05)

	procs = psutil.Process().children()	
	for p in procs:
		try:
			p.terminate()
		except psutil.NoSuchProcess:
			pass




def start_zenframe_subprocess(tgtpath):
	"""Запустить графическую оболочку в новом процессе."""

	debugstr = "--debug" if zenframe.configure.DEBUG_MODE else "" 
	debugcomm = "--debugcomm" if zenframe.configure.CONFIGURE_PRINT_COMMUNICATION_DUMP else ""
	no_sleeped = "" if zenframe.configure.CONFIGURE_SLEEPED_OPTIMIZATION else "--no-sleeped"
#	no_evalcache_notify = "--no-evalcache-notify" if zenframe.configure.CONFIGURE_WITHOUT_EVALCACHE_NOTIFIES else ""
	interpreter = INTERPRETER
	cmd = f'{interpreter} -m zenframe {no_sleeped} --subproc --tgtpath {tgtpath}"'

	subproc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE, 
		close_fds=True)
	return subproc


def start_unbound_zenframe(*args, tgtpath, **kwargs):
	"""Основная процедура запуска.

	Создаёт в отдельном процессе графическую оболочку,
	После чего создаёт в своём процессе виджет, который встраивается в графическую оболочку.
	Для коммуникации между процессами создаётся pipe"""

	global MAIN_COMMUNICATOR
	global IS_STARTER

	IS_STARTER = True
	zenframe.util.PROCNAME = f"st({os.getpid()})"

	subproc = start_zenframe_subprocess(tgtpath)

	stdout = io.TextIOWrapper(subproc.stdout, line_buffering=True)
	stdin = io.TextIOWrapper(subproc.stdin, line_buffering=True)

	communicator = zenframe.communicator.Communicator(
		ifile=stdout, ofile=stdin)

	MAIN_COMMUNICATOR = communicator
	communicator.subproc = subproc

	#common_unbouded_proc(pipes=True, need_prescale=True, *args, **kwargs)
	return MAIN_COMMUNICATOR








if __name__ == "__main__":
	start_zenframe_sandbox()