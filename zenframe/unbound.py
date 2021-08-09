import io
import sys
import os
import time
import traceback
import subprocess
import runpy
import json

from PyQt5 import QtCore, QtWidgets

from zenframe.util import print_to_stderr
from zenframe.retransler import ConsoleRetransler
from zenframe.communicator import Communicator
from zenframe.client import Client
from zenframe.configuration import Configuration
from zenframe.finisher import invoke_destructors
from zenframe.animate import AnimateThread

COMMUNICATOR = None
RETRANSLER = None
PRESCALE_SIZE = None
BOTTOM_HALF = None
UNBOUND_MODE = False
NOSHOW_MODE = False

# TEST
THREAD_MODE = False
BOTTOM_HALF_TEST = None

if Configuration.FILTER_QT_WARNINGS:
    QtCore.QLoggingCategory.setFilterRules('qt.qpa.xcb=false')


def start_unbounded_worker(application_name):
    interpreter = sys.executable

    cmd = f'{interpreter} -m {application_name} --unbound --sleeped'

    subproc = None
    try:
        subproc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                                   close_fds=True)

    except OSError as ex:
        print("Warn: subprocess.Popen finished with exception", ex)
        raise ex

    stdout = io.TextIOWrapper(subproc.stdout, line_buffering=True)
    stdin = io.TextIOWrapper(subproc.stdin, line_buffering=True)

    communicator = Communicator(ifile=stdout, ofile=stdin)
    client = Client(communicator=communicator, subprocess=subproc)

    return client


def unbound_worker_top_half(top_half, bottom_half):
    global COMMUNICATOR, PRESCALE_SIZE, RETRANSLER
    global BOTTOM_HALF, UNBOUND_MODE

    BOTTOM_HALF = bottom_half
    UNBOUND_MODE = True

    QAPP = QtWidgets.QApplication.instance()
    if QAPP is None:
        QAPP = QtWidgets.QApplication([])

    # Переопределяем дескрипторы, чтобы стандартный поток вывода пошёл
    # через ретранслятор. Теперь все консольные сообщения будуут обвешиваться
    # тегами и поступать на коммуникатор.
    RETRANSLER = ConsoleRetransler(sys.stdout)
    RETRANSLER.start_listen()

    # Коммуникатор будет слать сообщения на скрытый файл,
    # тоесть, на истинный stdout
    COMMUNICATOR = Communicator(
        ifile=sys.stdin, ofile=RETRANSLER.new_file)

    # Показываем ретранслятору его коммуникатор.
    RETRANSLER.set_communicator(COMMUNICATOR)

    if True:  # Sleeped
        # Спящий процесс оптимизирует время загрузки скрипта.
        # этот процесс повисает в цикле чтения и дожидается,
        # пока ему не передадут задание на выполнение.
        # оптимизация достигается за счёт предварительной загрузки библиотек.
        try:
            data0 = COMMUNICATOR.simple_read()
            if Configuration.COMMUNICATOR_TRACE:
                print_to_stderr("slep", data0)

            data1 = COMMUNICATOR.simple_read()
            if Configuration.COMMUNICATOR_TRACE:
                print_to_stderr("slep", data1)

            dct0 = json.loads(data0)  # set_oposite_pid
            dct1 = json.loads(data1)  # unwait
        except Exception as ex:
            print_to_stderr("sleeped thread finished with exception")
            print_to_stderr(ex)
            sys.exit()

        COMMUNICATOR.declared_opposite_pid = int(dct0["data"])
        path = dct1["path"]

    COMMUNICATOR.oposite_clossed.connect(
        QtWidgets.QApplication.instance().quit)

    top_half(COMMUNICATOR)

    COMMUNICATOR.start_listen()

    # Меняем директорию, чтобы скрипт мог подключать зависимые модули.
    path = os.path.abspath(path)
    directory = os.path.dirname(os.path.abspath(path))
    os.chdir(directory)
    sys.path.append(directory)

    # Совершив подготовительные процедуры, запускаем скрипт.
    try:
        runpy.run_path(path, run_name="__main__")
    except Exception as ex:
        tb = traceback.format_exc()
        COMMUNICATOR.send({"cmd": "except", "path": path,
                           "header": repr(ex), "tb": str(tb)})


def unbound_worker_bottom_half(*args, **kwargs):
    """Вызывается из showapi"""

    widget = BOTTOM_HALF(COMMUNICATOR, *args, **kwargs)

    if THREAD_MODE:
        return worker_thread_mode_impl(widget)

    COMMUNICATOR.send({
        "cmd": "bindwin",
        "id": int(widget.winId()),
        "pid": os.getpid(),
    })

    widget.window().setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
    widget.show()
    time.sleep(0.05)

    timer = QtCore.QTimer()
    timer.start(Configuration.TIMER_PULSE * 1000)
    timer.timeout.connect(lambda: None)

    AnimateThread.start_all_threads()
    QtWidgets.QApplication.instance().exec()


def is_unbound_mode():
    return UNBOUND_MODE


def start_unbounded_frame(path, application_name):
    interpreter = sys.executable

    cmd = f'{interpreter} -m {application_name} "{path}" --frame'

    subproc = None
    try:
        subproc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                                   close_fds=True)
    except OSError as ex:
        print("Warn: subprocess.Popen finished with exception", ex)
        raise ex

    stdout = io.TextIOWrapper(subproc.stdout, line_buffering=True)
    stdin = io.TextIOWrapper(subproc.stdin, line_buffering=True)

    communicator = Communicator(ifile=stdout, ofile=stdin)
    communicator.subproc = subproc

    return communicator


def unbound_frame_summon(widget_creator, application_name, *args, **kwargs):
    QAPP = QtWidgets.QApplication.instance()
    if QAPP is None:
        QAPP = QtWidgets.QApplication([])

    CONSOLE_FILTER = ConsoleRetransler(sys.stdout, without_wrap=True)
    CONSOLE_FILTER.start_listen()

    communicator = start_unbounded_frame(sys.argv[0], application_name)

    time.sleep(3)

    widget = widget_creator(communicator, *args, **kwargs)
    widget.window().setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

    communicator.oposite_clossed.connect(
        QtWidgets.QApplication.instance().quit)
    communicator.start_listen()

    # if BIND_MODE:
    communicator.send({
        "cmd": "bindwin",
        "id": int(widget.winId()),
        "pid": os.getpid(),
    })
    widget.show()

    time.sleep(0.05)
    timer = QtCore.QTimer()
    timer.start(500)  # You may change this if you wish.
    timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.

    def finished_listener(data):
        if data["cmd"] == "main_finished":
            invoke_destructors()
            os.wait()

            QtWidgets.QApplication.quit()

    communicator.newdata.connect(finished_listener)

    timer = QtCore.QTimer()
    timer.start(500)  # You may change this if you wish.

    def unsleeper():
        try:
            None
            pass
        except:
            os._exit(0)

    timer.timeout.connect(unsleeper)  # Let the interpreter run each 500 ms.

    AnimateThread.start_all_threads()
    QtWidgets.QApplication.instance().exec()


# TEST
def test_bottom_half_2(*args, **kwargs):
    import zenframe.mainwindow
    wdg = QtWidgets.QLabel("ThreadMode!!!!")
    zenframe.mainwindow.instance().bind_thread_widget(wdg)


def test_bottom_half(*args, **kwargs):
    print("test_bottom_half!!!")


class ThreadExecutor(QtCore.QThread):
    def __init__(self, w, r, openpath):
        super().__init__()
        self.w_fd = w
        self.r_fd = r
        self.w = io.TextIOWrapper(
            os.fdopen(self.w_fd, "wb"), line_buffering=True)
        self.r = io.TextIOWrapper(
            os.fdopen(self.r_fd, "rb"), line_buffering=True)
        self.openpath = openpath

    def run(self):
        print("run")
        self.communicator = Communicator(self.r, self.w)
        self.communicator.start_listen()

        global COMMUNICATOR
        COMMUNICATOR = self.communicator

        global BOTTOM_HALF, THREAD_MODE
        BOTTOM_HALF = test_bottom_half
        THREAD_MODE = True

        try:
            runpy.run_path(self.openpath, run_name="__main__")
        except Exception as ex:
            tb = traceback.format_exc()
            self.communicator.send({"cmd": "except", "path": self.openpath,
                                    "header": repr(ex), "tb": str(tb)})


def worker_thread_mode_impl(wdg):
    import zenframe.mainwindow
    global BOTTOM_HALF_TEST
    BOTTOM_HALF_TEST = test_bottom_half_2
    QtCore.QMetaObject.invokeMethod(
        zenframe.mainwindow.instance(), "hello", QtCore.Qt.QueuedConnection)
    print("worker_thread_mode_impl")

#    dispatchToMainThread(test_bottom_half_2)


def start_thread_worker(openpath):
    main_r, thread_w = os.pipe()
    thread_r, main_w = os.pipe()

    thr = ThreadExecutor(w=thread_w, r=thread_r, openpath=openpath)

    w = io.TextIOWrapper(os.fdopen(main_w, "wb"), line_buffering=True)
    r = io.TextIOWrapper(os.fdopen(main_r, "rb"), line_buffering=True)

    communicator = Communicator(r, w)

    thr.start()
    return Client(communicator, thread=thr)
