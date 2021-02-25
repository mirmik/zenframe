#!/usr/bin/env python3
# coding:utf-8

import os
import sys
import time

import psutil
import traceback
import runpy
import signal

import zenframe.starter as frame

from PyQt5 import QtWidgets


def console_options_handle():
    parser = frame.ArgumentParser()
    pargs = parser.parse_args()
    return pargs


def top_half(communicator):
    pass


def bottom_half(communicator, init_size, scene):
    # display = DisplayWidget(
    #    communicator=communicator,
    #    init_size=init_size)
    # display.attach_scene(scene)

    # communicator.bind_handler(display.external_communication_command)
    wdg = QtWidgets.QWidget()

    return wdg


def frame_creator(openpath, initial_communicator, norestore, unbound):
    from zenframe.mainwindow import ZenFrame

    mainwindow = ZenFrame(
    	title="zenframe",
    	application_name="zenframe",
        initial_communicator=initial_communicator,
        restore_gui=not norestore)

    return mainwindow, openpath


def main():
    pargs = console_options_handle()

    frame.invoke(
        pargs,
        frame_creator=frame_creator,
        exec_top_half=top_half,
        exec_bottom_half=bottom_half)


if __name__ == "__main__":
    main()
