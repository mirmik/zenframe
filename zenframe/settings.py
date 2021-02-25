from PyQt5.QtCore import *
import sys


def default_text_editor_os():
    if sys.platform == "linux":
        return "xdg-open {path}"
    elif sys.platform in ["win32", "win64"]:
        return "notepad.exe {path}"
    else:
        return ""


class BaseSettings:
    _instance = None

    def __init__(self, name, subname, default):
        self.name = name
        self.subname = subname
        self.list_of_settings = default
        self.restored = False

        BaseSettings._instance = self

    def store(self):
        settings = QSettings(self.name, self.subname)

        for g in self.list_of_settings:
            settings.beginGroup(g)
            for k in self.list_of_settings[g]:
                settings.setValue(k, self.list_of_settings[g][k])
            settings.endGroup()

    def restore(self):
        if self.restored:
            return

        settings = QSettings(self.name, self.subname)

        for g in self.list_of_settings:
            settings.beginGroup(g)
            for k in self.list_of_settings[g]:
                self.list_of_settings[g][k] = settings.value(
                    k, self.list_of_settings[g][k])
            settings.endGroup()

        self.restored = True

    def _restore_type(self, val):
        if val == "true":
            return True
        if val == "false":
            return False

        if isinstance(val, str):
            try:
                if float(val):
                    return float(val)
            except:
                pass

        return val

    def get(self, path):
        it = self.list_of_settings
        for p in path:
            it = it[p]

        it = self._restore_type(it)
        return it

    def set(self, path, value):
        it = self.list_of_settings
        for p in path[:-1]:
            it = it[p]
        it[path[-1]] = value

    @classmethod
    def instance(self):
        return self._instance


# if not reimplemented
BaseSettings("zenframe", "settings", 

{
            "gui": {
                "text_editor": default_text_editor_os(),
                "start_widget": True,
                "bind_widget": True
            },
            "memory": {
                "recents": [],
                "hsplitter_position": (300, 500),
                "vsplitter_position": (500, 300),
                "console_hidden": False,
                "texteditor_hidden": False,
                "wsize": None
            }
        }
)