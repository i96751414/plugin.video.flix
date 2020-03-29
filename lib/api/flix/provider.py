import base64
import json
import logging
import sys
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

from .kodi import ADDON_ID, ADDON_NAME, get_installed_addons, notify_all, set_logger
from .utils import bytes_to_str

__all__ = ["ProviderResult", "Provider"]


def get_providers():
    return [p_id for p_id, _ in get_installed_addons(addon_type="xbmc.python.script", enabled=True)
            if p_id.startswith("script.flix.")]


def send_to_providers(providers, method, *args, **kwargs):
    data = {}
    if args:
        data["args"] = args
    if kwargs:
        data["kwargs"] = kwargs
    data_b64 = bytes_to_str(base64.b64encode(json.dumps(data)))
    for provider in providers:
        xbmc.executebuiltin("RunScript({}, {}, {}, {})".format(provider, ADDON_ID, method, data_b64))


def send_to_provider(provider, method, *args, **kwargs):
    send_to_providers((provider,), method, *args, **kwargs)


def _setter_and_getter(attribute):
    def setter(self, value):
        self[attribute] = value

    def getter(self):
        return self.get(attribute)

    return setter, property(getter)


class ProviderResult(dict):
    set_label, label = _setter_and_getter("label")
    set_label2, label2 = _setter_and_getter("label2")
    set_icon, icon = _setter_and_getter("icon")
    set_url, url = _setter_and_getter("url")
    set_provider_data, provider_data = _setter_and_getter("provider_data")


class Provider(object):
    def __init__(self):
        self.logger = set_logger("provider", level=logging.INFO)
        self._methods = {}
        for name in dir(self):
            if not name.startswith("_") and name != "register":
                attr = getattr(self, name)
                if callable(attr):
                    self._methods[name] = attr

    def search(self, query):
        """
        Perform a raw search.

        :param query: The query for performing the search.
        :type query: str
        :return: List of search results.
        :rtype: list[ProviderResult]
        """
        raise NotImplementedError("'search' method must be implemented")

    def search_movie(self, tmdb_id, title, year, titles):
        """
        Search a movie.

        :param tmdb_id: The movie TMDB id.
        :type tmdb_id: str
        :param title: The movie title.
        :type title: str
        :param year: The movie release year. This is optional, as some movies don't have a release date attribute.
        :type year: int or None
        :param titles: Dictionary containing key-pairs of country and title, respectively.
        :type titles: dict[str, str]
        :return: List of search results.
        :rtype: list[ProviderResult]
        """
        raise NotImplementedError("'search_movie' method must be implemented")

    def search_episode(self, tmdb_id, show_title, season_number, episode_number, titles):
        """
        Search an episode.

        :param tmdb_id: The tv show TMDB id.
        :type tmdb_id: str
        :param show_title: The show title.
        :type show_title: str
        :param season_number: The season number.
        :type season_number: int
        :param episode_number: The episode number.
        :type episode_number: int
        :param titles: Dictionary containing key-pairs of country and title, respectively.
        :type titles: dict[str, str]
        :return: List of search results.
        :rtype: list[ProviderResult]
        """
        raise NotImplementedError("'search_episode' method must be implemented")

    def resolve(self, handle, item, provider_data):
        """
        Resolve method is only called in cases where the provider has not set the `url` parameter of
        :class:`ProviderResult` but did set the `provider_data` parameter (which will be used here).
        This may be useful in cases where the `url` can't be obtained right away.

        In cases where no url is returned, it is expected a call to :func:`xbmcplugin.setResolvedUrl`
        from this method, otherwise the player will not start.

        :param handle: The calling plugin handle - to be used in :func:`xbmcplugin.setResolvedUrl`, if needed.
        :type handle: int
        :param item: Dictionary containing :class:`xbmcgui.ListItem` information ('title', 'info' and 'art').
        :type item: dict
        :param provider_data: `provided_data` from result (:class:`ProviderResult`) .
        :type provider_data: any
        :return: The url to be played. If None, it is assumed the script will invoke the player by itself.
        :rtype: str or None
        """
        raise NotImplementedError("'resolve' method must be implemented")

    @staticmethod
    def ping():
        """
        Ping method for checking the communication with a provider.
        :return: The provider id.
        :rtype: str
        """
        return ADDON_ID

    def register(self):
        self.logger.debug("Running with args: %s", sys.argv)
        if len(sys.argv) != 4:
            self.logger.error("Expecting 4 arguments. Got %s", sys.argv)
            xbmcgui.Dialog().notification(ADDON_NAME, xbmcaddon.Addon("plugin.video.flix").getLocalizedString(30109))
            return

        _, sender, method, data_b64 = sys.argv
        if method in self._methods:
            data = json.loads(base64.b64decode(data_b64))
            value = self._methods[method](*data.get("args", []), **data.get("kwargs", {}))
            if not notify_all(ADDON_ID, "{}.{}".format(sender, method), value):
                self.logger.error("Failed sending provider data")
        else:
            self.logger.error("Unknown method provided '%s'. Expecting one of %s", method, self._methods.keys())
            raise ValueError("Unknown method provided")


class ProviderListener(xbmc.Monitor):
    def __init__(self, providers, method, timeout=10):
        super(ProviderListener, self).__init__()
        self._waiting = {i: True for i in providers}
        self._method = "Other.{}.{}".format(ADDON_ID, method)
        self._timeout = timeout
        self._data = {}
        self._lock = threading.Lock()
        self._start_time = time.time()

    def onNotification(self, sender, method, data):
        logging.debug("Received notification with sender=%s, method=%s, data=%s", sender, method, data)
        with self._lock:
            if method == self._method and self._waiting.get(sender, False):
                try:
                    self._data[sender] = json.loads(data)
                except Exception as e:
                    logging.error("Unable to get data from sender '%s': %s", sender, e)
                else:
                    self._waiting[sender] = False
                    self.on_receive(sender)

    def on_receive(self, sender):
        pass

    def is_complete(self):
        with self._lock:
            return not any(self._waiting.values())

    def wait(self, **kwargs):
        if kwargs.get("reset"):
            self._start_time = time.time()
        timeout = kwargs.get("timeout", self._timeout)
        while not (self.is_complete() or self.abortRequested() or 0 < timeout < time.time() - self._start_time):
            xbmc.sleep(200)

    @property
    def data(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wait()
        return False
