import tmdbsimple
import xbmcgui

from lib.kodi import ADDON_ID
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


def get_movie_info(data):
    if prefer_original_titles():
        title = data["original_title"]
    else:
        title = data["title"] or data["original_title"]

    # genres_dict = get_genres_by_id(Genres().movie_list(language=get_language()))

    premiered = data.get("release_date", "")
    if premiered in ["2999-01-01", "1900-01-01"]:
        premiered = ""

    movie_credits = data.get("credits", {})
    cast = movie_credits.get("cast", [])
    crew = movie_credits.get("crew", [])
    runtime = data.get("runtime")
    info = {
        "title": title,
        "originaltitle": data.get("original_title"),
        # "genre": [genres_dict[i] for i in data.get("genre_ids", []) if i in genres_dict],
        "country": data.get("origin_country"),
        "date": premiered,
        "premiered": premiered,
        "year": premiered.split("-")[0] if premiered else "",
        "rating": data.get("vote_average"),
        "votes": data.get("vote_count"),
        "plot": data.get("overview"),
        "trailer": "plugin://{}/play_trailer/movie/{}".format(ADDON_ID, data["id"]),
        "mediatype": "movie",
        # with info() - append_to_response="credits"
        "genre": [g["name"] for g in data.get("genres", [])],
        "imdbnumber": data.get("imdb_id"),
        "code": data.get("imdb_id"),
        "tagline": data.get("tagline"),
        "status": data.get("status"),
        "castandrole": [(c["name"], c["character"]) for c in cast],
        "director": [c["name"] for c in crew if c["job"] == "Director"],
        "writer": [c["name"] for c in crew if c["job"] == "Writer"],
        "studio": [s["name"] for s in data.get("production_companies", [])],
        "duration": runtime * 60 if runtime else None,
    }

    icon = get_image(data, "poster_path")
    backdrop = get_image(data, "backdrop_path")
    art = {"icon": "DefaultVideo.png", "thumb": icon, "poster": icon, "fanart": backdrop}

    return title, info, art


def movie_to_list_item(show_data):
    title, info, art = get_movie_info(show_data)
    list_item = xbmcgui.ListItem(title)
    list_item.setInfo("video", info)
    list_item.setArt(art)
    return list_item


def movie_list_items(data):
    for result in data["results"]:
        yield movie_to_list_item(result)


def movie_list_items_by_ids(movie_ids):
    for movie_id in movie_ids:
        result = Movies(movie_id).info(language=get_language(), append_to_response="credits")
        yield movie_to_list_item(result)


def get_show_info(data):
    if prefer_original_titles():
        title = data["original_name"]
    else:
        title = data["name"] or data["original_name"]

    # genres_dict = get_genres_by_id(Genres().tv_list(language=get_language()))

    premiered = data.get("first_air_date", "")
    if premiered in ["2999-01-01", "1900-01-01"]:
        premiered = ""

    show_credits = data.get("credits", {})
    cast = show_credits.get("cast", [])
    crew = show_credits.get("crew", [])
    info = {
        "title": title,
        "originaltitle": data.get("original_title"),
        "tvshowtitle": data.get("original_title"),
        # "genre": [genres_dict[i] for i in data.get("genre_ids", []) if i in genres_dict],
        "date": premiered,
        "premiered": premiered,
        "year": premiered.split("-")[0] if premiered else "",
        "rating": data.get("vote_average"),
        "votes": data.get("vote_count"),
        "plot": data.get("overview"),
        "status": data.get("status"),
        "trailer": "plugin://{}/play_trailer/show/{}".format(ADDON_ID, data["id"]),
        "mediatype": "tvshow",
        # with info() - append_to_response="credits"
        "genre": [g["name"] for g in data.get("genres", [])],
        "imdbnumber": data.get("imdb_id"),
        "code": data.get("imdb_id"),
        "castandrole": [(c["name"], c["character"]) for c in cast],
        "director": [c["name"] for c in crew if c["job"] == "Director"],
        "writer": [c["name"] for c in crew if c["job"] == "Writer"],
        "studio": [s["name"] for s in data.get("production_companies", [])],
        "season": data.get("number_of_seasons"),
        "episode": data.get("number_of_episodes"),
    }

    icon = get_image(data, "poster_path")
    backdrop = get_image(data, "backdrop_path")
    art = {"icon": "DefaultVideo.png", "thumb": icon, "poster": icon, "fanart": backdrop}

    return title, info, art


def show_to_list_item(show_data):
    title, info, art = get_show_info(show_data)
    list_item = xbmcgui.ListItem(title)
    list_item.setInfo("video", info)
    list_item.setArt(art)
    return list_item


def show_list_items(data):
    for result in data["results"]:
        yield show_to_list_item(result), result["id"]


def show_list_items_by_id(shows_ids):
    for show_id in shows_ids:
        result = TV(show_id).info(language=get_language(), append_to_response="credits")
        yield show_to_list_item(result), result["id"]


def season_list_items(show_id):
    data = TV(show_id).info(language=get_language(), append_to_response="credits")
    title, info, art = get_show_info(data)
    info.update({
        "mediatype": "season",
        "status": "",
    })

    for season in data["seasons"]:
        season_art = dict(art)
        season_info = dict(info)

        premiered = season.get("air_date", "")
        season_info["trailer"] = "plugin://{}/play_trailer/season/{}/{}".format(
            ADDON_ID, data["id"], season["season_number"])
        season_info["tvshowtitle"] = title
        season_info["premiered"] = premiered
        season_info["year"] = premiered.split("-")[0] if premiered else ""
        season_info["season"] = 1
        season_info["episode"] = season.get("episode_count")
        overview = season.get("overview")
        if overview:
            season_info["plot"] = overview

        season_li = xbmcgui.ListItem(title + " - " + season["name"])
        season_li.setInfo("video", season_info)

        icon = get_image(season, "poster_path")
        if icon:
            season_art["thumb"] = season_art["poster"] = icon

        season_li.setArt(season_art)
        yield season_li, season["season_number"]


def get_episode_info(data):
    title = data["name"]

    crew = data.get("crew", [])
    info = {
        "title": title,
        "aired": data.get("air_date"),
        "season": data.get("season_number"),
        "episode": data.get("episode_number"),
        "code": data.get("production_code"),
        "plot": data.get("overview"),
        "rating": data.get("vote_average"),
        "votes": data.get("vote_count"),
        "trailer": "plugin://{}/play_trailer/episode/{}/{}/{}".format(
            ADDON_ID, data["show_id"], data["season_number"], data["episode_number"]),
        "mediatype": "episode",
        "castandrole": [(c["name"], c["character"]) for c in data.get("guest_stars", [])],
        "director": [c["name"] for c in crew if c["job"] == "Director"],
        "writer": [c["name"] for c in crew if c["job"] == "Writer"],
    }

    still_path = get_image(data, "still_path")
    art = {"icon": "DefaultVideo.png", "thumb": still_path, "poster": still_path, "fanart": still_path}

    return title, info, art


def episodes_list_items(show_id, season_number):
    season = TVSeasons(show_id, season_number).info(language=get_language())
    for episode in season["episodes"]:
        title, info, art = get_episode_info(episode)
        episode_li = xbmcgui.ListItem(title)
        episode_li.setInfo("video", info)
        episode_li.setArt(art)
        yield episode_li, episode["episode_number"]


def person_list_items(data):
    for result in data["results"]:
        list_item = xbmcgui.ListItem(result["name"])
        icon = get_image(result, "profile_path")
        list_item.setArt({"icon": "DefaultActor.png", "thumb": icon, "poster": icon})
        yield list_item
