from PyQt5.QtCore import QSettings
import sys
import os


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
            except Exception:
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
        if self._instance is None:
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
            self._instance.restore()

        return self._instance

    def get_recent(self):
        if self.list_of_settings["memory"]["recents"] is None:
            self.list_of_settings["memory"]["recents"] = []

        self.clear_deleted_recent()
        return self.list_of_settings["memory"]["recents"]

    def add_recent(self, added):
        while added in self.list_of_settings["memory"]["recents"]:
            self.list_of_settings["memory"]["recents"].remove(added)

        self.list_of_settings["memory"]["recents"] = [
            added] + self.list_of_settings["memory"]["recents"]
        if len(self.list_of_settings["memory"]["recents"]) > 10:
            self.list_of_settings["memory"]["recents"] = self.list_of_settings["memory"]["recents"][:10]

        self.store()

    def clear_deleted_recent(self):
        recents = self.list_of_settings["memory"]["recents"]
        need_store = False

        for r in recents:
            if not os.path.exists(r) or not os.path.isfile(r):
                self.list_of_settings["memory"]["recents"].remove(r)
                need_store = True

        if need_store:
            self.store()
