import argparse

from zenframe.configuration import Configuration


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__()

        #self.add_argument("--zenframe", action="store_true", help="Test frame sublibrary")
        self.add_argument("--unbound", action="store_true")
        self.add_argument("--display", action="store_true")
        self.add_argument("--frame", action="store_true")
        self.add_argument("--sleeped", action="store_true",
                          help="Don't use manualy. Create sleeped thread.")
        self.add_argument("paths", type=str, nargs="*", help="runned file")
        self.add_argument("--no-restore", action="store_true")

        # NOTE: Неизвестно нужны ли параметры задания геометрии.
        self.add_argument("--size")

    def parse_args(self, *args, **kwargs):
        pargs = super().parse_args(*args, **kwargs)

        if Configuration.TRACE_EXEC_OPTION:
            from zenframe.util import print_to_stderr
            print_to_stderr(sys.argv, pargs)

        return pargs
