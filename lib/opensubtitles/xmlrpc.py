import logging

try:
    from xmlrpclib import ServerProxy, Transport  # nosec
except ImportError:
    from xmlrpc.client import ServerProxy, Transport  # nosec

from lib.opensubtitles.utils import DataStruct


class XMLRPCStruct(DataStruct):
    pass


class SearchPayload(XMLRPCStruct):
    languages = XMLRPCStruct.attr("sublanguageid")
    hash = XMLRPCStruct.attr("moviehash")
    size = XMLRPCStruct.attr("moviebytesize")
    imdb_id = XMLRPCStruct.attr("imdbid")
    query = XMLRPCStruct.attr("query")
    season = XMLRPCStruct.attr("season")
    episode = XMLRPCStruct.attr("episode")
    tag = XMLRPCStruct.attr("tag")


class Subtitle(XMLRPCStruct):
    score = XMLRPCStruct.attr("Score")
    info_release_group = XMLRPCStruct.attr("InfoReleaseGroup")
    info_format = XMLRPCStruct.attr("InfoFormat")
    info_other = XMLRPCStruct.attr("InfoOther")
    id_movie = XMLRPCStruct.attr("IDMovie")
    id_movie_imdb = XMLRPCStruct.attr("IDMovieImdb")
    id_sub_movie_file = XMLRPCStruct.attr("IDSubMovieFile")
    id_subtitle = XMLRPCStruct.attr("IDSubtitle")
    id_subtitle_file = XMLRPCStruct.attr("IDSubtitleFile")
    iso_639 = XMLRPCStruct.attr("ISO639")
    language_name = XMLRPCStruct.attr("LanguageName")
    matched_by = XMLRPCStruct.attr("MatchedBy")
    movie_byte_size = XMLRPCStruct.attr("MovieByteSize")
    movie_fps = XMLRPCStruct.attr("MovieFPS")
    movie_hash = XMLRPCStruct.attr("MovieHash")
    movie_imdb_rating = XMLRPCStruct.attr("MovieImdbRating")
    movie_kind = XMLRPCStruct.attr("MovieKind")
    movie_name = XMLRPCStruct.attr("MovieName")
    movie_name_eng = XMLRPCStruct.attr("MovieNameEng")
    movie_release_name = XMLRPCStruct.attr("MovieReleaseName")
    movie_time_ms = XMLRPCStruct.attr("MovieTimeMS")
    movie_year = XMLRPCStruct.attr("MovieYear")
    query_number = XMLRPCStruct.attr("QueryNumber")
    query_parameters = XMLRPCStruct.attr("QueryParameters")
    query_cached = XMLRPCStruct.attr("QueryCached")
    series_episode = XMLRPCStruct.attr("SeriesEpisode")
    series_imdb_parent = XMLRPCStruct.attr("SeriesIMDBParent")
    series_season = XMLRPCStruct.attr("SeriesSeason")
    sub_actual_cd = XMLRPCStruct.attr("SubActualCD")
    sub_add_date = XMLRPCStruct.attr("SubAddDate")
    sub_author_comment = XMLRPCStruct.attr("SubAuthorComment")
    sub_bad = XMLRPCStruct.attr("SubBad")
    sub_sum_votes = XMLRPCStruct.attr("SubSumVotes")
    sub_comments = XMLRPCStruct.attr("SubComments")
    sub_download_link = XMLRPCStruct.attr("SubDownloadLink")
    sub_downloads_cnt = XMLRPCStruct.attr("SubDownloadsCnt")
    sub_encoding = XMLRPCStruct.attr("SubEncoding")
    sub_featured = XMLRPCStruct.attr("SubFeatured")
    sub_file_name = XMLRPCStruct.attr("SubFileName")
    sub_format = XMLRPCStruct.attr("SubFormat")
    sub_hash = XMLRPCStruct.attr("SubHash")
    sub_hd = XMLRPCStruct.attr("SubHD")
    sub_hearing_impaired = XMLRPCStruct.attr("SubHearingImpaired")
    sub_language_id = XMLRPCStruct.attr("SubLanguageID")
    sub_last_ts = XMLRPCStruct.attr("SubLastTS")
    sub_ts_group = XMLRPCStruct.attr("SubTSGroup")
    sub_ts_group_hash = XMLRPCStruct.attr("SubTSGroupHash")
    sub_rating = XMLRPCStruct.attr("SubRating")
    sub_size = XMLRPCStruct.attr("SubSize")
    sub_sum_cd = XMLRPCStruct.attr("SubSumCD")
    sub_translator = XMLRPCStruct.attr("SubTranslator")
    sub_auto_translation = XMLRPCStruct.attr("SubAutoTranslation")
    sub_foreign_parts_only = XMLRPCStruct.attr("SubForeignPartsOnly")
    sub_from_trusted = XMLRPCStruct.attr("SubFromTrusted")
    subtitles_link = XMLRPCStruct.attr("SubtitlesLink")
    user_id = XMLRPCStruct.attr("UserID")
    user_nick_name = XMLRPCStruct.attr("UserNickName")
    user_rank = XMLRPCStruct.attr("UserRank")
    zip_download_link = XMLRPCStruct.attr("ZipDownloadLink")


class SubtitleFile(XMLRPCStruct):
    id = XMLRPCStruct.attr("idsubtitlefile")
    data = XMLRPCStruct.attr("data")


class OpenSubtitlesError(Exception):
    pass


class OpenSubtitles(object):
    """
    OpenSubtitles API wrapper.
    Please check the official API documentation at:
    http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
    """

    API_XMLRPC = 'http://api.opensubtitles.org/xml-rpc'

    def __init__(self, language="en", user_agent="TemporaryUserAgent"):
        self._token = None
        self.language = language
        self.user_agent = user_agent

        transport = Transport()
        transport.user_agent = self.user_agent

        self._server = ServerProxy(self.API_XMLRPC, allow_none=True, transport=transport)

    @staticmethod
    def _assert_successful(data):
        status = data.get("status")
        if status != "200 OK":
            raise OpenSubtitlesError("Failed request: {}".format(status))

    def _request(self, method, *args):
        data = getattr(self._server, method)(*args)
        self._assert_successful(data)
        return data

    def login(self, username, password):
        """
        Perform login with the provided parameters.

        :param username: Username.
        :type username: str
        :param password: Password.
        :type password: str
        """
        data = self._request("LogIn", username, password, self.language, self.user_agent)
        self._token = data["token"]

    def logout(self):
        """
        Perform logout.
        """
        if self._token is not None:
            self._request("LogOut", self._token)
            self._token = None

    def search_subtitles(self, payload):
        """
        Returns a list with the subtitles' info.

        :param payload: List containing parameters for search.
        :type payload: list[SearchPayload]
        :return: Search results.
        :rtype: list[Subtitle]
        """
        data = self._request("SearchSubtitles", self._token, payload)
        return [Subtitle.from_data(d) for d in data["data"]]

    def download_subtitles(self, ids):
        # OpenSubtitles will accept a maximum of 20 IDs for download
        if len(ids) > 20:
            logging.warning("Cannot download more than 20 files at once.")
            ids = ids[:20]

        data = self._request("DownloadSubtitles", self._token, ids)
        return [SubtitleFile.from_data(d) for d in data["data"]]
