import time
from datetime import datetime, timedelta

import tmdbsimple
import xbmcgui
from cached import Cache

from lib.api.flix.kodi import ADDON_ID
from lib.api.flix.utils import get_data
from lib.settings import is_cache_enabled, prefer_original_titles, get_language, get_scraper_threads, \
    get_cache_expiration_days

IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"
tmdbsimple.API_KEY = "eee9ac1822295afd8dadb555a0cc4ea8"

# noinspection PyProtectedMember
_tmdb_original_get = tmdbsimple.base.TMDB._GET


def _tmdb_get(self, path, params=None):
    cache = Cache.get_instance() if is_cache_enabled() else None
    if cache is None:
        return _tmdb_original_get(self, path, params=params)
    identifier = "{}|{}".format(path, repr(params))
    data = cache.get(identifier, hashed_key=True)
    if data is None:
        data = _tmdb_original_get(self, path, params=params)
        cache.set(identifier, data, timedelta(days=get_cache_expiration_days()), hashed_key=True)
    return data


# Patching tmdbsimple to enable cache
tmdbsimple.base.TMDB._GET = _tmdb_get


class _TMDB(tmdbsimple.base.TMDB):
    def _format_path(self, key):
        return self._get_path(key).format(**self.__dict__)


class Trending(_TMDB):
    BASE_PATH = "trending"
    URLS = {
        "trending": "/{media_type}/{time_window}",
    }

    def __init__(self, media_type, time_window):
        super(Trending, self).__init__()
        self.media_type = media_type
        self.time_window = time_window

    def get_trending(self, **kwargs):
        response = self._GET(self._format_path("trending"), kwargs)
        self._set_attrs_to_values(response)
        return response


def has_results(data):
    return bool(data["results"])


def get_ids(data):
    return [r["id"] for r in data["results"]]


def get_image(data, key, size="original"):
    # size: "w92", "w154", "w185", "w342", "w500", "w780" or "original"
    path = data.get(key)
    return "" if path is None else (IMAGE_BASE_URL + size + path)


def get_genres_by_id(genres_data):
    return {g["id"]: g["name"] for g in genres_data["genres"]}


def get_genres_by_name(genres_data):
    return {g["name"]: g["id"] for g in genres_data["genres"]}


def get_cast(cast):
    return [{"name": c.get("name", "-"), "role": c["character"],
             "thumbnail": get_image(c, "profile_path", "w342"), "order": i}
            for i, c in enumerate(cast, 1)]


def get_cast_and_role(cast):
    return [(c.get("name", "-"), c["character"]) for c in cast]


def get_directors(crew):
    return [c["name"] for c in crew if c["job"] == "Director"]


def get_writers(crew):
    return [c["name"] for c in crew if c["job"] == "Writer"]


def is_unaired(air_date, now):
    return not air_date or datetime(*time.strptime(air_date, "%Y-%m-%d")[:6]) > now


class VideoItem(object):
    def __init__(self, **kwargs):
        self._title = kwargs.get("title", "")
        self._info = kwargs.get("info", {})
        self._art = kwargs.get("art", {})
        self._cast = kwargs.get("cast", [])

    def to_list_item(self, path=None, playable=False):
        list_item = xbmcgui.ListItem(self._title)
        list_item.setInfo("video", self._info)
        list_item.setArt(self._art)
        list_item.setCast(self._cast)
        if playable:
            list_item.setProperty("IsPlayable", "true")
        if path is not None:
            list_item.setPath(path)
        return list_item

    @property
    def title(self):
        return self._title

    def dict(self):
        return {"title": self._title, "info": self._info, "art": self._art, "cast": self._cast}

    def get_info(self, key):
        return self._info[key]

    def get_info_as(self, key, clazz, default=None):
        value = self.get_info(key)
        return clazz(value) if value else default

    def get_art(self, key):
        return self._art[key]

    def __str__(self):
        return "{}(title={})".format(self.__class__.__name__, self._title)


class MovieItem(VideoItem):
    def __init__(self, movie_id, **kwargs):
        super(MovieItem, self).__init__(**kwargs)
        self._movie_id = movie_id

    @property
    def movie_id(self):
        return self._movie_id

    def __str__(self):
        return "{}(id={})".format(self.__class__.__name__, self._movie_id)


class Movie(MovieItem):
    def __init__(self, movie_id):
        self._data = tmdbsimple.Movies(movie_id).info(
            language=get_language(), append_to_response="credits,alternative_titles")
        self._alternative_titles = {
            t["iso_3166_1"].lower(): t["title"] for t in self._data.get("alternative_titles", {}).get("titles", [])
        }
        self._alternative_titles["auto"] = title = self._data["title"] or self._data["original_title"]

        if prefer_original_titles():
            title = self._data["original_title"]

        # genres_dict = get_genres_by_id(Genres().movie_list(language=get_language()))
        premiered = self._data.get("release_date", "")
        if premiered in ["2999-01-01", "1900-01-01"]:
            premiered = ""

        movie_credits = self._data.get("credits", {})
        cast = movie_credits.get("cast", [])
        crew = movie_credits.get("crew", [])
        runtime = self._data.get("runtime")

        info = {
            "title": title,
            "originaltitle": self._data.get("original_title"),
            # "genre": [genres_dict[i] for i in self._data.get("genre_ids", []) if i in genres_dict],
            "country": self._data.get("origin_country"),
            "date": premiered,
            "premiered": premiered,
            "year": premiered.split("-")[0] if premiered else "",
            "rating": self._data.get("vote_average"),
            "votes": self._data.get("vote_count"),
            "plot": self._data.get("overview"),
            "trailer": "plugin://{}/play_trailer/movie/{}".format(ADDON_ID, self._data["id"]),
            "mediatype": "movie",
            "genre": [g["name"] for g in self._data.get("genres", [])],
            "imdbnumber": self._data.get("imdb_id"),
            "code": self._data.get("imdb_id"),
            "tagline": self._data.get("tagline"),
            "status": self._data.get("status"),
            "castandrole": get_cast_and_role(cast),
            "director": get_directors(crew),
            "writer": get_writers(crew),
            "studio": [s["name"] for s in self._data.get("production_companies", [])],
            "duration": runtime * 60 if runtime else None,
        }

        icon = get_image(self._data, "poster_path", "w780")
        backdrop = get_image(self._data, "backdrop_path")
        art = {"icon": "DefaultVideo.png", "thumb": icon, "poster": icon, "fanart": backdrop}

        super(Movie, self).__init__(movie_id, title=title, info=info, art=art, cast=get_cast(cast))

    @property
    def alternative_titles(self):
        return self._alternative_titles


class ShowItem(VideoItem):
    def __init__(self, show_id, **kwargs):
        super(ShowItem, self).__init__(**kwargs)
        self._show_id = show_id

    @property
    def show_id(self):
        return self._show_id

    def __str__(self):
        return "{}(id={})".format(self.__class__.__name__, self._show_id)


class Show(ShowItem):
    def __init__(self, show_id):
        self._data = tmdbsimple.TV(show_id).info(
            language=get_language(), append_to_response="credits,alternative_titles,external_ids")
        self._alternative_titles = {
            t["iso_3166_1"].lower(): t["title"] for t in self._data.get("alternative_titles", {}).get("results", [])
        }
        self._alternative_titles["auto"] = title = self._data["name"] or self._data["original_name"]
        self._external_ids = self._data.get("external_ids", {})

        if prefer_original_titles():
            title = self._data["original_name"]

        # genres_dict = get_genres_by_id(Genres().tv_list(language=get_language()))

        premiered = self._data.get("first_air_date", "")
        if premiered in ["2999-01-01", "1900-01-01"]:
            premiered = ""

        show_credits = self._data.get("credits", {})
        cast = show_credits.get("cast", [])
        crew = show_credits.get("crew", [])
        info = {
            "title": title,
            "originaltitle": self._data.get("original_name"),
            "tvshowtitle": self._data.get("original_name"),
            # "genre": [genres_dict[i] for i in self._data.get("genre_ids", []) if i in genres_dict],
            "date": premiered,
            "premiered": premiered,
            "year": premiered.split("-")[0] if premiered else "",
            "rating": self._data.get("vote_average"),
            "votes": self._data.get("vote_count"),
            "plot": self._data.get("overview"),
            "status": self._data.get("status"),
            "trailer": "plugin://{}/play_trailer/show/{}".format(ADDON_ID, self._data["id"]),
            "mediatype": "tvshow",
            "genre": [g["name"] for g in self._data.get("genres", [])],
            "imdbnumber": self._external_ids.get("imdb_id"),
            "code": self._external_ids.get("imdb_id"),
            "castandrole": get_cast_and_role(cast),
            "director": get_directors(crew),
            "writer": get_writers(crew),
            "studio": [s["name"] for s in self._data.get("production_companies", [])],
        }

        icon = get_image(self._data, "poster_path", "w780")
        backdrop = get_image(self._data, "backdrop_path")
        art = {"icon": "DefaultVideo.png", "thumb": icon, "poster": icon, "fanart": backdrop}

        super(Show, self).__init__(show_id, title=title, info=info, art=art, cast=get_cast(cast))

    @property
    def alternative_titles(self):
        return self._alternative_titles

    def seasons(self, get_unaired=True):
        now = datetime.now()
        for season in self._data["seasons"]:
            premiered = season.get("air_date", "")
            if not get_unaired and is_unaired(premiered, now):
                continue

            season_art = dict(self._art)
            season_info = dict(self._info)

            season_title = season["name"]
            season_number = season["season_number"]
            season_info.update({
                "mediatype": "season",
                "status": "",
                "originaltitle": None,
                "title": season_title,
                "trailer": "plugin://{}/play_trailer/season/{}/{}".format(
                    ADDON_ID, self._show_id, season_number),
                "premiered": premiered,
                "year": premiered.split("-")[0] if premiered else "",
                "season": season_number
            })

            overview = season.get("overview")
            if overview:
                season_info["plot"] = overview

            icon = get_image(season, "poster_path", "w780")
            if icon:
                season_art["thumb"] = season_art["poster"] = icon

            yield SeasonItem(self._show_id, season_number,
                             title=season_title, info=season_info, art=season_art, cast=self._cast)


class SeasonItem(ShowItem):
    def __init__(self, show_id, season_number, **kwargs):
        super(SeasonItem, self).__init__(show_id, **kwargs)
        self._season_number = season_number

    @property
    def season_number(self):
        return self._season_number

    def __str__(self):
        return "{}(id={}, season={})".format(
            self.__class__.__name__, self._show_id, self._season_number)


class Season(SeasonItem):
    def __init__(self, show_id, season_number, show_title=None):
        self._data = tmdbsimple.TV_Seasons(show_id, season_number).info(
            language=get_language(), append_to_response="credits")
        self._credits = self._data.get("credits", {})
        self._show_title = show_title
        # TODO: parse data - to_list_item is useless atm
        super(Season, self).__init__(show_id, season_number)

    def _parse_episode(self, episode):
        title = episode["name"]
        episode_number = episode["episode_number"]
        crew = episode.get("crew", [])
        cast = self._credits.get("cast", []) + episode.get("guest_stars", [])
        info = {
            "title": title,
            "tvshowtitle": self._show_title,
            "aired": episode.get("air_date"),
            "season": self._season_number,
            "episode": episode_number,
            "code": episode.get("production_code"),
            "plot": episode.get("overview"),
            "rating": episode.get("vote_average"),
            "votes": episode.get("vote_count"),
            "trailer": "plugin://{}/play_trailer/episode/{}/{}/{}".format(
                ADDON_ID, self._show_id, self._season_number, episode_number),
            "mediatype": "episode",
            "castandrole": get_cast_and_role(cast),
            "director": get_directors(crew),
            "writer": get_writers(crew),
        }

        still_path = get_image(episode, "still_path")
        art = {"icon": "DefaultVideo.png", "thumb": still_path, "poster": still_path, "fanart": still_path}
        return EpisodeItem(self._show_id, self._season_number, episode_number,
                           title=title, info=info, art=art, cast=get_cast(cast))

    def episodes(self, get_unaired=True):
        now = datetime.now()
        for episode in self._data["episodes"]:
            if get_unaired or not is_unaired(episode.get("air_date"), now):
                yield self._parse_episode(episode)

    def get_episode(self, episode_number):
        for episode in self._data["episodes"]:
            if episode["episode_number"] == int(episode_number):
                return self._parse_episode(episode)
        raise ValueError("No such episode")


class EpisodeItem(SeasonItem):
    def __init__(self, show_id, season_number, episode_number, **kwargs):
        super(EpisodeItem, self).__init__(show_id, season_number, **kwargs)
        self._episode_number = episode_number

    @property
    def episode_number(self):
        return self._episode_number

    def __str__(self):
        return "{}(id={}, season={}, episode={})".format(
            self.__class__.__name__, self._show_id, self._season_number, self._episode_number)


def person_list_items(data):
    for result in data["results"]:
        list_item = xbmcgui.ListItem(result["name"])
        icon = get_image(result, "profile_path", "w500")
        list_item.setArt({"icon": "DefaultActor.png", "thumb": icon, "poster": icon})
        yield list_item, result["id"]


def _get_credits(data_credits):
    now = datetime.now()
    for credit in data_credits:
        media_type = credit.get("media_type")
        if media_type == "movie":
            release_date, is_movie = credit.get("release_date"), True
        elif media_type == "tv":
            release_date, is_movie = credit.get("first_air_date"), False
        else:
            continue
        if not release_date or datetime(*time.strptime(release_date, "%Y-%m-%d")[:6]) > now:
            continue
        yield credit["id"], is_movie, release_date


def get_person_credits(person_id, cast=True, crew=False):
    data = tmdbsimple.People(person_id).combined_credits(language=get_language())
    credits_list = []
    if cast:
        credits_list += list(_get_credits(data.get("cast", [])))
    if crew:
        credits_list += list(_get_credits(data.get("crew", [])))
    credits_list.sort(key=lambda v: v[2], reverse=True)
    return credits_list


def get_movies(data):
    ids = get_ids(data)
    return get_data(Movie, ids, threads=get_scraper_threads(), yield_exceptions=False), len(ids)


def get_shows(data):
    ids = get_ids(data)
    return get_data(Show, ids, threads=get_scraper_threads(), yield_exceptions=False), len(ids)


def get_credits_media(credits_entry):
    tmdb_id, is_movie, _ = credits_entry
    return Movie(tmdb_id) if is_movie else Show(tmdb_id), is_movie


def get_person_media(person_id):
    credits_list = get_person_credits(person_id)
    return (get_data(get_credits_media, credits_list, threads=get_scraper_threads(), yield_exceptions=False),
            len(credits_list))
