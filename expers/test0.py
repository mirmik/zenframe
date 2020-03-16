#!/usr/bin/env python3

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtTest import *

import zenframe
import zenframe.agent
import sys

qapp = QApplication(sys.argv[1:])

font = QFont()
font.setPointSize(72)
font.setBold(True)

wdg = QLabel("Hello")

wdg.setFont(font)
wdg.show()

agent = zenframe.agent.make_agent(on_close=qapp.quit)
agent.bind_window(wdg.winId())

qapp.exec()