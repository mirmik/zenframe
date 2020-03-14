#!/usr/bin/env python3

import sys
import signal
import time
import psutil

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import zenframe.signal_handling

from zenframe.mainwindow import MainWindow 
from zenframe.communicator import Communicator
from zenframe.retransler import ConsoleRetransler

CONSOLE_RETRANS_THREAD = None
MAIN_COMMUNICATOR = None

def start_zenframe_sandbox(tgtpath=None, console_retrans=False):
	"""Запустить графический интерфейс в текущем потоке.

	Используются файловые дескрипторы по умолчанию, которые длжен открыть
	вызывающий поток."""

	global CONSOLE_RETRANS_THREAD
	global MAIN_COMMUNICATOR

	def signal_sigchild(a,b):
		os.wait()

	if sys.platform == "linux":
		signal.signal(signal.SIGCHLD, signal_sigchild) 

	qapp = QApplication([])
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


if __name__ == "__main__":
	start_zenframe_sandbox()