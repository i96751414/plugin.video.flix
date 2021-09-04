"""
Module `provider` provides the core logic behind providers.
"""

import base64
import json
import logging
import sys
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

from .kodi import ADDON_ID, ADDON_NAME, get_installed_addons, notify_all, set_logger, run_script
from .utils import bytes_to_str, str_to_bytes

__all__ = ["ProviderResult", "Provider"]


def get_providers():
    return [p_id for p_id, _ in get_installed_addons(addon_type="xbmc.python.script", enabled=True)
            if p_id.startswith("script.flix.") and p_id != ADDON_ID]


def send_to_providers(providers, method, *args, **kwargs):
    data = {}
    if args:
        data["args"] = args
    if kwargs:
        data["kwargs"] = kwargs
    data_b64 = bytes_to_str(base64.b64encode(str_to_bytes(json.dumps(data))))
    for provider in providers:
        run_script(provider, ADDON_ID, method, data_b64)


def send_to_provider(provider, method, *args, **kwargs):
    send_to_providers((provider,), method, *args, **kwargs)


def _setter_and_getter(attribute):
    def setter(self, value):
        self[attribute] = value

    def getter(self):
        return self.get(attribute)

    setter.__doc__ = "Set {}".format(attribute)
    getter.__doc__ = "Get {}".format(attribute)
    return setter, property(getter)


class ProviderResult(dict):
    # noinspection PyUnresolvedReferences
    """
    The ProviderResult is the only type allowed to be returned by :func:`Provider.search`,
    :func:`Provider.search_movie` and :func:`Provider.search_episode` methods.

    :keyword label: The result label.
    :type label: str, optional
    :keyword label2: The result label2.
    :type label2: str, optional
    :keyword icon: The result icon. If not set, the fallback icon will be used.
    :type icon: str, optional
    :keyword url: The result url. If not set, then `provider_data` must be set, otherwise the result is discarded.
    :type url: str, optional
    :keyword provider_data: Data to be sent to provider when :func:`Provider.resolve` is called.
    :type provider_data: any, optional

    Example::

        # Start by creating the result with some values
        result = ProviderResult(
            label="label",
            label2="label2",
            icon="foo/icon.png",
            url="http://foo.bar/video.mp4",
        )

        # We can then modify values
        result.set_label2("new label2")
    """

    set_label, label = _setter_and_getter("label")
    set_label2, label2 = _setter_and_getter("label2")
    set_icon, icon = _setter_and_getter("icon")
    set_url, url = _setter_and_getter("url")
    set_provider_data, provider_data = _setter_and_getter("provider_data")


class Provider(object):
    """
    This is where all the logic behind a provider must be implemented. It has methods which
    are required to be implemented by it's subclass (:func:`search`, :func:`search_movie` and
    :func:`search_episode`) and also optional methods (:func:`resolve`). The provider can then
    be registered by using :func:`register`.

    Example::

        class CustomProvider(Provider):
            def search(self, query):
                # Implementation here
                return []

            def search_movie(self, tmdb_id, title, titles, year=None):
                return self.search("{:s} {:d}".format(title, year) if year else title)

            def search_show(self, tmdb_id, show_title, titles, year=None):
                return self.search("{:s} {:d}".format(show_title, year) if year else show_title)

            def search_season(self, tmdb_id, show_title, season_number, titles):
                return self.search("{:s} S{:02d}".format(show_title, season_number))

            def search_episode(self, tmdb_id, show_title, season_number, episode_number, titles):
                return self.search("{:s} S{:02d}E{:02d}".format(show_title, season_number, episode_number))

        CustomProvider().register()
    """

    def __init__(self):
        self.logger = set_logger("provider")
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

    def search_movie(self, tmdb_id, title, titles, year=None):
        """
        Search a movie.

        :param tmdb_id: The movie TMDB id.
        :type tmdb_id: str
        :param title: The movie title.
        :type title: str
        :param titles: Dictionary containing key-pairs of country (ISO-3166-1 lowercase) and title, respectively.
        :type titles: dict[str, str]
        :param year: The movie release year. This is optional, as some movies don't have a release date attribute.
        :type year: int, optional
        :return: List of search results.
        :rtype: list[ProviderResult]
        """
        raise NotImplementedError("'search_movie' method must be implemented")

    def search_show(self, tmdb_id, show_title, titles, year=None):
        """
        Search a tv show.

        :param tmdb_id: The tv show TMDB id.
        :type tmdb_id: str
        :param show_title: The show title.
        :type show_title: str
        :param titles: Dictionary containing key-pairs of country (ISO-3166-1 lowercase) and title, respectively.
        :type titles: dict[str, str]
        :param year: The show first air year. This is optional, as some shows don't have this attribute.
        :type year: int, optional
        :return: List of search results.
        :rtype: list[ProviderResult]
        """
        raise NotImplementedError("'search_show' method must be implemented")

    def search_season(self, tmdb_id, show_title, season_number, titles):
        """
        Search a season.

        :param tmdb_id: The tv show TMDB id.
        :type tmdb_id: str
        :param show_title: The show title.
        :type show_title: str
        :param season_number: The season number.
        :type season_number: int
        :param titles: Dictionary containing key-pairs of country (ISO-3166-1 lowercase) and title, respectively.
        :type titles: dict[str, str]
        :return: List of search results.
        :rtype: list[ProviderResult]
        """
        raise NotImplementedError("'search_season' method must be implemented")

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
        :param titles: Dictionary containing key-pairs of country (ISO-3166-1 lowercase) and title, respectively.
        :type titles: dict[str, str]
        :return: List of search results.
        :rtype: list[ProviderResult]
        """
        raise NotImplementedError("'search_episode' method must be implemented")

    def resolve(self, provider_data):
        """
        Resolve method is only called in cases where the provider has not set (:attr:`ProviderResult.url`)
        but did set the (:attr:`ProviderResult.provider_data`) parameter (which will be used here).
        This may be useful in cases where the `url` can't be obtained right away.

        :param provider_data: `provided_data` from result (:class:`ProviderResult`) .
        :type provider_data: any
        :return: The url to be played.
        :rtype: str
        """
        raise NotImplementedError("'resolve' method must be implemented")

    def ping(self):
        """
        Ping method for checking the communication with a provider.

        :return: The provider id.
        :rtype: str
        """
        self.logger.debug("Ping method called")
        return ADDON_ID

    def register(self):
        """
        Register the provider for execution.
        """
        self.logger.debug("Running with args: %s", sys.argv)
        if len(sys.argv) != 4:
            self.logger.error("Expecting 4 arguments. Got %s", sys.argv)
            xbmcgui.Dialog().notification(ADDON_NAME, xbmcaddon.Addon("plugin.video.flix").getLocalizedString(30109))
            return

        _, sender, method, data_b64 = sys.argv
        if method in self._methods:
            try:
                data = json.loads(base64.b64decode(data_b64))
                value = self._methods[method](*data.get("args", []), **data.get("kwargs", {}))
            except Exception as e:
                self.logger.error("Failed running method '%s' with data '%s': %s", method, data_b64, e, exc_info=True)
                value = None
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
        while not (self.is_complete() or 0 < timeout < time.time() - self._start_time or self.waitForAbort(0.2)):
            pass

    def get_missing(self):
        with self._lock:
            return [k for k, v in self._waiting.items() if v]

    @property
    def data(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wait()
        missing = self.get_missing()
        if missing:
            logging.warning("Provider(s) timed out: %s", ", ".join(missing))
        return False
