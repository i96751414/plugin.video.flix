# noinspection PyUnresolvedReferences
"""
Module `kodi` provides Kodi utilities.

.. data:: ADDON

    The addon instance (:class:`xbmcaddon.Addon`).

.. data:: ADDON_NAME

    The addon name (:class:`str`).

.. data:: ADDON_ID

    The addon id (:class:`str`).

.. data:: ADDON_PATH

    The addon path (:class:`str`).

.. data:: ADDON_ICON

    The addon icon (:class:`str`).

.. data:: ADDON_DATA

    The addon data path (:class:`str`).

.. function:: set_setting(id, value)

    Set a setting.

    :param id: id of the setting that the module needs to set.
    :type id: str
    :param value: value of the setting.
    :type value: str

.. function:: get_setting(id)

    Get a setting.

    :param id: id of the setting that the module needs to access.
    :type id: str

.. function:: open_settings

    Open settings window.

.. function:: translate(id)

    Get a localized string.

    :param id: id of string to localize.
    :type id: int
    :return: Localized string.
    :rtype: str

.. function:: translate_path(path)

    Translates the provided path.

    :param path: path to translate.
    :type path: str
    :return: Translated path.
    :rtype: str

"""

import json
import logging

import xbmc
import xbmcaddon
import xbmcgui

from .utils import assure_unicode, assure_str, PY3

ADDON = xbmcaddon.Addon()
if PY3:
    from xbmcvfs import translatePath

    translate = ADDON.getLocalizedString
else:
    from xbmc import translatePath

    def translate(*args, **kwargs):
        return ADDON.getLocalizedString(*args, **kwargs).encode("utf-8")

translate_path = translatePath
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_VERSION = ADDON.getAddonInfo("version")
ADDON_PATH = assure_unicode(ADDON.getAddonInfo("path"))
ADDON_ICON = assure_unicode(ADDON.getAddonInfo("icon"))
ADDON_DATA = assure_unicode(translate_path(ADDON.getAddonInfo("profile")))

set_setting = ADDON.setSetting
get_setting = ADDON.getSetting
open_settings = ADDON.openSettings

# Windows IDs - https://kodi.wiki/view/Window_IDs
WINDOW_HOME = 10000

iso_639_1_languages = {
    "Chinese": "zh", "English": "en", "French": "fr", "Hindi": "hi", "Mongolian": "mn",
    "Persian": "fa", "Portuguese": "pt", "Serbian": "sr", "Spanish": "es", "Tamil": "ta",
}


def get_language_iso_639_1(default="en", region=False):
    """
    Get the active language as defined in ISO 639-1.

    :param default: fallback language if unable to get language.
    :param region: append the region delimited by "-" to the language.
    :type default: str
    """
    language = xbmc.getLanguage(xbmc.ISO_639_1, region=region)
    if not language or (region and language.startswith("-")):
        name = xbmc.getLanguage(xbmc.ENGLISH_NAME)
        for k in iso_639_1_languages:
            if name.startswith(k):
                language = iso_639_1_languages[k] + language
                break
        else:
            language = default

    return language


def notification(message, heading=ADDON_NAME, icon=ADDON_ICON, time=5000, sound=True):
    """
    Show a Notification alert.

    :param message: dialog message.
    :type message: str
    :param heading: dialog heading (default ADDON_NAME).
    :type heading: str
    :param icon: icon to use. (default ADDON_ICON)
    :type icon: str
    :param time: time in milliseconds (default 5000)
    :type time: int
    :param sound: play notification sound (default True)
    :type sound: bool
    """
    xbmcgui.Dialog().notification(heading, message, icon, time, sound)


def get_current_view_id():
    """
    Gets the current view ID.

    :return: The current view ID.
    :rtype: int
    """
    return xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId()


def set_view_mode(view_id):
    """
    Sets the current view mode.

    :param view_id: The view ID.
    :type view_id: int
    """
    xbmc.executebuiltin("Container.SetViewMode({})".format(view_id))


def get_boolean_setting(setting):
    """
    Get setting as boolean.

    :param setting: The setting id.
    :type setting: str
    :return: The setting value.
    :rtype: bool
    """
    return get_setting(setting) == "true"


def get_int_setting(setting):
    """
    Get setting as integer.

    :param setting: The setting id.
    :type setting: str
    :return: The setting value.
    :rtype: int
    """
    return int(get_setting(setting))


def get_float_setting(setting):
    """
    Get setting as float.

    :param setting: The setting id.
    :type setting: str
    :return: The setting value.
    :rtype: float
    """
    return float(get_setting(setting))


def set_boolean_setting(setting, value):
    """
    Set boolean setting.

    :param setting: The setting id.
    :type setting: str
    :param value: The setting value.
    :type value: bool
    """
    set_setting(setting, "true" if value else "false")


def set_any_setting(setting, value):
    """
    Set a setting.

    :param setting: The setting id.
    :type setting: str
    :param value: The setting value.
    """
    if isinstance(value, bool):
        set_boolean_setting(setting, value)
    else:
        set_setting(setting, str(value))


def execute_json_rpc(method, rpc_version="2.0", rpc_id=1, **params):
    """
    Execute a JSON-RPC call.

    :param method: The JSON-RPC method, as specified in https://kodi.wiki/view/JSON-RPC_API.
    :type method: str
    :param rpc_version: The JSON-RPC version (default 2.0).
    :type rpc_version: str
    :param rpc_id: The JSON-RPC call id (default 1).
    :type rpc_id: int
    :param params: The JSON-RPC call parameters.
    :return: The call result.
    """
    return json.loads(xbmc.executeJSONRPC(json.dumps(dict(
        jsonrpc=rpc_version, method=method, params=params, id=rpc_id))))


def notify_all(sender, message, data=None):
    """
    Notify all other connected clients.

    :param sender: The notification sender.
    :type sender: str
    :param message: The notification message.
    :type message: str
    :param data: Data to send on the notification (optional).
    :return: The call outcome.
    :rtype: bool
    """
    # We could use NotifyAll(sender, data [, json]) builtin as well.
    params = {"sender": sender, "message": message}
    if data is not None:
        params["data"] = data
    return execute_json_rpc("JSONRPC.NotifyAll", **params).get("result") == "OK"


def get_installed_addons(addon_type="", content="unknown", enabled="all"):
    """
    Get installed addons.

    :param addon_type: Filter by addon type (optional).
    :type addon_type: str
    :param content: Filter by content type (optional).
    :type content: str
    :param enabled: Filter by enabled addons only (optional).
    :type enabled: str or bool
    :return: List of installed addons.
    :rtype: list[tuple[str, str]]
    """
    data = execute_json_rpc("Addons.GetAddons", type=addon_type, content=content, enabled=enabled)
    addons = data["result"].get("addons")
    return [(a["addonid"], a["type"]) for a in addons] if addons else []


def container_refresh():
    """
    Refresh the current container.
    """
    xbmc.executebuiltin("Container.Refresh")


def container_update(path):
    """
    Update the container to the specified path.

    :param path: The path where to update.
    :type path: str
    """
    xbmc.executebuiltin("Container.Update({})".format(path))


def run_plugin(plugin):
    """
    Runs the plugin. Full path must be specified. Does not work for folder plugins.

    :param plugin: Full path of the plugin.
    :type plugin: str
    """
    xbmc.executebuiltin("RunPlugin({})".format(plugin))


def run_script(script, *args):
    """
    Runs the python script. You must specify the add-on id of the script.
    As of 2007/02/24, all extra parameters are passed to the script as arguments and
    can be accessed by python using sys.argv.

    :param script: The script addon-id.
    :type script: str
    :param args: The extra parameters to be passed.
    :type args: str
    """
    xbmc.executebuiltin("RunScript({})".format(",".join((script,) + args)))


def update_library(database, path=None):
    """
    Takes either "video" or "music" as a parameter to begin updating the corresponding database.
    For "video" you can additionally specify a specific path to be scanned.

    :param database: The database type.
    :type database: str
    :param path: The path to be scanned.
    :type path: str
    """
    args = [database]
    if path:
        args.append(path)
    xbmc.executebuiltin("UpdateLibrary({})".format(",".join(args)))


def clean_library(database):
    """
    This function will perform a number of 'cleanup' tasks on your video database and can be run
    if you have moved, deleted or renamed files.
    Takes either "video" or "music" as a parameter to begin cleaning the corresponding database.

    :param database: The database type.
    :type database: str
    """
    xbmc.executebuiltin("CleanLibrary({})".format(database))


def busy_dialog():
    """
    Activate busy dialog window.
    """
    xbmc.executebuiltin("ActivateWindow(busydialog)")


def close_busy_dialog():
    """
    Close busy dialog window.
    """
    xbmc.executebuiltin("Dialog.Close(busydialog)")


def set_property(key, value):
    """
    Set a property on the current Kodi instance.

    :param key: The property key.
    :type key: str
    :param value: The property value.
    :type value: str
    """
    xbmcgui.Window(WINDOW_HOME).setProperty(key, value)


def get_property(key):
    """
    Get a property of the current Kodi instance.

    :param key: The property key.
    :type key: str
    :return: The property value.
    :rtype: str
    """
    return xbmcgui.Window(WINDOW_HOME).getProperty(key)


class Busy(object):
    """
    Context manager for activating the busy dialog window while processing,
    closing it afterwards.
    """

    def __enter__(self):
        busy_dialog()

    def __exit__(self, exc_type, exc_val, exc_tb):
        close_busy_dialog()


class Progress(object):
    """
    Iterable wrapper for showing and automatically update/close a progress dialog.

    :param iterable: The iterable to be wrapped.
    :param length: The iterable length (optional).
    :param impl: The dialog implementation to use (default :class:`xbmcgui.DialogProgressBG`).
    :param percent_range: The percentage range of this iterable (useful when there are multiple iterables).
    :param percent_offset: The percentage offset of this iterable (useful when there are multiple iterables).
    :param kwargs: Arguments to pass to `dialog.create()` method.
    """

    def __init__(self, iterable, length=None, impl=xbmcgui.DialogProgressBG, percent_range=100, percent_offset=0,
                 **kwargs):
        self._iterable = iterable
        if length is None:
            if not hasattr(self._iterable, "__len__"):
                self._iterable = list(self._iterable)
            self._length = len(self._iterable)
        else:
            self._length = length
        self._impl = impl
        self._percent_range = percent_range
        self._percent_offset = percent_offset
        self._kwargs = kwargs
        self._dialog = None

    def __iter__(self):
        if self._dialog is not None:
            raise ValueError("dialog already created")

        self._dialog = self._impl()
        self._dialog.create(**self._kwargs)

        try:
            for i, obj in enumerate(self._iterable):
                self._dialog.update(int(self._percent_offset + self._percent_range * (i + 1) / self._length))
                yield obj
        finally:
            self.close()

    def __del__(self):
        self.close()

    def close(self):
        """
        Close the progress dialog.
        """
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
        xbmc.log(assure_str(self.format(record)), self.levels[record.levelno])

    def flush(self):
        pass


def set_logger(name=None, level=logging.NOTSET):
    """
    Set a :mod:`logging` logger using :func:`xbmc.log` in the background.

    :param name: The logger name (optional).
    :type name: str
    :param level: Default logging level (default `logging.INFO`).
    :type level: int
    :return: The logger.
    :rtype: logging.Logger
    """
    logger = logging.getLogger(name)
    logger.handlers = [KodiLogHandler()]
    logger.setLevel(level)
    return logger
