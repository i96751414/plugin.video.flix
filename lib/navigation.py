import datetime
import logging
import os

# noinspection PyPackageRequirements
from routing import Plugin
from xbmc import executebuiltin
from xbmcgui import ListItem, Dialog
from xbmcplugin import addDirectoryItem, endOfDirectory, setContent

from lib import tmdb
from lib.api.flix.kodi import ADDON_PATH, ADDON_NAME, set_logger, notification, translate, Progress
from lib.providers import play_search, play_movie, play_episode
from lib.settings import get_language

MOVIES_TYPE = "movies"
SHOWS_TYPE = "tvshows"
EPISODES_TYPE = "episodes"

plugin = Plugin()
plugin.add_route(play_search, "/providers/play_search/<query>")
plugin.add_route(play_movie, "/providers/play_movie/<movie_id>")
plugin.add_route(play_episode, "/providers/play_episode/<show_id>/<season_number>/<episode_number>")


def progress(obj):
    return Progress(obj, heading=ADDON_NAME, message=translate(30110))


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


def add_person(person_li, person_id):
    addDirectoryItem(plugin.handle, plugin.url_for(handle_person, person_id), person_li, isFolder=True)


def add_movie(movie_id):
    addDirectoryItem(
        plugin.handle,
        plugin.url_for(play_movie, movie_id),
        tmdb.Movie(movie_id).to_list_item(playable=True),
    )


def add_show(show_id):
    addDirectoryItem(
        plugin.handle,
        plugin.url_for(handle_show, show_id),
        tmdb.Show(show_id).to_list_item(),
        isFolder=True,
    )


def add_season(season):
    addDirectoryItem(
        plugin.handle,
        plugin.url_for(handle_season, season.show_id, season.season_number),
        season.to_list_item(),
        isFolder=True,
    )


def add_episode(episode):
    addDirectoryItem(
        plugin.handle,
        plugin.url_for(play_episode, episode.show_id, episode.season_number, episode.episode_number),
        episode.to_list_item(playable=True),
    )


@plugin.route("/")
def index():
    addDirectoryItem(plugin.handle, plugin.url_for(discover), li(30100, "discover.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(movies), li(30101, "movies.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(shows), li(30102, "series.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(search), li(30103, "search.png"))
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
    for movie_id in progress(tmdb.get_ids(data)):
        add_movie(movie_id)
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
    for show_id in progress(tmdb.get_ids(data)):
        add_show(show_id)
    handle_page(data, discover_shows, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/discover/people")
@plugin.route("/discover/people/<page>")
def discover_people(**kwargs):
    data = tmdb.People().popular(**kwargs)
    for person_li, person_id in tmdb.person_list_items(data):
        add_person(person_li, person_id)
    handle_page(data, discover_people, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/movies")
def movies():
    addDirectoryItem(plugin.handle, plugin.url_for(trending_movies), li(30114, "trending.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(get_movies, "popular"), li(30115, "popular.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(get_movies, "top_rated"), li(30116, "top_rated.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(get_movies, "now_playing"), li(30117, "playing.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(get_movies, "upcoming"), li(30118, "upcoming.png"), isFolder=True)
    endOfDirectory(plugin.handle)


@plugin.route("/movies/trending")
@plugin.route("/movies/trending/<page>")
def trending_movies(**kwargs):
    setContent(plugin.handle, MOVIES_TYPE)
    data = tmdb.Trending("movie", "week").get_trending(**kwargs)
    for tmdb_id in progress(tmdb.get_ids(data)):
        add_movie(tmdb_id)
    handle_page(data, trending_movies, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/movies/get/<call>")
@plugin.route("/movies/get/<call>/<page>")
def get_movies(call, **kwargs):
    setContent(plugin.handle, MOVIES_TYPE)
    logging.debug("Going to call tmdb.Movies().%s()", call)
    data = getattr(tmdb.Movies(), call)(**kwargs)
    for tmdb_id in progress(tmdb.get_ids(data)):
        add_movie(tmdb_id)
    handle_page(data, get_movies, call=call, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/shows")
def shows():
    addDirectoryItem(plugin.handle, plugin.url_for(trending_shows), li(30119, "trending.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(get_shows, "popular"), li(30120, "popular.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(get_shows, "top_rated"), li(30121, "top_rated.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(get_shows, "airing_today"), li(30122, "playing.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(get_shows, "on_the_air"), li(30123, "upcoming.png"), isFolder=True)
    endOfDirectory(plugin.handle)


@plugin.route("/shows/trending")
@plugin.route("/shows/trending/<page>")
def trending_shows(**kwargs):
    setContent(plugin.handle, SHOWS_TYPE)
    data = tmdb.Trending("tv", "week").get_trending(**kwargs)
    for tmdb_id in progress(tmdb.get_ids(data)):
        add_show(tmdb_id)
    handle_page(data, trending_shows, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/shows/get/<call>")
@plugin.route("/shows/get/<call>/<page>")
def get_shows(call, **kwargs):
    setContent(plugin.handle, SHOWS_TYPE)
    logging.debug("Going to call tmdb.TV().%s()", call)
    data = getattr(tmdb.TV(), call)(**kwargs)
    for tmdb_id in progress(tmdb.get_ids(data)):
        add_show(tmdb_id)
    handle_page(data, get_shows, call=call, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/search")
def search():
    choice = Dialog().select(translate(30124), [translate(30125), translate(30126), translate(30127)])
    if choice == 0:
        query = Dialog().input(translate(30124) + ": " + translate(30125))
        search_type = "movie"
    elif choice == 1:
        query = Dialog().input(translate(30124) + ": " + translate(30126))
        search_type = "show"
    elif choice == 2:
        query = Dialog().input(translate(30124) + ": " + translate(30127))
        search_type = "person"
    else:
        return
    if query:
        container_update(handle_search, search_type, query)


@plugin.route("/search/<search_type>/<query>")
@plugin.route("/search/<search_type>/<query>/<page>")
def handle_search(search_type, **kwargs):
    if search_type == "movie":
        setContent(plugin.handle, MOVIES_TYPE)
        data = tmdb.Search().movie(**kwargs)
        for movie_id in progress(tmdb.get_ids(data)):
            add_movie(movie_id)
    elif search_type == "show":
        setContent(plugin.handle, SHOWS_TYPE)
        data = tmdb.Search().tv(**kwargs)
        for show_id in progress(tmdb.get_ids(data)):
            add_show(show_id)
    elif search_type == "person":
        data = tmdb.Search().person(**kwargs)
        for person_li, person_id in tmdb.person_list_items(data):
            add_person(person_li, person_id)
    else:
        logging.error("Invalid search type '%s' used", search_type)
        raise ValueError("Unknown search type")

    handle_page(data, handle_search, search_type=search_type, **kwargs)

    succeeded = tmdb.has_results(data)
    if not succeeded:
        notification(translate(30112))
    endOfDirectory(plugin.handle, succeeded)


@plugin.route("/handle_person/<person_id>")
def handle_person(person_id):
    for tmdb_id, is_movie, _ in progress(tmdb.get_person_credits(person_id)):
        add_movie(tmdb_id) if is_movie else add_show(tmdb_id)
    endOfDirectory(plugin.handle)


@plugin.route("/handle_show/<show_id>")
def handle_show(show_id):
    setContent(plugin.handle, SHOWS_TYPE)
    for season in tmdb.Show(show_id).seasons():
        add_season(season)
    endOfDirectory(plugin.handle)


@plugin.route("/handle_season/<show_id>/<season_number>")
def handle_season(show_id, season_number):
    setContent(plugin.handle, EPISODES_TYPE)
    for episode in tmdb.Season(show_id, season_number).episodes():
        add_episode(episode)
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
