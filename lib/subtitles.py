import logging
import os
import sys
import time
from contextlib import closing
from datetime import timedelta
from shutil import copyfileobj, copy

import requests
import unicodedata
import xbmc
import xbmcgui
import xbmcplugin
from cached import memory_cached

from lib.api.flix.kodi import ADDON_ID, ADDON_VERSION, translate_path
from lib.api.flix.utils import assure_unicode
from lib.opensubtitles.rest import OpenSubtitles, SearchPayload, DownloadRequest
from lib.opensubtitles.utils import calculate_hash
from lib.settings import get_os_username, get_os_password, get_os_folder, store_subtitle

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
        self._handle = handle or int(sys.argv[1])
        self._params = params or parse_qs(sys.argv[2].lstrip("?"))
        self._api = OpenSubtitles(ADDON_ID, ADDON_VERSION)

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
                # Assuming it's a tv show
                payload.query = tv_show_title
                season = xbmc.getInfoLabel("VideoPlayer.Season")
                episode = xbmc.getInfoLabel("VideoPlayer.Episode")
                if episode and season:
                    payload.season = int(season)
                    payload.episode = int(episode)
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
        _, ext = os.path.splitext(result.file_name)
        download_path = temp_path = os.path.join(self._temp_dir, "TempSubtitle." + ext)

        if store_subtitle():
            subtitles_dir = get_os_folder()
            if subtitles_dir and os.path.isdir(subtitles_dir):
                download_path = os.path.join(subtitles_dir, result.file_name)
                logging.debug("Going to download subtitle to %s", download_path)
            else:
                logging.error("Invalid subtitles directory provided: %s", subtitles_dir)

        with closing(requests.get(result.link, stream=True)) as r:
            r.raise_for_status()
            r.raw.decode_content = True
            with open(download_path, "wb") as f:
                copyfileobj(r.raw, f)

        if temp_path is not download_path:
            copy(download_path, temp_path)

        xbmcplugin.addDirectoryItem(self._handle, temp_path, xbmcgui.ListItem(label=result.file_name))

    @property
    def _temp_dir(self):
        temp_dir = os.path.join(translate_path("special://temp"), ADDON_ID)
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        return temp_dir

    def login(self):
        self._api.login(get_os_username(), get_os_password())
        # on /login there is set limit 1 request per 1 second to avoid flooding with wrong credentials
        time.sleep(1)

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
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._api.logout()
        finally:
            self._api.close()
        return False
