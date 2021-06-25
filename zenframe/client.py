# NOTE: При работе с pyinstaller pid возвращаемый с submodule отличается от declared_pid


class Client:
    """ Хранит объекты, связанные с управлением одним клиентом. """

    def __init__(self, communicator=None, subprocess=None, thread=False):
        self.communicator = communicator
        self.subprocess = subprocess
        self.embeded_window = None
        self.embeded_widget = None
        self.thread_mode = thread

    def set_embed(self, window, widget):
        self.embeded_window = window
        self.embeded_widget = widget

    def pid(self):
        if self.thread_mode:
            return self.communicator.declared_opposite_pid

        if self.subprocess:
            return self.subprocess.pid
        else:
            return self.communicator.declared_opposite_pid

    def declared_pid(self):
        return self.communicator.declared_opposite_pid

    def send(self, *args, **kwargs):
        return self.communicator.send(*args, **kwargs)

    def terminate(self, nowait=False):
        if self.thread_mode:
            self.communicator.stop_listen(nowait=nowait)
            self.communicator.close()
            return

        self.communicator.stop_listen(nowait=nowait)
        self.communicator.close()
        self.subprocess.terminate()

    def terminate_only(self):
        if self.subprocess:
            self.subprocess.terminate()
