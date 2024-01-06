import logging
import os
import sys
from datetime import timedelta

import requests
import unicodedata
import xbmc
import xbmcgui
import xbmcplugin
from cached import memory_cached

from lib.api.flix.kodi import ADDON_ID, ADDON_DATA, ADDON_VERSION
from lib.api.flix.utils import assure_unicode
from lib.opensubtitles.rest import OpenSubtitles, SearchPayload, DownloadRequest
from lib.opensubtitles.utils import calculate_hash
from lib.settings import get_os_username, get_os_password, get_os_folder

try:
    from urllib.parse import parse_qs, urlencode
except ImportError:
    # noinspection PyUnresolvedReferences
    from urlparse import parse_qs
    # noinspection PyUnresolvedReferences
    from urllib import urlencode


def get_from_params(params, key, **kwargs):
    try:
        data = params[key]
        if data and len(data) > 0:
            return data[0]
    except KeyError:
        pass
    if "default" in kwargs:
        return kwargs["default"]
    raise AttributeError("No attribute '{}' provided")


def normalize_string(s):
    return unicodedata.normalize("NFKD", assure_unicode(s))


def get_language_code(language_mame):
    logging.debug("Converting language '%s' to code", language_mame)
    for prefix, code in (("English", "en"), ("French", "fr"), ("Spanish", "es")):
        if language_mame.startswith(prefix):
            return code

    try:
        return {
            "Chinese": "zh-cn",
            "Chinese (Simple)": "zh-cn",
            "Chinese (Traditional)": "zh-tw",
            "Portuguese": "pt-pt",
            "Portuguese (Brazil)": "pt-br",
        }[language_mame]
    except KeyError:
        return xbmc.convertLanguage(language_mame, xbmc.ISO_639_1)


def get_language_flag(language):
    language = language.lower()
    try:
        return {"pt-pt": "pt", "pt-br": "pb"}[language]
    except KeyError:
        return language.split("-", maxsplit=1)[0]


class SubtitlesService(object):
    def __init__(self, handle=None, params=None):
        self._subtitles_dir = get_os_folder()
        if not self._subtitles_dir or not os.path.isdir(self._subtitles_dir):
            self._subtitles_dir = os.path.join(ADDON_DATA, "subtitles")
            if not os.path.exists(self._subtitles_dir):
                os.makedirs(self._subtitles_dir)

        self._handle = handle or int(sys.argv[1])
        self._params = params or parse_qs(sys.argv[2].lstrip("?"))
        self._api = OpenSubtitles(ADDON_ID, ADDON_VERSION)
        self._api.login(get_os_username(), get_os_password())

    def _add_result(self, result):
        list_item = xbmcgui.ListItem(label=result.language, label2=result.release)
        list_item.setArt({
            "icon": str(int(round(float(result.ratings) / 2))),
            "thumb": get_language_flag(result.language),
        })
        list_item.setProperty("sync", "true" if result.moviehash_match else "false")
        list_item.setProperty("hearing_imp", "true" if result.hearing_impaired else "false")

        url = "plugin://{}/?{}".format(ADDON_ID, urlencode(dict(
            action="download", file_id=result.files[0].file_id)))

        xbmcplugin.addDirectoryItem(self._handle, url, list_item)

    def _get_query_languages(self):
        return [get_language_code(language) for language in self._get_param("languages").split(",")]

    def _get_preferred_language(self):
        return get_language_code(self._get_param("preferredlanguage", default=None))

    def _get_param(self, key, **kwargs):
        return get_from_params(self._params, key, **kwargs)

    @memory_cached(timedelta(minutes=30), instance_method=True)
    def _search_subtitles(self, payload):
        return self._api.search_subtitles(payload)

    def search(self, languages, search_string=None, preferred_language=None):
        logging.debug("Searching subtitle for languages %s and preferred language %s", languages, preferred_language)
        if search_string is None:
            path = xbmc.Player().getPlayingFile()
            payload = SearchPayload()

            # Search by hash
            file_hash = calculate_hash(path)
            if file_hash:
                payload.hash = file_hash

            # Search by file name
            # if os.path.isfile(path):
            #    payload.query = os.path.splitext(os.path.basename(path))[0]

            # Search with info labels
            tv_show_title = normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
            imdb_number = xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
            if tv_show_title:
                # Assuming its a tv show
                payload.query = tv_show_title
                season = xbmc.getInfoLabel("VideoPlayer.Season")
                episode = xbmc.getInfoLabel("VideoPlayer.Episode")
                if episode and season:
                    payload.season = season
                    payload.episode = episode
                    if imdb_number and imdb_number[2:].isdigit():
                        payload.imdb_id = int(imdb_number[2:])
            else:
                # Assuming it's a movie
                title = normalize_string(
                    xbmc.getInfoLabel("VideoPlayer.OriginalTitle") or xbmc.getInfoLabel("VideoPlayer.Title"))
                year = xbmc.getInfoLabel("VideoPlayer.Year")
                if not year:
                    title, year = xbmc.getCleanMovieTitle(title)
                if year and year.isdigit():
                    payload.year = int(year)
                payload.query = title
                if imdb_number and imdb_number[2:].isdigit():
                    payload.imdb_id = int(imdb_number[2:])
        else:
            payload = SearchPayload(query=search_string)

        payload.languages = ",".join(languages)
        logging.debug("Search payload: %s", payload)
        results = self._search_subtitles(payload)
        results.sort(
            key=lambda r: (r.moviehash_match, r.ratings, r.language.lower() == preferred_language), reverse=True)

        for result in results:
            try:
                self._add_result(result)
            except Exception as e:
                logging.error(e, exc_info=True)

    def download(self, file_id):
        result = self._api.download_subtitle(DownloadRequest(file_id=file_id))
        path = os.path.join(self._subtitles_dir, result.file_name)

        r = requests.get(result.link)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)

        xbmcplugin.addDirectoryItem(self._handle, path, xbmcgui.ListItem(label=result.file_name))

    def run(self):
        succeeded = True
        try:
            action = self._get_param("action")
            if action == "search":
                self.search(self._get_query_languages(), preferred_language=self._get_preferred_language())
            elif action == "manualsearch":
                self.search(
                    self._get_query_languages(), self._get_param("searchstring"),
                    preferred_language=self._get_preferred_language())
            elif action == "download":
                self.download(int(self._get_param("file_id")))
            else:
                succeeded = False
                logging.error("Unknown action '%s'", action)
        except AttributeError as e:
            logging.error(e)
            succeeded = False

        xbmcplugin.endOfDirectory(self._handle, succeeded)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._api.logout()
        return False
