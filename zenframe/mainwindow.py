import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from zenframe.inotifier import InotifyThread
from zenframe.screen_saver import ScreenSaverWidget
from zenframe.console import ConsoleWidget
from zenframe.text_editor import TextEditor
from zenframe.client import Client
from zenframe.configuration import Configuration

from zenframe.util import print_to_stderr

from zenframe.settings import BaseSettings
from zenframe.actions import ZenFrameActionsMixin
from zenframe.finisher import invoke_destructors, terminate_all_subprocess, remove_destructor
from zenframe.unbound import start_unbounded_worker, start_thread_worker


if Configuration.FILTER_QT_WARNINGS:
    QtCore.QLoggingCategory.setFilterRules('qt.qpa.xcb=false')

MAINWINDOW = None


def instance():
    return MAINWINDOW


class ZenFrame(QtWidgets.QMainWindow, ZenFrameActionsMixin):
    """Класс реализует логику общения с подчинёнными процессами,
    управление окнами, слежение за изменениями."""

    def __init__(self,
                 title,
                 application_name,
                 initial_communicator=None,
                 restore_gui=True
                 ):
        global MAINWINDOW
        MAINWINDOW = self

        super().__init__()
        self.resize(800, 600)

        self.setWindowTitle(title)

        # MODES
        self.use_threads = False
        self.use_sleeped_process = True

        # Init variables
        self._openlock = QtCore.QMutex(QtCore.QMutex.Recursive)

        # Путь с именем текщего открытого/открываемого файла.
        self._current_opened = None

        self._application_name = application_name
        self._initial_client = None
        self._current_client = None
        self._sleeped_client = None
        self._retransler = None
        self.notifier = InotifyThread(self)

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

        if self.use_sleeped_process:
            self._sleeped_client = self.spawn_process(self._application_name)

        self.init_central_widget()
        if restore_gui:
            self.restore_gui_state()

        self.create_actions()
        self.create_menus()

        # Bind signals
        self.init_changes_notifier(self.reopen_current)

    def spawn_process(self, application_name):
        return start_unbounded_worker(application_name=application_name)

    def set_retransler(self, retransler):
        self.retransler = retransler

    def is_reopen_mode(self):
        return self._reopen_mode

    def remake_sleeped_client(self):
        if self._sleeped_client:
            self._sleeped_client.terminate()

        self._sleeped_client = self.spawn_process(self._application_name)

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
                    pid not in self._keep_alive_pids):
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
        if not self._openlock.tryLock():
            return

        try:
            window = QtGui.QWindow.fromWinId(winid)
            container = QtWidgets.QWidget.createWindowContainer(
                window)

            # Удерживаем ссылки на объекты, чтобы избежать
            # произвола от сборщика мусора
            self._current_client.set_embed(
                window=window,
                widget=container)

            # For Windows.
            # Window lost focus after createWindowContainer
            if sys.platform == "win32":
                self.activateWindow()

            self.vsplitter.replaceWidget(0, container)

            self.setWindowTitle(self._current_opened)
            self.synchronize_subprocess_state()

            # time.sleep(0.01)
            # self.resize(self.size())

        except Exception as ex:
            self._openlock.unlock()
            print_to_stderr("exception on window bind", ex)
            raise ex

        self.subprocess_finalization_do()
        self._openlock.unlock()

    def synchronize_subprocess_state(self):
        size = self.vsplitter.widget(0).size()
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

        client = self.start_new_client(openpath)
        oldclient = self._current_client

        self._current_client = client
        self._clients[client.pid()] = client

        self._current_client.communicator.bind_handler(self.message_handler)
        self._current_client.communicator.start_listen()

        self.enable_display_changed_mode()

        if oldclient:
            oldclient.terminate_only()

        self.console.clear()
        self.setWindowTitle(self._current_opened)
        self.openStartEvent(openpath)
        self._openlock.unlock()

    def start_new_client(self, openpath):
        if self.use_threads:
            return start_thread_worker(openpath)

        if self.use_sleeped_process:
            client = self._sleeped_client
            self._sleeped_client = self.spawn_process(self._application_name)
        else:
            client = self.spawn_process(self._application_name)

        client.communicator.send({
            "cmd": "unsleep",
            "path": openpath
        })

        return client

    def internal_key_pressed_raw(self, key, modifiers, text):
        self.activateWindow()
        self.texteditor.setFocus()
        modifiers = QtCore.Qt.KeyboardModifiers()
        event = QtGui.QKeyEvent(
            QtCore.QEvent.KeyPress, key, QtCore.Qt.KeyboardModifier(modifiers), text)
        QtGui.QGuiApplication.postEvent(self.texteditor, event)

    def internal_key_released_raw(self, key, modifiers):
        self.activateWindow()
        self.texteditor.setFocus()
        modifiers = QtCore.Qt.KeyboardModifiers()
        event = QtGui.QKeyEvent(QtCore.QEvent.KeyRelease,
                                key, QtCore.Qt.KeyboardModifier(modifiers))
        QtGui.QGuiApplication.postEvent(self.texteditor, event)

    def open_declared(self, path):
        self._current_opened = path
        self.texteditor.open(path)

        self.notifier.clear()
        self.notifier.add_target(path)

    def message_handler(self, data, procpid):
        try:
            cmd = data["cmd"]
        except Exception:
            return False

        if procpid != self._current_client.declared_pid() and data["cmd"] != "finish_screen":
            return False

        if cmd == 'bindwin':
            self.bind_window(winid=data['id'], pid=data["pid"])
        elif cmd == "except":
            print(
                f"Exception in subprocess with executable path: {data['path']}")
            print(data["header"])
            print(data["tb"])
        elif cmd == "keypressed_raw":
            self.internal_key_pressed_raw(
                data["key"], data["modifiers"], data["text"])
        elif cmd == "keyreleased_raw":
            self.internal_key_released_raw(data["key"], data["modifiers"])
        elif cmd == "console":
            self.internal_console_request(data["data"])
        else:
            return False

        return True

    def internal_console_request(self, data):
        self.console.write(data)

# TEST
    @QtCore.pyqtSlot()
    def hello(self):
        print("hello")
        import zenframe.unbound
        zenframe.unbound.BOTTOM_HALF_TEST()

    def bind_thread_widget(self, wdg):
        # wdg.show()
        # wdg.moveToThread(QtWidgets.QApplication.instance().thread())
        self.vsplitter.replaceWidget(0, wdg)

    def openStartEvent(self, path):
        """ Добавляем путь в список последних вызовов."""
        BaseSettings.instance().add_recent(os.path.abspath(path))
        self.update_recent_menu()
