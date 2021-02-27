from zenframe.util import print_to_stderr


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

    def send(self, *args, **kwargs):
        return self.communicator.send(*args, **kwargs)

    def terminate(self):
        if self.thread_mode:
            self.communicator.stop_listen()
            self.communicator.close()
            return

        self.communicator.stop_listen()
        self.communicator.close()
        self.subprocess.terminate()
