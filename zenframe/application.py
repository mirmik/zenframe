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
from zenframe.sandbox import ZenFrameSandbox 
from zenframe.communicator import Communicator
from zenframe.retransler import ConsoleRetransler
from zenframe.util import print_to_stderr

INTERPRETER = sys.executable
CONSOLE_RETRANS_THREAD = None
MAIN_COMMUNICATOR = None
IS_STARTER = False

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



def start_agent_subprocess(path, sleeped=False, session_id=0, size=None):
	"""Создать новый поток и отправить запрос на добавление
	его вместо предыдущего ??? """
	
	sleeped = "--sleeped" if sleeped else ""
	debug_mode = "--debug" if zenframe.configure.CONFIGURE_DEBUG_MODE else ""
	sizestr = "--size {},{}".format(size.width(), size.height()) if size is not None else ""
	interpreter = INTERPRETER

	cmd = f'{interpreter} -m zenframe --agent {debug_mode} {sleeped} --session_id {session_id} -- "{path}"'

	print_to_stderr("CMD", cmd)
	
	try:
		subproc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE, 
			close_fds=True)
		return subproc
	except OSError as ex:
		print("Warn: subprocess.Popen finished with exception", ex)
		raise ex

def start_unbounded_agent(path, session_id, sleeped=False, size=None):
	"""Запустить процесс, обсчитывающий файл path и 
	вернуть его коммуникатор."""

	subproc = start_agent_subprocess(path, sleeped, session_id, size=size)

	stdout = io.TextIOWrapper(subproc.stdout, line_buffering=True)
	stdin = io.TextIOWrapper(subproc.stdin, line_buffering=True)

	communicator = zenframe.communicator.Communicator(
		ifile=stdout, ofile=stdin)
	communicator.subproc = subproc

	return communicator





if __name__ == "__main__":
	start_zenframe_sandbox()