#!/usr/bin/env python3

import os
import sys
import json

from PyQt5.QtCore import pyqtSignal, QObject

from zenframe.util import print_to_stderr
from zenframe.listener import Listener
from zenframe.configuration import Configuration
from zenframe.finisher import register_destructor


class Communicator(QObject):
    """Объект обеспечивает связь между процессами, позволяя
    передавать комманды и отладочный вывод между оболочком и
    инстансами рабочих процессов.
    Связь обеспечивается через входной файл @ifile и
    выходной @ofile.

    TODO: вынести subproc из коммуникатора.
    """

    oposite_clossed = pyqtSignal()
    newdata = pyqtSignal(dict, int)

    def __init__(self, ifile, ofile):
        super().__init__()
        self.declared_opposite_pid = None
        self.ifile = ifile
        self.ofile = ofile
        self._listener = None

        self.send({"cmd": "set_opposite_pid", "data": os.getpid()})

        register_destructor(id(self), self.stop_listen)

    def newdata_handler(self, inputdata):
        if Configuration.COMMUNICATOR_TRACE:
            print_to_stderr("recv", inputdata)

        try:
            unwraped_data = json.loads(inputdata)

            if unwraped_data["cmd"] == "set_opposite_pid":
                self.declared_opposite_pid = unwraped_data["data"]
                return

            self.newdata.emit(unwraped_data, self.declared_opposite_pid)

        except Exception as ex:
            if Configuration.DROP_COMMUNICATOR_INVALIDE_DATA:
                return

            print_to_stderr(ex)
            sys.exit()

    def simple_read(self):
        """Чтение из входного файла. Не должно вызываться после
        вызова метода start_listen"""
        inputdata = self.ifile.readline()
        return inputdata

    def bind_handler(self, function):
        """Подписать внешний метод на событие прихода
        очередной команды. Если подписчиков много, событие получат все."""
        self.newdata.connect(function)

    def start_listen(self):
        self._listener = Listener(self.ifile, self)
        self._listener.stream_handler = self.newdata_handler
        self._listener.start()

    def stop_listen(self, nowait=False):
        if self._listener:
            self._listener.stop()

            if not nowait:
                self._listener.wait()

    def close(self):
        self.ifile.close()
        self.ofile.close()

    def send(self, obj):
        if Configuration.COMMUNICATOR_TRACE:
            print_to_stderr("send", obj)

        sendstr = json.dumps(obj) + "\n"

        try:
            self.ofile.write(sendstr)
            self.ofile.flush()
            return True
        except Exception as ex:
            print_to_stderr(ex)
            return False
