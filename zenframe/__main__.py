#!/usr/bin/env python3
# coding:utf-8

import os
import sys
import time

import psutil
import traceback
import runpy
import signal
import time

import zenframe.starter as frame
import zenframe.argparse

from PyQt5 import QtWidgets


class TestWidget(QtWidgets.QWidget):
    def __init__(self, timelapse=0):
        super().__init__()
        self.timelapse = timelapse
        self.lbl = QtWidgets.QLabel("ZenFrame")
        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self.lbl)
        self.setLayout(layout)

    def paintEvent(self, ev):
        print("TestWidget.paintEvent")
        super().paintEvent(ev)
        time.sleep(self.timelapse)

    def showEvent(self, ev):
        print("TestWidget.showEvent")
        super().showEvent(ev)
        time.sleep(self.timelapse)

    def resizeEvent(self, ev):
        print("TestWidget.resizeEvent")
        super().resizeEvent(ev)
        time.sleep(self.timelapse)


def console_options_handle():
    parser = zenframe.argparse.ArgumentParser()
    pargs = parser.parse_args()
    return pargs


def top_half(communicator):
    pass


def bottom_half(communicator, timelapse=0):
    from PyQt5 import QtCore
    Qt = QtCore.Qt
    wdg = TestWidget(timelapse=timelapse)
    return wdg


def frame_creator(openpath, initial_communicator, norestore, unbound):
    from zenframe.mainwindow import ZenFrame
    from zenframe.util import create_temporary_file

    if openpath is None:
        openpath = create_temporary_file()

    mainwindow = ZenFrame(
        title="zenframe",
        application_name="zenframe",
        initial_communicator=initial_communicator,
        restore_gui=not norestore)

    return mainwindow, openpath


def main():
    pargs = console_options_handle()

    if pargs.display:
        from PyQt5 import QtWidgets, QtCore
        app = QtWidgets.QApplication([])
        wdg = QtWidgets.QLabel("ZenFrame")  # TestWidget()
        wdg.show()

        return app.exec()

    frame.invoke(
        pargs,
        frame_creator=frame_creator,
        exec_top_half=top_half,
        exec_bottom_half=bottom_half)


if __name__ == "__main__":
    main()
