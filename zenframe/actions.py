import os

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import zenframe.util

class MainWindowActionsMixin:
	def init_menubar(self):
		self.view_mode = False
		self.hide_bars_mode = False
		self.full_screen_mode = False

		self.createActions()
		self.createMenus()

	def create_action(self, text, action, tip, shortcut=None, checkbox=False, defcheck=False):
		act = QAction(self.tr(text), self)
		act.setStatusTip(self.tr(tip))

		if shortcut is not None:
			act.setShortcut(self.tr(shortcut))

		if not checkbox:
			act.triggered.connect(action)
		else:
			act.setCheckable(True)
			act.toggled.connect(action)
			act.setChecked(defcheck)

		return act

	def createActions(self):
		self.mExitAction = self.create_action("Exit", self.close, "Exit", "Ctrl+Q")
		self.mHideConsole = self.create_action("Hide console", self.hide_console, "Hide console", checkbox=True)
		self.mHideEditor = self.create_action("Hide editor", self.hide_editor, "Hide editor", checkbox=True)
		self.mFullScreen = self.create_action("Full screen", self.full_screen, "Full screen", "F11")
		self.mDisplayMode = self.create_action("Display mode", self.display_mode, "Display mode", "F10")
		self.mHideBars = self.create_action("Hide Bars", self.hide_bars, "Hide bars", "F9")
		self.mAutoUpdate = self.create_action("Restart on update", self.auto_update, "Restart on update", checkbox=True, defcheck=True)
		self.mOpenAction = self.create_action("Open...", self.open_action, "Open", "Ctrl+O")

	def hide_console(self, en):
		self.console.setHidden(en)

	def hide_editor(self, en):
		self.texteditor.setEnabled(not en)
		self.texteditor.setHidden(en)

		#self.client_communicator.send({"cmd":"keyboard_retranslate", "en": not en})

	def hide_bars(self):
		if not self.hide_bars_mode:	
			self.menu_bar_height = self.menuBar().height()
			self.menuBar().setFixedHeight(0)
			#self.info_widget.setHidden(True)
			self.hide_bars_mode = True
		else:
			self.menuBar().setFixedHeight(self.menu_bar_height)
			#self.info_widget.setHidden(False)
			self.hide_bars_mode = False

	def display_mode_enable(self, en):
		if not en:
			self.hide_editor(False)
			self.hide_console(False)
			self.mHideConsole.setChecked(False)
			self.mHideEditor.setChecked(False)			

		else:
			self.hide_editor(True)
			self.hide_console(True)
			self.mHideConsole.setChecked(True)
			self.mHideEditor.setChecked(True)

	def display_mode(self):
		self.display_mode_enable(not (self.texteditor.isHidden() or self.console.isHidden()))		

	def full_screen(self):
		if not self.full_screen_mode:
			self.showFullScreen()
			self.full_screen_mode = True
		else:
			self.showNormal()
			self.full_screen_mode = False

	def auto_update(self, en):
		if not en:
			pass
		#	self.notifier.stop()
		#	self.notifier = None
		else:
			pass
		#	self.notifier = InotifyThread(self)
		#	if self.current_opened:
		#		self.notifier.retarget(self.current_opened)
		#		self.notifier.changed.connect(self.reopen_current)
		#		self.notifier.start()	

	def open_action(self):
		current_file = self.current_opened()

		if current_file == "" or current_file == None:
			current_directory = None
		else:
			current_directory = os.path.dirname(current_file)


		path = zenframe.util.open_file_dialog(self, directory=current_directory)

		if path[0] == "":
			return

		self._open_routine(path[0])
		

	def createMenus(self):
		self.mFileMenu = self.menuBar().addMenu(self.tr("&File"))
		self.mFileMenu.addAction(self.mOpenAction)
		self.mFileMenu.addAction(self.mExitAction)

		self.mViewMenu = self.menuBar().addMenu(self.tr("&View"))
		self.mViewMenu.addAction(self.mFullScreen)
		self.mViewMenu.addAction(self.mDisplayMode)
		self.mViewMenu.addAction(self.mHideBars)
		self.mViewMenu.addAction(self.mHideEditor)
		self.mViewMenu.addAction(self.mHideConsole)
