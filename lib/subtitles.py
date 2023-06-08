import gzip
import io
import logging
import os
import sys
import unicodedata
from datetime import timedelta

import requests
import xbmc
import xbmcgui
import xbmcplugin
from cached import memory_cached

from lib.api.flix.kodi import ADDON_ID, ADDON_DATA, get_language_iso_639_1, convert_language_iso_639_2
from lib.api.flix.utils import assure_str, assure_unicode
from lib.opensubtitles.utils import calculate_hash
from lib.opensubtitles.xmlrpc import OpenSubtitles, SearchPayload
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


class SubtitlesService(object):
    def __init__(self, handle=None, params=None):
        self._subtitles_dir = get_os_folder()
        if not self._subtitles_dir or not os.path.isdir(self._subtitles_dir):
            self._subtitles_dir = os.path.join(ADDON_DATA, "subtitles")
            if not os.path.exists(self._subtitles_dir):
                os.makedirs(self._subtitles_dir)

        self._handle = handle or int(sys.argv[1])
        self._params = params or parse_qs(sys.argv[2].lstrip("?"))
        self._api = OpenSubtitles(language=get_language_iso_639_1(), user_agent="XBMC_Subtitles_Login_v5.0.16")
        self._api.login(get_os_username(), get_os_password())

    def _add_result(self, result):
        list_item = xbmcgui.ListItem(label=result.language_name, label2=result.sub_file_name)
        list_item.setArt({"icon": str(int(round(float(result.sub_rating) / 2))), "thumb": result.iso_639})
        list_item.setProperty("sync", "true" if result.matched_by == "moviehash" else "false")
        list_item.setProperty("hearing_imp", "true" if result.sub_hearing_impaired == "1" else "false")

        url = "plugin://{}/?{}".format(ADDON_ID, urlencode(dict(
            action="download", name=assure_str(result.sub_file_name), url=result.sub_download_link)))

        xbmcplugin.addDirectoryItem(self._handle, url, list_item)

    def _get_query_languages(self):
        return ",".join([convert_language_iso_639_2(language) for language in self._get_param("languages").split(",")])

    def _get_param(self, key):
        return get_from_params(self._params, key)

    @memory_cached(timedelta(minutes=30), instance_method=True)
    def _search_subtitles(self, payload):
        return self._api.search_subtitles(payload)

    def search(self, languages, search_string=None):
        path = xbmc.Player().getPlayingFile()
        if search_string is None:
            payload = []
            # Start by searching by hash
            file_hash = calculate_hash(path)
            if file_hash:
                payload.append(SearchPayload(hash=file_hash))
            # Search by file name
            if os.path.isfile(path):
                payload.append(SearchPayload(query=os.path.splitext(os.path.basename(path))[0]))
            # Search with info labels
            tv_show_title = normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
            imdb_number = xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
            if tv_show_title:
                # Assuming its a tv show
                season = xbmc.getInfoLabel("VideoPlayer.Season")
                episode = xbmc.getInfoLabel("VideoPlayer.Episode")
                if episode and season:
                    payload.append(SearchPayload(query="{} S{:0>2}E{:0>2}".format(tv_show_title, season, episode)))
                    payload.append(SearchPayload(query=tv_show_title, season=season, episode=episode))
                    if imdb_number:
                        payload.append(SearchPayload(imdb_id=imdb_number[2:], season=season, episode=episode))
            else:
                # Assuming its a movie
                title = normalize_string(
                    xbmc.getInfoLabel("VideoPlayer.OriginalTitle") or xbmc.getInfoLabel("VideoPlayer.Title"))
                year = xbmc.getInfoLabel("VideoPlayer.Year")
                if not year:
                    title, year = xbmc.getCleanMovieTitle(title)
                if year:
                    payload.append(SearchPayload(query=title + " " + year))
                payload.append(SearchPayload(query=title))
                if imdb_number:
                    payload.append(SearchPayload(imdb_id=imdb_number[2:]))
        else:
            payload = [SearchPayload(query=search_string)]

        for search_payload in payload:
            search_payload.languages = languages

        logging.debug("Search payload: %s", payload)
        results = self._search_subtitles(payload)
        for result in results:
            try:
                self._add_result(result)
            except Exception as e:
                logging.error(e, exc_info=True)

    def download(self, name, url):
        path = os.path.join(self._subtitles_dir, name)
        content = gzip.GzipFile(fileobj=io.BytesIO(requests.get(url).content)).read()
        with open(path, "wb") as f:
            f.write(content)

        xbmcplugin.addDirectoryItem(self._handle, path, xbmcgui.ListItem(label=name))

    def run(self):
        succeeded = True
        try:
            action = self._get_param("action")
            if action == "search":
                self.search(self._get_query_languages())
            elif action == "manualsearch":
                self.search(self._get_query_languages(), self._get_param("searchstring"))
            elif action == "download":
                self.download(self._get_param("name"), self._get_param("url"))
            else:
                succeeded = False
                logging.error("Unknown action '%s'", action)
        except AttributeError as e:
            logging.error(e)
            succeeded = False

        xbmcplugin.endOfDirectory(self._handle, succeeded)
