import time
from datetime import datetime

import tmdbsimple
import xbmcgui

from lib.api.flix.kodi import ADDON_ID
from lib.api.flix.utils import get_data
from lib.kodi_cache import KodiCache
from lib.settings import is_cache_enabled, prefer_original_titles, get_language, get_scraper_thrads

IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"
tmdbsimple.API_KEY = "eee9ac1822295afd8dadb555a0cc4ea8"


class TMDB(tmdbsimple.base.TMDB):
    def __init__(self):
        super(TMDB, self).__init__()
        self._cache = KodiCache() if is_cache_enabled() else None

    def _GET(self, path, params=None):
        if self._cache is None:
            return super(TMDB, self)._GET(path, params=params)
        identifier = "{}|{}".format(path, repr(params))
        data = self._cache.get(identifier)
        if data is None:
            data = super(TMDB, self)._GET(path, params=params)
            self._cache.set(identifier, data)
        return data

    def _format_path(self, key):
        return self._get_path(key).format(**self.__dict__)


def _code_gen():
    with open(tmdbsimple.__file__) as f:
        contents = f.read()

    import re
    for imports in re.findall(r"from .+? import\s(.+)", contents):
        for i in imports.split(","):
            i = i.strip()
            if tmdbsimple.base.TMDB in getattr(tmdbsimple, i).__mro__:
                print("class {}(tmdbsimple.{}, TMDB):\n    pass\n\n".format(i.replace("_", ""), i))


# Code automatically generated
class Account(tmdbsimple.Account, TMDB):
    pass


class Authentication(tmdbsimple.Authentication, TMDB):
    pass


class GuestSessions(tmdbsimple.GuestSessions, TMDB):
    pass


class Lists(tmdbsimple.Lists, TMDB):
    pass


class Changes(tmdbsimple.Changes, TMDB):
    pass


class Configuration(tmdbsimple.Configuration, TMDB):
    pass


class Certifications(tmdbsimple.Certifications, TMDB):
    pass


class Timezones(tmdbsimple.Timezones, TMDB):
    pass


class Discover(tmdbsimple.Discover, TMDB):
    pass


class Find(tmdbsimple.Find, TMDB):
    pass


class Genres(tmdbsimple.Genres, TMDB):
    pass


class Movies(tmdbsimple.Movies, TMDB):
    pass


class Collections(tmdbsimple.Collections, TMDB):
    pass


class Companies(tmdbsimple.Companies, TMDB):
    pass


class Keywords(tmdbsimple.Keywords, TMDB):
    pass


class Reviews(tmdbsimple.Reviews, TMDB):
    pass


class People(tmdbsimple.People, TMDB):
    pass


class Credits(tmdbsimple.Credits, TMDB):
    pass


class Jobs(tmdbsimple.Jobs, TMDB):
    pass


class Search(tmdbsimple.Search, TMDB):
    pass


class TV(tmdbsimple.TV, TMDB):
    pass


class TVSeasons(tmdbsimple.TV_Seasons, TMDB):
    pass


class TVEpisodes(tmdbsimple.TV_Episodes, TMDB):
    pass


class Networks(tmdbsimple.Networks, TMDB):
    pass


# end of auto generated code
class Trending(TMDB):
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
    return [{"name": c["name"], "role": c["character"], "thumbnail": get_image(c, "profile_path", "w342"), "order": i}
            for i, c in enumerate(cast, 1)]


def get_cast_and_role(cast):
    return [(c["name"], c["character"]) for c in cast]


def get_directors(crew):
    return [c["name"] for c in crew if c["job"] == "Director"]


def get_writers(crew):
    return [c["name"] for c in crew if c["job"] == "Writer"]


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

    def get_art(self, key):
        return self._art[key]


class MovieItem(VideoItem):
    def __init__(self, movie_id, **kwargs):
        super(MovieItem, self).__init__(**kwargs)
        self._movie_id = movie_id

    @property
    def movie_id(self):
        return self._movie_id


class Movie(MovieItem):
    def __init__(self, movie_id):
        self._data = Movies(movie_id).info(language=get_language(), append_to_response="credits,alternative_titles")
        self._alternative_titles = {
            t["iso_3166_1"].lower(): t["title"] for t in self._data.get("alternative_titles", {}).get("titles", [])
        }

        if prefer_original_titles():
            title = self._data["original_title"]
        else:
            title = self._data["title"] or self._data["original_title"]

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


class Show(ShowItem):
    def __init__(self, show_id):
        self._data = TV(show_id).info(language=get_language(), append_to_response="credits,alternative_titles")
        self._alternative_titles = {
            t["iso_3166_1"].lower(): t["title"] for t in self._data.get("alternative_titles", {}).get("results", [])
        }

        if prefer_original_titles():
            title = self._data["original_name"]
        else:
            title = self._data["name"] or self._data["original_name"]

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
            "imdbnumber": self._data.get("imdb_id"),
            "code": self._data.get("imdb_id"),
            "castandrole": get_cast_and_role(cast),
            "director": get_directors(crew),
            "writer": get_writers(crew),
            "studio": [s["name"] for s in self._data.get("production_companies", [])],
            "season": self._data.get("number_of_seasons"),
            "episode": self._data.get("number_of_episodes"),
        }

        icon = get_image(self._data, "poster_path", "w780")
        backdrop = get_image(self._data, "backdrop_path")
        art = {"icon": "DefaultVideo.png", "thumb": icon, "poster": icon, "fanart": backdrop}

        super(Show, self).__init__(show_id, title=title, info=info, art=art, cast=get_cast(cast))

    @property
    def alternative_titles(self):
        return self._alternative_titles

    def seasons(self):
        for season in self._data["seasons"]:
            season_art = dict(self._art)
            season_info = dict(self._info)

            season_title = season["name"]
            season_number = season["season_number"]
            premiered = season.get("air_date", "")
            season_info.update({
                "mediatype": "season",
                "status": "",
                "originaltitle": None,
                "title": season_title,
                "trailer": "plugin://{}/play_trailer/season/{}/{}".format(
                    ADDON_ID, self._show_id, season_number),
                "tvshowtitle": self._title,
                "premiered": premiered,
                "year": premiered.split("-")[0] if premiered else "",
                "season": 1,
                "episode": season.get("episode_count"),
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


class Season(SeasonItem):
    def __init__(self, show_id, season_number):
        self._data = TVSeasons(show_id, season_number).info(language=get_language(), append_to_response="credits")
        self._credits = self._data.get("credits", {})
        # TODO: parse data - to_list_item is useless atm
        super(Season, self).__init__(show_id, season_number)

    def _parse_episode(self, episode):
        title = episode["name"]
        episode_number = episode["episode_number"]
        crew = episode.get("crew", [])
        cast = self._credits.get("cast", []) + episode.get("guest_stars", [])
        info = {
            "title": title,
            "aired": episode.get("air_date"),
            "season": episode.get("season_number"),
            "episode": episode.get("episode_number"),
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

    def episodes(self):
        for episode in self._data["episodes"]:
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
    data = People(person_id).combined_credits(language=get_language())
    credits_list = []
    if cast:
        credits_list += list(_get_credits(data.get("cast", [])))
    if crew:
        credits_list += list(_get_credits(data.get("crew", [])))
    credits_list.sort(key=lambda v: v[2], reverse=True)
    return credits_list


def get_movies(data):
    ids = get_ids(data)
    return get_data(Movie, ids, threads=get_scraper_thrads()), len(ids)


def get_shows(data):
    ids = get_ids(data)
    return get_data(Show, ids, threads=get_scraper_thrads()), len(ids)


def get_credits_media(credits_entry):
    tmdb_id, is_movie, _ = credits_entry
    return Movie(tmdb_id) if is_movie else Show(tmdb_id), is_movie


def get_person_media(person_id):
    credits_list = get_person_credits(person_id)
    return get_data(get_credits_media, credits_list, threads=get_scraper_thrads()), len(credits_list)
