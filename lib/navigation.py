import datetime
import logging
import os

from routing import Plugin
from xbmc import executebuiltin
from xbmcgui import ListItem, Dialog
from xbmcplugin import addDirectoryItem, endOfDirectory, setContent

from lib import tmdb
from lib.kodi import ADDON_PATH, set_logger, notification, translate
from lib.settings import get_language

MOVIES_TYPE = "movies"
SHOWS_TYPE = "tvshows"
EPISODES_TYPE = "episodes"

plugin = Plugin()


def li(tid, icon):
    return list_item(translate(tid), icon)


def list_item(label, icon):
    item = ListItem(label)
    item.setArt({"icon": os.path.join(ADDON_PATH, "resources", "images", icon)})
    return item


def handle_page(data, func, *args, **kwargs):
    page = int(kwargs.get("page", 1))
    if page < data["total_pages"]:
        kwargs["page"] = page + 1
        addDirectoryItem(plugin.handle, plugin.url_for(func, *args, **kwargs), li(30105, "next.png"), isFolder=True)


def container_update(func, *args, **kwargs):
    executebuiltin("Container.Update({})".format(plugin.url_for(func, *args, **kwargs)))


@plugin.route("/")
def index():
    addDirectoryItem(plugin.handle, plugin.url_for(discover), li(30100, "discover.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(movies), li(30101, "movies.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(shows), li(30102, "series.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(search), li(30103, "search.png"), isFolder=True)
    endOfDirectory(plugin.handle)


@plugin.route("/discover")
def discover():
    addDirectoryItem(plugin.handle, plugin.url_for(discover_select, MOVIES_TYPE),
                     list_item("{} - {}".format(translate(30100), translate(30101)), "movies.png"))
    addDirectoryItem(plugin.handle, plugin.url_for(discover_select, SHOWS_TYPE),
                     list_item("{} - {}".format(translate(30100), translate(30102)), "series.png"))
    addDirectoryItem(plugin.handle, plugin.url_for(discover_people),
                     list_item("{} - {}".format(translate(30100), translate(30104)), "people.png"), isFolder=True)
    endOfDirectory(plugin.handle)


@plugin.route("/discover/select/<media_type>")
def discover_select(media_type):
    if media_type == MOVIES_TYPE:
        label = 30101
        handler = discover_movies
    elif media_type == SHOWS_TYPE:
        label = 30102
        handler = discover_shows
    else:
        return

    result = Dialog().select("{} - {}".format(translate(30100), translate(label)), [
        translate(30100),  # discover
        translate(30106),  # by genre
        translate(30107),  # by year
    ])
    if result < 0:
        return

    language = get_language()
    kwargs = {"language": language}
    if result == 1:
        genres_handle = tmdb.Genres().movie_list if media_type == MOVIES_TYPE else tmdb.Genres().tv_list
        genres_dict = tmdb.get_genres_by_name(genres_handle(language=language))
        genres_names = sorted(genres_dict.keys())
        selected_genre = Dialog().select("{} - {}".format(translate(30100), translate(30106)), genres_names)
        if selected_genre < 0:
            return
        kwargs["with_genres"] = genres_dict[genres_names[selected_genre]]
    elif result == 2:
        years = [str(y) for y in range(datetime.datetime.now().year, 1900 - 1, -1)]
        selected_year = Dialog().select("{} - {}".format(translate(30100), translate(30107)), years)
        if selected_year < 0:
            return
        kwargs["year" if media_type == MOVIES_TYPE else "first_air_date_year"] = years[selected_year]

    container_update(handler, **kwargs)


@plugin.route("/discover/movies/<language>")
@plugin.route("/discover/movies/<language>/<page>")
@plugin.route("/discover/movies/by_year/<year>/<language>")
@plugin.route("/discover/movies/by_year/<year>/<language>/<page>")
@plugin.route("/discover/movies/by_genre/<with_genres>/<language>")
@plugin.route("/discover/movies/by_genre/<with_genres>/<language>/<page>")
def discover_movies(**kwargs):
    setContent(plugin.handle, MOVIES_TYPE)
    data = tmdb.Discover().movie(**kwargs)
    for movie_li in tmdb.movie_list_items_by_ids(tmdb.get_ids(data)):
        # TODO - call providers
        addDirectoryItem(plugin.handle, "", movie_li)
    handle_page(data, discover_movies, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/discover/shows/<language>")
@plugin.route("/discover/shows/<language>/<page>")
@plugin.route("/discover/shows/by_year/<first_air_date_year>/<language>")
@plugin.route("/discover/shows/by_year/<first_air_date_year>/<language>/<page>")
@plugin.route("/discover/shows/by_genre/<with_genres>/<language>")
@plugin.route("/discover/shows/by_genre/<with_genres>/<language>/<page>")
def discover_shows(**kwargs):
    setContent(plugin.handle, SHOWS_TYPE)
    data = tmdb.Discover().tv(**kwargs)
    for show_li, show_id in tmdb.show_list_items_by_id(tmdb.get_ids(data)):
        addDirectoryItem(plugin.handle, plugin.url_for(handle_show, show_id), show_li, isFolder=True)
    handle_page(data, discover_shows, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/discover/people")
@plugin.route("/discover/people/<page>")
def discover_people(**kwargs):
    data = tmdb.People().popular(**kwargs)
    for person_li in tmdb.person_list_items(data):
        # TODO - show movies
        addDirectoryItem(plugin.handle, "", person_li, isFolder=True)
    handle_page(data, discover_people, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/movies")
def movies():
    pass


@plugin.route("/shows")
def shows():
    pass


@plugin.route("/search")
def search():
    pass


@plugin.route("/handle_show/<show_id>")
def handle_show(show_id):
    setContent(plugin.handle, SHOWS_TYPE)
    for season_li, season_number in tmdb.season_list_items(show_id):
        addDirectoryItem(plugin.handle, plugin.url_for(handle_season, show_id, season_number), season_li, isFolder=True)
    endOfDirectory(plugin.handle)


@plugin.route("/handle_season/<show_id>/<season_number>")
def handle_season(show_id, season_number):
    setContent(plugin.handle, EPISODES_TYPE)
    for episode_li, episode_number in tmdb.episodes_list_items(show_id, season_number):
        # TODO - call providers
        addDirectoryItem(plugin.handle, "", episode_li)
    endOfDirectory(plugin.handle)


@plugin.route("/play_trailer/<media_type>/<tmdb_id>")
@plugin.route("/play_trailer/<media_type>/<tmdb_id>/<season_number>")
@plugin.route("/play_trailer/<media_type>/<tmdb_id>/<season_number>/<episode_number>")
def play_trailer(media_type, tmdb_id, season_number=None, episode_number=None, language=None, fallback_language="en"):
    if media_type == "movie":
        tmdb_obj = tmdb.Movies(tmdb_id)
    elif media_type == "show":
        tmdb_obj = tmdb.TV(tmdb_id)
    elif media_type == "season":
        if season_number is None:
            logging.error("season_number attribute is required for seasons")
            return
        tmdb_obj = tmdb.TVSeasons(tmdb_id, season_number)
    elif media_type == "episode":
        if season_number is None or episode_number is None:
            logging.error("both season_number and episode_number attributes are required for episodes")
            return
        tmdb_obj = tmdb.TVEpisodes(tmdb_id, season_number, episode_number)
    else:
        logging.error("Invalid media type '%s' used", media_type)
        return

    if language is None:
        language = get_language()

    for result in tmdb_obj.videos(language=language)["results"]:
        if result["type"] == "Trailer" and result["site"] == "YouTube":
            executebuiltin("RunPlugin(plugin://plugin.video.youtube/?action=play_video&videoid={})".format(
                result["key"]))
            return

    if language == fallback_language:
        notification(translate(30108))
    else:
        play_trailer(
            media_type, tmdb_id,
            season_number=season_number,
            episode_number=episode_number,
            language=fallback_language,
            fallback_language=fallback_language)


def run():
    set_logger(level=logging.INFO)
    try:
        plugin.run()
    except Exception as e:
        logging.error("Caught exception:", exc_info=True)
        notification(str(e))
