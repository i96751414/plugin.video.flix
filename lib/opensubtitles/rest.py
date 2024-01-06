import json

import requests

from lib.api.flix.utils import string_types as string
from lib.opensubtitles.utils import DataStruct

API_KEY = "Hmq0xSCYdI9yG8w7FADtVFDrl2DAjUQA"


class JSONStruct(DataStruct):
    def json(self):
        return json.dumps(self.to_dict())


class SearchPayload(JSONStruct):
    ai_translated = JSONStruct.attr("ai_translated", string)  # exclude, include (default: include)
    episode = JSONStruct.attr("episode_number", int)  # For Tvshows
    foreign_parts_only = JSONStruct.attr("foreign_parts_only", string)  # exclude, include, only (default: include)
    hearing_impaired = JSONStruct.attr("hearing_impaired", string)  # include, exclude, only. (default: include)
    id = JSONStruct.attr("id", int)  # ID of the movie or episode
    imdb_id = JSONStruct.attr("imdb_id", int)  # IMDB ID of the movie or episode
    languages = JSONStruct.attr("languages", string)  # Language code(s), coma separated (en,fr)
    machine_translated = JSONStruct.attr("machine_translated", string)  # exclude, include (default: exclude)
    hash = JSONStruct.attr("moviehash", string)  # hash of the movie
    hash_match = JSONStruct.attr("moviehash_match", string)  # include, only (default: include)
    order_by = JSONStruct.attr("order_by", string)  # Order of the returned results, accept any of above fields
    order_direction = JSONStruct.attr("order_direction", string)  # Order direction of the returned results (asc,desc)
    page = JSONStruct.attr("page", int)  # Results page to display
    parent_feature_id = JSONStruct.attr("parent_feature_id", int)  # For Tvshows
    parent_imdb_id = JSONStruct.attr("parent_imdb_id", int)  # For Tvshows
    parent_tmdb_id = JSONStruct.attr("parent_tmdb_id", int)  # For Tvshows
    query = JSONStruct.attr("query", string)  # file name or text search
    season = JSONStruct.attr("season_number", int)  # For Tvshows
    tmdb_id = JSONStruct.attr("tmdb_id", int)  # TMDB ID of the movie or episode
    trusted_sources = JSONStruct.attr("trusted_sources", string)  # include, only (default: include)
    type = JSONStruct.attr("type", string)  # movie, episode or all, (default: all)
    uploader_id = JSONStruct.attr("uploader_id", int)  # To be used alone - for user uploads listing
    year = JSONStruct.attr("year", int)  # Filter by movie/episode year


class FileAttributes(JSONStruct):
    file_id = JSONStruct.attr("file_id", int)
    cd_number = JSONStruct.attr("cd_number", int)
    file_name = JSONStruct.attr("file_name", string)


class SubtitleAttributes(JSONStruct):
    subtitle_id = JSONStruct.attr("subtitle_id", string)
    language = JSONStruct.attr("language", string, nullable=True)
    hearing_impaired = JSONStruct.attr("hearing_impaired", bool)
    ratings = JSONStruct.attr("ratings", float)
    moviehash_match = JSONStruct.attr("moviehash_match", bool, default=False)
    release = JSONStruct.attr("release", string)
    files = JSONStruct.attr("files", [FileAttributes])


class DownloadRequest(JSONStruct):
    file_id = JSONStruct.attr("file_id", int)  # file_id from /subtitles search results
    sub_format = JSONStruct.attr("sub_format", string)  # from /infos/formats
    file_name = JSONStruct.attr("file_name", string)  # desired file name
    in_fps = JSONStruct.attr("in_fps", int)  # used for conversions, in_fps and out_fps must then be indicated
    out_fps = JSONStruct.attr("out_fps", int)  # used for conversions, in_fps and out_fps must then be indicated
    timeshift = JSONStruct.attr("timeshift", int)
    force_download = JSONStruct.attr("force_download", bool)


class DownloadResponse(JSONStruct):
    link = JSONStruct.attr("link", string)
    file_name = JSONStruct.attr("file_name", string)
    requests = JSONStruct.attr("requests", int)
    remaining = JSONStruct.attr("remaining", int)
    message = JSONStruct.attr("message", string)
    reset_time = JSONStruct.attr("reset_time", string)
    reset_time_utc = JSONStruct.attr("reset_time_utc", string)


# API definition at https://opensubtitles.stoplight.io/docs/opensubtitles-api
class OpenSubtitles(object):
    API_REST = "https://api.opensubtitles.com/api/v1"

    def __init__(self, app_name, app_version, api_key=None):
        self._token = None
        self._session = requests.Session()
        self._session.headers = {
            "Api-Key": api_key or API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "{} v{}".format(app_name, app_version),
        }

    def login(self, username, password):
        """
        Perform login with the provided parameters.

        :param username: Username.
        :type username: str
        :param password: Password.
        :type password: str
        """
        data = self._request("POST", "login", data=json.dumps(dict(username=username, password=password)))
        self._token = data["token"]

    def logout(self):
        """
        Perform logout of the current session.
        """
        if self._token is not None:
            self._request("DELETE", "logout", headers=self._login_headers)
            self._token = None

    def search_subtitles(self, payload):
        return [SubtitleAttributes.from_data(d["attributes"], strict=True)
                for d in self._request("GET", "subtitles", params=payload.to_dict())["data"]]

    def download_subtitle(self, payload):
        return DownloadResponse.from_data(
            self._request("POST", "download", params=payload.to_dict()), strict=True)

    @property
    def _login_headers(self):
        return {"Authorization": "Bearer " + self._token}

    def _request(self, method, url, *args, **kwargs):
        r = self._session.request(method, self.API_REST + "/" + url, *args, **kwargs)
        r.raise_for_status()
        return r.json()
