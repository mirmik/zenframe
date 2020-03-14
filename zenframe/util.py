from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import tempfile
import sys
import os

PROCNAME = str(os.getpid())

def print_to_stderr(*args):
    sys.stderr.write("STDERR {}: ".format(PROCNAME))
    sys.stderr.write(str(args))
    sys.stderr.write("\r\n")
    sys.stderr.flush()

def create_temporary_file(zenframe_template=False):
	path = tempfile.mktemp(".py")
	
	if zenframe_template:
		f = open(path, "w")
		f.write(
			"#!/usr/bin/env python3\n#coding: utf-8\n\n"
		)
		f.close()

	return path

def open_file_dialog(parent, directory=None):
	filters = "*.py;;*.*"
	defaultFilter = "*.py"

	if directory == tempfile.gettempdir() or None:
		directory = "." 

	path = QFileDialog.getOpenFileName(
		parent, "Open File", directory, filters, defaultFilter
	)

	return path

def save_file_dialog(parent):
	filters = "*.py;;*.*"
	defaultFilter = "*.py"

	path = QFileDialog.getSaveFileName(
		parent, "Save File", "", filters, defaultFilter
	)

	return path

#def open_online_manual():
#	QDesktopServices.openUrl(
#		QUrl("https://mirmik.github.io/zenframe", QUrl.TolerantMode)
#	)

def set_process_name(name):
	pass