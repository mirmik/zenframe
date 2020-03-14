# coding: utf-8

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtTest import *

from zenframe.actions import MainWindowActionsMixin
from zenframe.console import ConsoleWidget
from zenframe.texteditor import TextEditor

class MainWindow(QMainWindow, MainWindowActionsMixin):
	def __init__(self, 
			client_communicator=None, 
			openned_path=None, 
			fastopen=None,
			title = "ZenFrame"):
		super().__init__()

		self.init_menubar()

		self.setWindowTitle(title)
		self.console = ConsoleWidget()
		self.texteditor = TextEditor(self)
		self.texteditor.open_start_signal.connect(self.setWindowTitle)

		self.central_widget = QWidget()
		self.central_widget_layout = QVBoxLayout()
		self.hsplitter = QSplitter(Qt.Horizontal)
		self.vsplitter = QSplitter(Qt.Vertical)

		self.central_widget_layout.addWidget(self.hsplitter)
		self.central_widget.setLayout(self.central_widget_layout)

		self.screen_saver = QWidget()

		self.hsplitter.addWidget(self.texteditor)
		self.hsplitter.addWidget(self.vsplitter)
		self.vsplitter.addWidget(self.screen_saver)
		self.vsplitter.addWidget(self.console)

		self.resize(640,480)
		self.vsplitter.setSizes([self.height()*5/8, self.height()*3/8])
		self.hsplitter.setSizes([self.width()*3/8, self.width()*5/8])

		self.central_widget_layout.setContentsMargins(0,0,0,0)
		self.central_widget_layout.setSpacing(0)

		self.setCentralWidget(self.central_widget)

	def current_opened(self):
		return self.texteditor.edited

	def _open_routine(self, path):
		self.texteditor.open(path)