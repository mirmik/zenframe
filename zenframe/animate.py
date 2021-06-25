from PyQt5.QtCore import QThread, pyqtSignal

import time
import traceback
import sys

import zenframe


class AnimateThread(QThread):
    after_update_signal = pyqtSignal()
    ANIMATE_THREADS = []

    def __init__(self, updater, step, debug_mode=False):
        QThread.__init__(self)
        self.updater = updater
        self.cancelled = False
        self.step = step
        self.debug_mode = debug_mode

        self.ANIMATE_THREADS.append(self)
        zenframe.finisher.register_destructor(self, self.finish)

    @classmethod
    def start_all_threads(cls):
        for a in cls.ANIMATE_THREADS:
            a.start()

    def finish(self):
        if self.debug_mode:
            zenframe.util.print_to_stderr("AnimateThread::Finish")
        self.cancelled = True
        self.wait()

    def set_animate_step(self, step):
        self.animate_step = step

    def run(self):
        start_time = time.time()
        plantime = start_time

        while 1:
            curtime = time.time()
            errtime = plantime - curtime

            if self.cancelled:
                if self.debug_mode:
                    zenframe.util.print_to_stderr("AnimateThread::return")
                return

            if errtime > 0:
                time.sleep(errtime)

            if self.cancelled:
                if self.debug_mode:
                    zenframe.util.print_to_stderr("AnimateThread::return")
                return

            try:
                self.updater()
                if self.cancelled:
                    return
            except Exception:
                print("Error: Exception in animation thread.")
                traceback.print_exc(file=sys.stdout)
                return

            plantime = plantime + self.step


def create_animate_thread(updater, step, debug_mode=False):
    athr = AnimateThread(updater=updater, step=step, debug_mode=debug_mode)
    athr.start()
