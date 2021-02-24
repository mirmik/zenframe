import os
import sys
import signal
import tempfile
import time

from PyQt5 import QtCore, QtGui, QtWidgets, QtOpenGL

from zenframe.inotifier import InotifyThread
from zenframe.screen_saver import ScreenSaverWidget
from zenframe.console import ConsoleWidget
from zenframe.text_editor import TextEditor
from zenframe.client import Client
from zenframe.configuration import Configuration

import zenframe.util
from zenframe.util import print_to_stderr
import zenframe.worker

from zenframe.settings import BaseSettings
from zenframe.actions import ZenFrameActionsMixin
from zenframe.finisher import invoke_destructors, terminate_all_subprocess, remove_destructor

if Configuration.FILTER_QT_WARNINGS:
    QtCore.QLoggingCategory.setFilterRules('qt.qpa.xcb=false')


class ZenFrame(QtWidgets.QMainWindow, ZenFrameActionsMixin):
    """Класс реализует логику общения с подчинёнными процессами,
    управление окнами, слежение за изменениями."""

    def __init__(self,
                 title,
                 sleeped_optimization=False,
                 initial_communicator=None,
                 restore_gui=True
                 ):
        super().__init__()
        self.setWindowTitle(title)

        self._initial_client = None
        self._current_client = None
        self._sleeped_client = None
        self._retransler = None
        self.notifier = InotifyThread(self)

        self._sleeped_optimization = sleeped_optimization

        self._keep_alive_pids = []
        self._clients = {}
        self._fscreen_mode = False  # Full screen mode enabled/disabled
        self.view_mode = False
        self._reopen_mode = False

        if initial_communicator:
            self._initial_client = Client(initial_communicator)
            self._current_client = self._initial_client

            initial_pid = self._initial_client.pid()
            self._clients[initial_pid] = self._initial_client
            self._keep_alive_pids.append(initial_pid)

        if self._sleeped_optimization:
            self._sleeped_client = self.spawn(sleeped=True)

        self.init_central_widget()
        if restore_gui:
            self.restore_gui_state()

        self.create_actions()
        self.create_menus()

        # Bind signals
        self.init_changes_notifier(self.reopen_current)

    def set_retransler(self, retransler):
        self.retransler = retransler

    def is_reopen_mode(self):
        return self._reopen_mode

    def spawn(self, sleeped=None):
        zenframe.util.print_to_stderr("Warning: Spawn is not reimplemented")
        return zenframe.worker.spawn_test_worker(sleeped=sleeped)

    def remake_sleeped_client(self):
        if self._sleeped_client:
            self._sleeped_client.terminate()

        self._sleeped_client = self.spawn(sleeped=True)

    def init_central_widget(self):
        self.console = ConsoleWidget()
        self.texteditor = TextEditor()
        self.screen_saver = ScreenSaverWidget()

        self.cw = QtWidgets.QWidget()
        self.cw_layout = QtWidgets.QVBoxLayout()
        self.hsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.vsplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        self.cw_layout.addWidget(self.hsplitter)
        self.cw.setLayout(self.cw_layout)

        self.hsplitter.addWidget(self.texteditor)
        self.hsplitter.addWidget(self.vsplitter)
        self.vsplitter.addWidget(self.screen_saver)
        self.vsplitter.addWidget(self.console)

        self.cw_layout.setContentsMargins(0, 0, 0, 0)
        self.cw_layout.setSpacing(0)

        self.setCentralWidget(self.cw)
        self.update()

    def central_widget_layout(self):
        return self.cw_layout

    def central_widget(self):
        return self.cw

    def init_changes_notifier(self, handler):
        self.notifier.changed.connect(handler)

    def subprocess_finalization_do(self):
        to_delete = []
        current_pid = self._current_client.pid()
        for pid in self._clients:
            if (
                    not pid == current_pid and
                    not pid in self._keep_alive_pids):
                self._clients[pid].terminate()
                to_delete.append(pid)

        for pid in to_delete:
            remove_destructor(id(self._clients[pid].communicator))
            del self._clients[pid]

    def reopen_current(self):
        self._openlock.lock()
        self.open(openpath=self._current_opened, update_texteditor=False)
        self.texteditor.reopen()
        self._openlock.unlock()

    def current_opened(self):
        return self._current_opened

    def bind_window(self, winid, pid):
        if self._current_client.pid() != pid:
            """Если заявленный pid отправителя не совпадает с pid текущего коммуникатора,
            то бинд уже неактуален."""
            print("Nonactual bind")
            return

        if not self._openlock.tryLock():
            return

        try:
            if self._bind_mode:
                window = QtGui.QWindow.fromWinId(winid)
                container = QtWidgets.QWidget.createWindowContainer(
                    window)

                # Удерживаем ссылки на объекты, чтобы избежать
                # произвола от сборщика мусора
                self._current_client.set_embed(
                    window=window,
                    widget=container)

                self.vsplitter.replaceWidget(0, container)

            self.setWindowTitle(self._current_opened)
            self.synchronize_subprocess_state()

        except Exception as ex:
            self._openlock.unlock()
            print_to_stderr("exception on window bind", ex)
            raise ex

        self.subprocess_finalization_do()
        self._openlock.unlock()

    def synchronize_subprocess_state(self):
        size = self.vsplitter.widget(0).size()
        if self._bind_mode:
            self._current_client.communicator.send({
                "cmd": "resize",
                "size": (size.width(), size.height())
            })

        self._current_client.communicator.send({
            "cmd": "keyboard_retranslate",
            "en": not self.texteditor.isHidden()
        })

    def restore_gui_state(self):
        hsplitter_position = BaseSettings.instance().get(
            ["memory", "hsplitter_position"])
        vsplitter_position = BaseSettings.instance().get(
            ["memory", "vsplitter_position"])
        texteditor_hidden = BaseSettings.instance().get(
            ["memory", "texteditor_hidden"])
        console_hidden = BaseSettings.instance().get(
            ["memory", "console_hidden"])
        wsize = BaseSettings.instance().get(["memory", "wsize"])
        if hsplitter_position:
            self.hsplitter.setSizes([int(s) for s in hsplitter_position])
        if vsplitter_position:
            self.vsplitter.setSizes([int(s) for s in vsplitter_position])
        if texteditor_hidden:
            self.hideEditor(True)
        if console_hidden:
            self.hideConsole(True)
        if wsize:
            self.setGeometry(wsize)

        w = self.hsplitter.width()
        h = self.vsplitter.height()
        if hsplitter_position[0] == "0" or hsplitter_position[0] == "1":
            self.hsplitter.setSizes([0.382*w, 0.618*w])
        if vsplitter_position[0] == "0" or vsplitter_position[1] == "0":
            self.vsplitter.setSizes([0.618*h, 0.382*h])

        self.hsplitter.refresh()
        self.vsplitter.refresh()
        self.update()

    def store_gui_state(self):
        hsplitter_position = self.hsplitter.sizes()
        vsplitter_position = self.vsplitter.sizes()
        wsize = self.geometry()
        BaseSettings.instance().set(["memory", "texteditor_hidden"],
                                    self.texteditor.isHidden())
        BaseSettings.instance().set(
            ["memory", "console_hidden"], self.console.isHidden())
        BaseSettings.instance().set(
            ["memory", "hsplitter_position"], hsplitter_position)
        BaseSettings.instance().set(
            ["memory", "vsplitter_position"], vsplitter_position)
        BaseSettings.instance().set(["memory", "wsize"], wsize)
        BaseSettings.instance().store()

    def closeEvent(self, ev):
        self.store_gui_state()

        if self._initial_client:
            self._initial_client.send({"cmd": "main_finished"})

        invoke_destructors()
        terminate_all_subprocess()

    def enable_display_changed_mode(self):
        self.screen_saver.set_loading_state()
        if self.vsplitter.widget(0) is not self.screen_saver:
            self.vsplitter.replaceWidget(0, self.screen_saver)

    def open(self, openpath, update_texteditor=True):
        self._openlock.lock()

        self._reopen_mode = openpath == self._current_opened

        self._current_opened = openpath
        if update_texteditor:
            self.texteditor.open(openpath)

        self.notifier.clear()
        self.notifier.add_target(openpath)

        if self._sleeped_optimization:
            client = self._sleeped_client
            size = self.vsplitter.widget(0).size()
            size = "{},{}".format(size.width(), size.height())
            client.communicator.send({
                "cmd": "unsleep",
                "path": openpath,
                "need_prescale": self._bind_mode,
                "size": size
            })

            self._sleeped_client = self.spawn(sleeped=True)

        else:
            size = self.vsplitter.widget(0).size()
            size = (size[0], size[1])
            client = self.spawn(
                path=openpath, need_prescale=self._bind_mode, size=size)

        self._current_client = client
        self._clients[client.pid()] = client

        self._current_client.communicator.bind_handler(self.new_worker_message)
        self._current_client.communicator.start_listen()

        self.enable_display_changed_mode()

        self.console.clear()
        self.setWindowTitle(self._current_opened)
        self.openStartEvent(openpath)
        self._openlock.unlock()

    def openStartEvent(self, path):
        pass


def sigchld_handler(a, b):
    print_to_stderr("SIGCHLD", a, b)


def start_application(openpath=None, none=False, unbound=False, norestore=False, sleeped_optimization=True):
    QAPP = QtWidgets.QApplication(sys.argv[1:])
    initial_communicator = None

    signal.signal(signal.SIGCHLD, sigchld_handler)  # Is not worked? Why?
    setup_interrupt_handlers()

    if unbound:
        # Переопределяем дескрипторы, чтобы стандартный поток вывода пошёл
        # через ретранслятор. Теперь все консольные сообщения будуут обвешиваться
        # тегами и поступать на коммуникатор.
        retransler = ConsoleRetransler(sys.stdout)
        retransler.start()

        # Коммуникатор будет слать сообщения на скрытый файл,
        # тоесть, на истинный stdout
        initial_communicator = Communicator(
            ifile=sys.stdin, ofile=retransler.new_file)

        # Показываем ретранслятору его коммуникатор.
        retransler.set_communicator(initial_communicator)

        data = initial_communicator.simple_read()
        dct0 = json.loads(data)

        initial_communicator.declared_opposite_pid = int(dct0["data"])

    openpath = zenframe.util.create_temporary_file()

    MAINWINDOW = ZenFrame(
        title="ZenFrame",
        initial_communicator=initial_communicator,
        restore_gui=not norestore,
        sleeped_optimization=sleeped_optimization)

    if unbound:
        initial_communicator.bind_handler(MAINWINDOW.new_worker_message)
        initial_communicator.start_listen()

    if openpath:
        if not unbound:
            MAINWINDOW.open(openpath)
        else:
            MAINWINDOW.open_declared(openpath)

    timer = QtCore.QTimer()
    timer.start(500)  # You may change this if you wish.
    timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.

    MAINWINDOW.show()
    QAPP.exec()
