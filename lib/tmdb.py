import time
from datetime import datetime

import tmdbsimple
import xbmcgui

from lib.api.flix.kodi import ADDON_ID
from lib.kodi_cache import KodiCache
from lib.settings import is_cache_enabled, prefer_original_titles, get_language

IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"
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

def get_ids(data):
    return [r["id"] for r in data["results"]]


def get_image(data, key):
    path = data.get(key)
    return "" if path is None else (IMAGE_BASE_URL + path)


def get_genres_by_id(genres_data):
    return {g["id"]: g["name"] for g in genres_data["genres"]}


def get_genres_by_name(genres_data):
    return {g["name"]: g["id"] for g in genres_data["genres"]}


class VideoItem(object):
    def __init__(self, **kwargs):
        self._title = kwargs.get("title", "")
        self._info = kwargs.get("info", {})
        self._art = kwargs.get("art", {})

    def to_list_item(self):
        list_item = xbmcgui.ListItem(self._title)
        list_item.setInfo("video", self._info)
        list_item.setArt(self._art)
        return list_item

    @property
    def title(self):
        return self._title

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
            "castandrole": [(c["name"], c["character"]) for c in cast],
            "director": [c["name"] for c in crew if c["job"] == "Director"],
            "writer": [c["name"] for c in crew if c["job"] == "Writer"],
            "studio": [s["name"] for s in self._data.get("production_companies", [])],
            "duration": runtime * 60 if runtime else None,
        }

        icon = get_image(self._data, "poster_path")
        backdrop = get_image(self._data, "backdrop_path")
        art = {"icon": "DefaultVideo.png", "thumb": icon, "poster": icon, "fanart": backdrop}

        super(Movie, self).__init__(movie_id, title=title, info=info, art=art)


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
            "originaltitle": self._data.get("original_title"),
            "tvshowtitle": self._data.get("original_title"),
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
            "castandrole": [(c["name"], c["character"]) for c in cast],
            "director": [c["name"] for c in crew if c["job"] == "Director"],
            "writer": [c["name"] for c in crew if c["job"] == "Writer"],
            "studio": [s["name"] for s in self._data.get("production_companies", [])],
            "season": self._data.get("number_of_seasons"),
            "episode": self._data.get("number_of_episodes"),
        }

        icon = get_image(self._data, "poster_path")
        backdrop = get_image(self._data, "backdrop_path")
        art = {"icon": "DefaultVideo.png", "thumb": icon, "poster": icon, "fanart": backdrop}

        super(Show, self).__init__(show_id, title=title, info=info, art=art)

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

            icon = get_image(season, "poster_path")
            if icon:
                season_art["thumb"] = season_art["poster"] = icon

            yield SeasonItem(self._show_id, season_number, title=season_title, info=season_info, art=season_art)


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
        # TODO: parse data - to_list_item is useless atm
        super(Season, self).__init__(show_id, season_number)

    def episodes(self):
        season_credits = self._data.get("credits", {})

        for episode in self._data["episodes"]:
            title = episode["name"]
            episode_number = episode["episode_number"]
            crew = episode.get("crew", [])
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
                "castandrole": [(c["name"], c["character"]) for c in
                                season_credits.get("cast", []) + episode.get("guest_stars", [])],
                "director": [c["name"] for c in crew if c["job"] == "Director"],
                "writer": [c["name"] for c in crew if c["job"] == "Writer"],
            }

            still_path = get_image(episode, "still_path")
            art = {"icon": "DefaultVideo.png", "thumb": still_path, "poster": still_path, "fanart": still_path}
            yield EpisodeItem(self._show_id, self._season_number, episode_number, title=title, info=info, art=art)


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
        icon = get_image(result, "profile_path")
        list_item.setArt({"icon": "DefaultActor.png", "thumb": icon, "poster": icon})
        yield list_item, result["id"]


def _get_credits(data_credits):
    now = datetime.now()
    for credit in data_credits:
        release_date = credit.get("release_date")
        if not release_date or datetime(*time.strptime(release_date, "%Y-%m-%d")[:6]) > now:
            continue
        if credit.get("media_type") == "movie":
            yield credit["id"], True, release_date
        elif credit.get("media_type") == "movie":
            yield credit["id"], False, release_date


def get_person_credits(person_id, cast=True, crew=False):
    data = People(person_id).combined_credits(language=get_language())
    credits_list = []
    if cast:
        credits_list += list(_get_credits(data.get("cast", [])))
    if crew:
        credits_list += list(_get_credits(data.get("crew", [])))
    credits_list.sort(key=lambda v: v[2], reverse=True)
    return credits_list
