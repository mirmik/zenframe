import sys
import io
import os
import time
import traceback
import subprocess
import runpy
import signal
import json

from PyQt5 import QtCore, QtGui, QtWidgets, QtOpenGL

from zenframe.util import print_to_stderr
from zenframe.retransler import ConsoleRetransler
from zenframe.communicator import Communicator
from zenframe.client import Client
from zenframe.configuration import Configuration
from zenframe.finisher import invoke_destructors

COMMUNICATOR = None
RETRANSLER = None
PRESCALE_SIZE = None
BOTTOM_HALF = None
UNBOUND_MODE = False

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
            data1 = COMMUNICATOR.simple_read()

            if Configuration.COMMUNICATOR_TRACE:
                print_to_stderr("slep", data0)
                print_to_stderr("slep", data1)
            dct0 = json.loads(data0)  # set_oposite_pid
            dct1 = json.loads(data1)  # unwait
        except Exception as ex:
            print_to_stderr("sleeped thread finished with exception")
            print_to_stderr(ex)
            sys.exit()

        COMMUNICATOR.declared_opposite_pid = int(dct0["data"])
        path = dct1["path"]
        PRESCALE_SIZE = list((int(a) for a in dct1["size"].split(",")))

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


def unbound_worker_bottom_half(scene):
    """Вызывается из showapi"""

    widget = BOTTOM_HALF(COMMUNICATOR, PRESCALE_SIZE, scene)

    COMMUNICATOR.send({
        "cmd": "bindwin",
        "id": int(widget.winId()),
        "pid": os.getpid(),
    })

    widget.show()
    time.sleep(0.05)

    timer = QtCore.QTimer()
    timer.start(Configuration.TIMER_PULSE * 1000)
    timer.timeout.connect(lambda: None)

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
    QAPP = QtWidgets.QApplication([])
    CONSOLE_FILTER = ConsoleRetransler(sys.stdout, without_wrap=True)
    CONSOLE_FILTER.start_listen()

    communicator = start_unbounded_frame(sys.argv[0], application_name)

    time.sleep(3)

    widget = widget_creator(communicator, *args, **kwargs)

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
    timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.

    QtWidgets.QApplication.instance().exec()
