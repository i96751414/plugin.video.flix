import json
import logging

import xbmc
import xbmcaddon
import xbmcgui

from .utils import str_to_unicode, PY3

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_PATH = str_to_unicode(ADDON.getAddonInfo("path"))
ADDON_ICON = str_to_unicode(ADDON.getAddonInfo("icon"))
ADDON_DATA = str_to_unicode(xbmc.translatePath(ADDON.getAddonInfo("profile")))

set_setting = ADDON.setSetting
get_setting = ADDON.getSetting
open_settings = ADDON.openSettings

if PY3:
    translate = ADDON.getLocalizedString
else:
    def translate(*args, **kwargs):
        return ADDON.getLocalizedString(*args, **kwargs).encode("utf-8")


def notification(message, heading=ADDON_NAME, icon=ADDON_ICON, time=5000, sound=True):
    xbmcgui.Dialog().notification(heading, message, icon, time, sound)


def get_boolean_setting(setting):
    return get_setting(setting) == "true"


def get_int_setting(setting):
    return int(get_setting(setting))


def get_float_setting(setting):
    return float(get_setting(setting))


def set_boolean_setting(setting, value):
    set_setting(setting, "true" if value else "false")


def execute_json_rpc(method, rpc_version="2.0", rpc_id=1, **params):
    return json.loads(xbmc.executeJSONRPC(json.dumps(dict(
        jsonrpc=rpc_version, method=method, params=params, id=rpc_id))))


def notify_all(sender, message, data=None):
    # We could use NotifyAll(sender, data [, json]) builtin as well.
    params = {"sender": sender, "message": message}
    if data is not None:
        params["data"] = data
    return execute_json_rpc("JSONRPC.NotifyAll", **params).get("result") == "OK"


def get_installed_addons(addon_type="", content="unknown", enabled="all"):
    data = execute_json_rpc("Addons.GetAddons", type=addon_type, content=content, enabled=enabled)
    return [(a["addonid"], a["type"]) for a in data["result"]["addons"]]


def busy_dialog():
    xbmc.executebuiltin("ActivateWindow(busydialog)")


def close_busy_dialog():
    xbmc.executebuiltin("Dialog.Close(busydialog)")


class Busy(object):
    def __enter__(self):
        busy_dialog()

    def __exit__(self, exc_type, exc_val, exc_tb):
        close_busy_dialog()


class Progress(object):
    def __init__(self, iterable, impl=xbmcgui.DialogProgressBG, **kwargs):
        self._iterable = iterable
        self._length = len(iterable)
        self._impl = impl
        self._kwargs = kwargs
        self._dialog = None

    def __iter__(self):
        if self._dialog is not None:
            raise ValueError("dialog already created")
        self._dialog = self._impl()
        self._dialog.create(**self._kwargs)
        for i, obj in enumerate(self._iterable):
            self._dialog.update(int(100 * (i + 1) / self._length))
            yield obj
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self._dialog is not None:
            self._dialog.close()
            self._dialog = None


class KodiLogHandler(logging.StreamHandler):
    levels = {
        logging.CRITICAL: xbmc.LOGFATAL,
        logging.ERROR: xbmc.LOGERROR,
        logging.WARNING: xbmc.LOGWARNING,
        logging.INFO: xbmc.LOGINFO,
        logging.DEBUG: xbmc.LOGDEBUG,
        logging.NOTSET: xbmc.LOGNONE,
    }

    def __init__(self):
        super(KodiLogHandler, self).__init__()
        self.setFormatter(logging.Formatter("[{}] %(message)s".format(ADDON_ID)))

    def emit(self, record):
        xbmc.log(self.format(record), self.levels[record.levelno])

    def flush(self):
        pass


def set_logger(name=None, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.addHandler(KodiLogHandler())
    logger.setLevel(level)
    return logger
