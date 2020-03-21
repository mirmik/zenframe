import pickle
import time
import sys
import os
import signal
import threading
import psutil

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtTest import *
import PyQt5

import zenframe.configure
from zenframe.guard import ZenFrameGuard 

from zenframe.actions import MainWindowActionsMixin
from zenframe.console import ConsoleWidget
from zenframe.texteditor import TextEditor
from zenframe.inotifier import InotifyThread
from zenframe.screen_saver import ScreenSaverWidget

from zenframe.util import print_to_stderr

def trace(*args):
	if zenframe.configure.CONFIGURE_DEBUG_MODE:
		print_to_stderr("MAINWINDOW:", *args)

class ZenFrameSandbox(QMainWindow, MainWindowActionsMixin):
	message_handler_qtsignal = pyqtSignal(bytes, int)

	def __init__(self, 
			prestart_command=None, 
			display_mode=False,
			title = "ZenFrame"):
		QMainWindow.__init__(self)
		
		self.guard = ZenFrameGuard(starter_mode=False)
		self.main_communicator = self.guard.main_communicator
		self.client_communicator = self.main_communicator
		
		self.openlock = QMutex()
		self.session_id=0

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

		self.screen_saver = ScreenSaverWidget()

		self.hsplitter.addWidget(self.texteditor)
		self.hsplitter.addWidget(self.vsplitter)
		self.vsplitter.addWidget(self.screen_saver)
		self.vsplitter.addWidget(self.console)

		self.resize(640,480)
		self.vsplitter.setSizes([self.height()*5/8, self.height()*3/8])
		self.hsplitter.setSizes([self.width()*3/8, self.width()*5/8])

		if display_mode:
			self.display_mode_enable(True)

		print(prestart_command)
		script = prestart_command[0]
		self.texteditor.open(script)

		self.central_widget_layout.setContentsMargins(0,0,0,0)
		self.central_widget_layout.setSpacing(0)

		self.setCentralWidget(self.central_widget)
		
		self.client_finalization_list = []
		self.communicator_dictionary = {}

		self.init_communication()
		self.init_sleeped()
		self.init_inotifier()

	def init_sleeped(self):
		if zenframe.configure.CONFIGURE_SLEEPED_OPTIMIZATION:
			pass

	def init_communication(self):
		self.message_handler_qtsignal.connect(self.message_handler)
		self.main_communicator.newdata.connect(self.message_handler_qtwrap)
		self.main_communicator.start_listen()

	def init_inotifier(self):
		self.notifier = InotifyThread(self)
		self.notifier.changed.connect(self.inotifier_reopen_action)
		self.notifier.retarget(self.current_opened())

	def inotifier_reopen_action(self):
		self._open_routine(
			self.current_opened(), 
			update_texteditor=True)

	def current_opened(self):
		return self.texteditor.edited

	def bind_window(self, winid, pid, session_id):
		print_to_stderr("bind_window: winid:{}, pid:{}".format(winid,pid))

		if self.client_communicator.subproc_pid() != pid:
			"""Если заявленный pid отправителя не совпадает с pid текущего коммуникатора,
			то бинд уже неактуален."""
			print_to_stderr("Nonactual bind")
			return
		
		if not self.openlock.tryLock():
			print_to_stderr("openlock")
			return

		try:
			if session_id != self.session_id:
				print_to_stderr("session_id != self.session_id", session_id, self.session_id)
				self.openlock.unlock()

				return
		
			if self.is_window_binded_mode():
				print_to_stderr("try bind")
				#oldwindow = self.cc_window
				self.embeded_window = QWindow.fromWinId(winid)

				#oldcc = self.embeded_window_container
				self.embeded_window_container = QWidget.createWindowContainer(
					self.embeded_window)    

				#self.embeded_window_container.setFocusPolicy(Qt.NoFocus)
				#self.embeded_window_container.installEventFilter(self.evfilter)
				#self.cc_window = winid
				trace("replace widget")
				self.vsplitter.replaceWidget(0, self.embeded_window_container)

				#if oldwindow is not None:
				#	wind = QWindow.fromWinId(oldwindow)
				#	if wind is not None:
				#		wind.close()					

				self.update()
			
			self.client_pid = pid
			self.setWindowTitle(self.current_opened())
		
			#info("window bind success")
			self.open_in_progress = False

			self.synchronize_subprocess_state()

			time.sleep(0.1)
			self.update()
		except Exception as ex:
			self.openlock.unlock()
			print_to_stderr("exception on window bind", ex)
			raise ex

		self.subprocess_finalization_do()
		self.openlock.unlock()

	def message_handler(self, data, procpid):
		print_to_stderr("new_worker_message")
		data = pickle.loads(data)
		try:
			cmd = data["cmd"]
		except:
			print("Warn: new_worker_message: message without 'cmd' field")
			return

		if procpid != self.client_communicator.subproc_pid() and data["cmd"] != "finish_screen":
			trace("MAINWINDOW: message: procpid != self.client_communicator.subproc_pid", procpid, self.client_communicator.subproc_pid())
			return
		
		# TODO: Переделать в словарь
		if cmd == "hello": print("HelloWorld")
		elif cmd == 'bindwin': self.bind_window(winid=data['id'], pid=data["pid"], session_id=data["session_id"])
		#elif cmd == 'setopened': self.set_current_opened(path=data['path'])
		#elif cmd == 'clientpid': self.clientpid = data['pid']
		#elif cmd == "qmarker": self.marker_handler("q", data)
		#elif cmd == "wmarker": self.marker_handler("w", data)
		#elif cmd == "location": self.location_update_handle(data["loc"])
		#elif cmd == "keypressed": self.internal_key_pressed(data["key"])
		#elif cmd == "keypressed_raw": self.internal_key_pressed_raw(data["key"], data["modifiers"], data["text"])
		#elif cmd == "keyreleased_raw": self.internal_key_released_raw(data["key"], data["modifiers"])
		#elif cmd == "console": self.internal_console_request(data["data"])
		#elif cmd == "trackinfo": self.info_widget.set_tracking_info(data["data"])
		#elif cmd == "finish_screen": self.finish_screen(data["data"][0], data["data"][1], procpid)
		#elif cmd == "fault": self.open_fault()
		#elif cmd == "evalcache": self.evalcache_notification(data)
		else:
			print_to_stderr("Warn: unrecognized command", data)

	def message_handler_qtwrap(self, *args, **kwargs):
		print_to_stderr(*args, **kwargs)
		self.message_handler_qtsignal.emit(*args, **kwargs)

	def is_window_binded_mode(self):
		return True
		#bind_widget_flag = zenframe.settings.get(["gui", "bind_widget"])
		#return not bind_widget_flag == "false" and not zenframe.configure.CONFIGURE_NO_EMBEDING_WINDOWS


	def synchronize_subprocess_state(self):
		"""
			Пересылаем на ту сторону информацию об опциях интерфейса.
		"""
		pass
		#size = self.vsplitter.widget(0).size()
#
		#if not self.need_prescale and self.last_location is not None:
		#	self.client_communicator.send({"cmd":"location", "dct": self.last_location})
		#	info("restore saved eye location")
	#
		#if self.is_window_binded():
		#	self.client_communicator.send({"cmd":"resize", "size":(size.width(), size.height())})
		#self.client_communicator.send({"cmd":"set_perspective", "en": self.perspective_checkbox_state})
		#self.client_communicator.send({"cmd":"keyboard_retranslate", "en": not self.texteditor.isHidden()})
		#self.client_communicator.send({"cmd":"redraw"})


	def subprocess_finalization_do(self):
		trace("subprocess_finalization_do")
		for comm in self.client_finalization_list:
			comm.send({"cmd":"stopworld"})

	def closeEvent(self, event):
	#	self.store_gui_state()

		trace("closeEvent")
		if self.embeded_window_container:
			self.embeded_window_container.close()

		#if self.client_communicator and self.client_communicator is not self.main_communicator:
		#	trace("send stopworld")
		#	self.client_communicator.send({"cmd": "stopworld"})
		#	self.client_communicator.send({"cmd": "stopworld"})
#		else:
#			trace("send smooth_stopworld")
#			self.client_communicator.send({"cmd": "smooth_stopworld"})

		self.main_communicator.send({"cmd":"stopworld"})
		self.main_communicator.stop_listen()

		if zenframe.configure.CONFIGURE_SLEEPED_OPTIMIZATION and self.sleeped_client:
			trace("send sleeped optimization stopworld")
			self.sleeped_client.send({"cmd":"stopworld"})
			self.sleeped_client.stop_listen()

		self.guard.console_retransler.finish()
		print_to_stderr("APPLICATION quit")

		time.sleep(0.05)
		print(threading.enumerate())

		APPLICATION.quit()










	def _open_routine(self, path, update_texteditor=True):
		if not self.openlock.tryLock():
			return
		self.setWindowTitle(path)

		another_file = path != self.current_opened()
		oldopenned = path

		if update_texteditor:
			self.texteditor.open(path)

		if self.open_in_progress is True:
			"""Процедура открытия была инициирована раньше,
			чем прошлый открываемый скрипт отчитался об успешном завершении"""
			self.client_communicator.kill()
			self.client_finalization_list.append(self.client_communicator)

		if another_file:
			self.screen_saver.drop_background()

		#if self.embeded_window and self.open_in_progress is False:
		#	if not another_file and zencad.configure.CONFIGURE_SCREEN_SAVER_TRANSLATE:
		#		self.client_communicator.send({"cmd":"screenshot"})
		self.client_communicator.send({"cmd":"stop_activity"})
		self.client_finalization_list.append(self.client_communicator)

		trace("planned to finalize:", len(self.client_finalization_list))

		self.console.clear()
		path = self.current_opened()
		
		try:
			self.session_id += 1
			if zenframe.configure.CONFIGURE_SLEEPED_OPTIMIZATION and self.sleeped_client:
				""" Будим спящую заготовку """
				trace("unsleep procedure")
				self.client_communicator = self.sleeped_client
				size = self.vsplitter.widget(0).size()
				size = "{},{}".format(size.width(), size.height())
				success = self.client_communicator.send({"path":path, "need_prescale":self.need_prescale, "size":size})
				if not success:
					"""Если разбудить заготовку не удалось, просто создать новый процесс"""
					trace("NOT SUCCESS UNSLEEP ROUTINE")
					self.client_communicator = zencad.gui.application.start_unbounded_worker(path, 
						need_prescale = self.need_prescale, session_id=self.session_id, size=self.vsplitter.widget(0).size())
				# Инициируем создание новой заготовки.
				self.sleeped_client = zenframe.application.spawn_sleeped_client(self.session_id + 1)
				time.sleep(0.05)
	
			else:
				""" Если оптимизация не включена, то просто создать новый процесс. """
				self.client_communicator = zenframe.application.start_unbounded_agent(
					path, 
					session_id=self.session_id, 
					size=self.vsplitter.widget(0).size())

		except OSError as ex:
			print("Err: open error")
			return

		# Теперь новый клиент готов к работе.
		self.open_in_progress = True
		self.communicator_dictionary[self.client_communicator.subproc.pid] = self.client_communicator
#		trace("add to self.communicator_dictionary", [c for c in self.communicator_dictionary])
		self.client_communicator.oposite_clossed.connect(self.delete_communicator)
		self.client_communicator.newdata.connect(self.message_handler)
		self.client_communicator.start_listen()
		
		# Добавляем путь в список последних вызовов.
		#zencad.settings.Settings.add_recent(os.path.abspath(path))

		self.screen_saver.set_loading_state()
		# Сплиттер некоректно отработает, до первого showEvent
		if hasattr(self, "MARKER"):
			timeout = 100 if zenframe.configure.CONFIGURE_SLEEPED_OPTIMIZATION else 500
			old_window_container = self.embeded_window_container
			def foo():
				self.openlock.lock()
				if self.open_in_progress:
					self.replace_widget(self.screen_saver)
				if old_window_container is not None:
					old_window_container.close()
				self.openlock.unlock()

			if self.is_window_binded_mode():
				QTimer.singleShot(timeout, foo)
		self.MARKER=None

		# Если уведомления включены, обновить цель.
		if self.notifier:
			print_to_stderr("PATH:", path)
			self.notifier.retarget(path)
		
		#self.update_recent_menu()

		self.openlock.unlock()

	#def resizeEvent(self, ev):
	#	super().resizeEvent(ev)
		#self.embeded_window_resized()

	def open_fault(self):
		self.screen_saver.set_error_state()

	def delete_communicator(self, comm):
		"""Вызывается по сигналу об окончании сеанса"""

		trace("delete_communicator")

		self.openlock.lock()
		
		comm.stop_listen()
		
		if comm in self.client_finalization_list:
			self.client_finalization_list.remove(comm)
		
		del self.communicator_dictionary[comm.subproc.pid]
		
		# clean client_finalization_list from uncostistent nodes
		for comm in self.client_finalization_list:
			if comm not in self.communicator_dictionary.values():
				self.client_finalization_list.remove(comm)

		trace("del from self.communicator_dictionary {}".format([ c.subproc.pid for c 
			in self.communicator_dictionary.values()]))

		comm.kill()
		#comm.subproc.wait()

		self.openlock.unlock()




	def replace_widget(self, wdg):
		if wdg is not self.vsplitter.widget(0):
			wdg.resize(self.vsplitter.widget(0).size())
			self.vsplitter.replaceWidget(0, wdg)







































def exec_sandbox(prestart_command, display_mode=True):
	"""Запустить графический интерфейс в текущем потоке.

	Используются файловые дескрипторы по умолчанию, которые длжен открыть
	вызывающий поток."""

	global APPLICATION

	def signal_sigchild(a,b):
		os.wait()

	if sys.platform == "linux":
		signal.signal(signal.SIGCHLD, signal_sigchild) 

	APPLICATION = QApplication([])

	main_widget = ZenFrameSandbox(
		display_mode = display_mode,
		prestart_command=prestart_command)

	main_widget.show()
	APPLICATION.exec()

	time.sleep(0.05)

	procs = psutil.Process().children()	
	for p in procs:
		try:
			p.terminate()
		except psutil.NoSuchProcess:
			pass
