import datetime
import logging
import os
import sqlite3
from functools import wraps

import tmdbsimple
# noinspection PyPackageRequirements
from routing import Plugin
from xbmc import executebuiltin
from xbmcgui import ListItem, Dialog
from xbmcplugin import addDirectoryItem, endOfDirectory, setContent, setResolvedUrl

from lib import tmdb
from lib.api.flix.kodi import ADDON_PATH, ADDON_NAME, set_logger, notification, translate, Progress, \
    container_refresh, get_current_view_id, set_view_mode, container_update, run_plugin
from lib.api.flix.utils import PY3
from lib.library import Library
from lib.providers import play_search, play_movie, play_show, play_season, play_episode
from lib.settings import get_language, include_adult_content, is_search_history_enabled, propagate_view_type, \
    show_unaired_episodes
from lib.storage import SearchHistory
from lib.subtitles import SubtitlesService

MOVIES_TYPE = "movies"
SHOWS_TYPE = "tvshows"
EPISODES_TYPE = "episodes"

SEARCH_STORE = "store"
SEARCH_UPDATE = "update"
SEARCH_EDIT = "edit"

VIEW_PROPERTY = "view"

set_logger()
plugin = Plugin()


def progress(obj, length=None):
    return Progress(obj, length=length, heading=ADDON_NAME, message=translate(30110))


def li(tid, icon):
    return list_item(translate(tid), icon)


def list_item(label, icon):
    icon_path = os.path.join(ADDON_PATH, "resources", "images", icon)
    item = ListItem(label)
    item.setArt({"icon": icon_path, "poster": icon_path})
    return item


def media(func, *args, **kwargs):
    return "PlayMedia({})".format(plugin.url_for(func, *args, **kwargs))


def action(func, *args, **kwargs):
    return "RunPlugin({})".format(plugin.url_for(func, *args, **kwargs))


def update(func, *args, **kwargs):
    return "Container.Update({})".format(plugin.url_for(func, *args, **kwargs))


def query_arg(name, required=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if name not in kwargs:
                query_list = plugin.args.get(name)
                if query_list:
                    kwargs[name] = query_list[0]
                elif required:
                    raise AttributeError("Missing {} required query argument".format(name))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def handle_view(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        view_list = plugin.args.get(VIEW_PROPERTY)
        ret = func(*args, **kwargs)
        if view_list:
            set_view_mode(view_list[0])
        return ret

    return wrapper


def handle_page(data, func, *args, **kwargs):
    page = int(kwargs.get("page", 1))
    total_pages = data["total_pages"] if isinstance(data, dict) else data
    if page < total_pages:
        kwargs["page"] = page + 1
        url = plugin.url_for(func, *args, **kwargs)
        propagate_view = propagate_view_type()
        if propagate_view:
            url = plugin.url_for(set_view, url=url)
        addDirectoryItem(plugin.handle, url, li(30105, "next.png"), isFolder=not propagate_view)


def plugin_update(func, *args, **kwargs):
    container_update(plugin.url_for(func, *args, **kwargs))


def add_person(person_li, person_id):
    addDirectoryItem(plugin.handle, plugin.url_for(handle_person, person_id), person_li, isFolder=True)


def add_movie(movie):
    item = movie.to_list_item(playable=True)
    item.addContextMenuItems([
        (translate(30144), update(similar_movies, movie.movie_id)),
        (translate(30133), action(library_add, MOVIES_TYPE, movie.movie_id)),
    ])
    addDirectoryItem(plugin.handle, plugin.url_for(play_movie, movie.movie_id), item)


def add_show(show):
    item = show.to_list_item()
    item.addContextMenuItems([
        (translate(30139), media(play_show, show.show_id)),
        (translate(30145), update(similar_shows, show.show_id)),
        (translate(30133), action(library_add, SHOWS_TYPE, show.show_id)),
    ])
    addDirectoryItem(plugin.handle, plugin.url_for(handle_show, show.show_id), item, isFolder=True)


def add_season(season):
    item = season.to_list_item()
    item.addContextMenuItems([
        (translate(30139), media(play_season, season.show_id, season.season_number)),
    ])
    addDirectoryItem(
        plugin.handle,
        plugin.url_for(
            handle_season,
            show_id=season.show_id,
            season_number=season.season_number,
            show_title=season.get_info("tvshowtitle")),
        item,
        isFolder=True,
    )


def add_episode(episode):
    addDirectoryItem(
        plugin.handle,
        plugin.url_for(play_episode, episode.show_id, episode.season_number, episode.episode_number),
        episode.to_list_item(playable=True),
    )


def play_youtube_video(video_id):
    p = "plugin://plugin.video.tubed/?mode=play&video_id=" if PY3 \
        else "plugin://plugin.video.youtube/play/?video_id="
    run_plugin(p + video_id)


@plugin.route("/")
def index():
    if "action" in plugin.args:
        with SubtitlesService(handle=plugin.handle, params=plugin.args) as s:
            s.run()
        return

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


def dialog_genres(media_type, kwargs):
    genres_handle = tmdbsimple.Genres().movie_list if media_type == MOVIES_TYPE else tmdbsimple.Genres().tv_list
    # noinspection PyArgumentList
    genres_dict = tmdb.get_genres_by_name(genres_handle(language=get_language()))
    genres_names = sorted(genres_dict.keys())
    selected_genres = Dialog().multiselect("{} - {}".format(translate(30100), translate(30106)), genres_names)
    has_selection = selected_genres is not None
    if has_selection:
        kwargs["with_genres"] = ",".join(str(genres_dict[genres_names[g]]) for g in selected_genres)
    return has_selection


def dialog_year(media_type, kwargs):
    years = [str(y) for y in range(datetime.datetime.now().year, 1900 - 1, -1)]
    selected_year = Dialog().select("{} - {}".format(translate(30100), translate(30107)), years)
    has_selection = selected_year >= 0
    if has_selection:
        kwargs["primary_release_year" if media_type == MOVIES_TYPE else "first_air_date_year"] = years[selected_year]
    return has_selection


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
        translate(30143),  # multiple filters
    ])
    if result < 0:
        return

    kwargs = {}
    if result == 1:
        if not dialog_genres(media_type, kwargs):
            return
    elif result == 2:
        if not dialog_year(media_type, kwargs):
            return
    elif result == 3:
        if not any([dialog(media_type, kwargs) for dialog in (dialog_year, dialog_genres)]):
            return

    plugin_update(handler, **kwargs)


@plugin.route("/discover/movies")
@query_arg("page", required=False)
@query_arg("primary_release_year", required=False)
@query_arg("with_genres", required=False)
@handle_view
def discover_movies(**kwargs):
    setContent(plugin.handle, MOVIES_TYPE)
    kwargs.setdefault("include_adult", include_adult_content())
    data = tmdbsimple.Discover().movie(**kwargs)
    for movie in progress(*tmdb.get_movies(data)):
        add_movie(movie)
    handle_page(data, discover_movies, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/discover/shows")
@query_arg("page", required=False)
@query_arg("first_air_date_year", required=False)
@query_arg("with_genres", required=False)
@handle_view
def discover_shows(**kwargs):
    setContent(plugin.handle, SHOWS_TYPE)
    kwargs.setdefault("include_adult", include_adult_content())
    data = tmdbsimple.Discover().tv(**kwargs)
    for show in progress(*tmdb.get_shows(data)):
        add_show(show)
    handle_page(data, discover_shows, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/discover/people")
@query_arg("page", required=False)
@handle_view
def discover_people(**kwargs):
    data = tmdbsimple.People().popular(**kwargs)
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
@query_arg("page", required=False)
@handle_view
def trending_movies(**kwargs):
    setContent(plugin.handle, MOVIES_TYPE)
    data = tmdb.Trending("movie", "week").get_trending(**kwargs)
    for movie in progress(*tmdb.get_movies(data)):
        add_movie(movie)
    handle_page(data, trending_movies, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/movies/similar/<tmdb_id>")
@query_arg("page", required=False)
@handle_view
def similar_movies(tmdb_id, **kwargs):
    setContent(plugin.handle, MOVIES_TYPE)
    data = tmdbsimple.Movies(tmdb_id).similar_movies(**kwargs)
    for movie in progress(*tmdb.get_movies(data)):
        add_movie(movie)
    handle_page(data, similar_movies, tmdb_id=tmdb_id, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/movies/get/<call>")
@query_arg("page", required=False)
@handle_view
def get_movies(call, **kwargs):
    setContent(plugin.handle, MOVIES_TYPE)
    logging.debug("Going to call tmdb.Movies().%s()", call)
    data = getattr(tmdbsimple.Movies(), call)(**kwargs)
    for movie in progress(*tmdb.get_movies(data)):
        add_movie(movie)
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
@query_arg("page", required=False)
@handle_view
def trending_shows(**kwargs):
    setContent(plugin.handle, SHOWS_TYPE)
    data = tmdb.Trending("tv", "week").get_trending(**kwargs)
    for show in progress(*tmdb.get_shows(data)):
        add_show(show)
    handle_page(data, trending_shows, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/shows/similar/<tmdb_id>")
@query_arg("page", required=False)
@handle_view
def similar_shows(tmdb_id, **kwargs):
    setContent(plugin.handle, SHOWS_TYPE)
    data = tmdbsimple.TV(tmdb_id).similar(**kwargs)
    for show in progress(*tmdb.get_shows(data)):
        add_show(show)
    handle_page(data, similar_shows, tmdb_id=tmdb_id, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/shows/get/<call>")
@query_arg("page", required=False)
@handle_view
def get_shows(call, **kwargs):
    setContent(plugin.handle, SHOWS_TYPE)
    logging.debug("Going to call tmdb.TV().%s()", call)
    data = getattr(tmdbsimple.TV(), call)(**kwargs)
    for show in progress(*tmdb.get_shows(data)):
        add_show(show)
    handle_page(data, get_shows, call=call, **kwargs)
    endOfDirectory(plugin.handle)


@plugin.route("/library/add/<media_type>/<tmdb_id>")
def library_add(media_type, tmdb_id):
    with Library() as library:
        if media_type == MOVIES_TYPE:
            added = library.add_movie(tmdb.Movie(tmdb_id))
        elif media_type == SHOWS_TYPE:
            added = library.add_show(tmdb.Show(tmdb_id))
        else:
            logging.error("Unknown media type '%s'", media_type)
            return
        notification(translate(30134 if added else 30137), time=2000, sound=False)


@plugin.route("/library/rebuild")
def library_rebuild():
    with Library() as library:
        library.rebuild()
        notification(translate(30138))


@plugin.route("/search")
def search():
    # 0 - movie, 1 - show, 2 - person, 3 - all
    search_type = Dialog().select(translate(30124), [translate(30125 + i) for i in range(4)])
    if search_type < 0:
        return
    if is_search_history_enabled():
        plugin_update(search_history, search_type)
    else:
        do_query(search_type)


@plugin.route("/search_history/<search_type>")
@query_arg("page", required=False)
@handle_view
def search_history(search_type, page=1):
    search_type = int(search_type)
    page = int(page)
    with SearchHistory() as s:
        addDirectoryItem(
            plugin.handle,
            plugin.url_for(do_query, search_type=search_type, search_action=SEARCH_STORE),
            li(30130, "new_search.png"),
        )
        for search_id, query in s.get_page(search_type, page):
            item = list_item(query, "search.png")
            item.addContextMenuItems([
                (translate(30131), action(delete_search_entry, search_id)),
                (translate(30136), action(do_query, search_type=search_type, search_action=SEARCH_EDIT, query=query)),
            ])
            addDirectoryItem(
                plugin.handle,
                plugin.url_for(do_query, search_type=search_type, search_action=SEARCH_UPDATE, query=query),
                item,
            )
        handle_page(s.pages_count(search_type), search_history, search_type=search_type, page=page)
    endOfDirectory(plugin.handle)


@plugin.route("/search_entry/delete/<search_id>")
def delete_search_entry(search_id):
    with SearchHistory() as s:
        s.delete_entry_by_id(int(search_id))
    container_refresh()


@plugin.route("/clear_search_history")
def clear_search_history():
    with SearchHistory() as s:
        s.clear_entries()
    notification(translate(30132))


@plugin.route("/query/<search_type>")
@query_arg("search_action", required=False)
@query_arg("query", required=False)
def do_query(search_type, query=None, search_action=None):
    search_type = int(search_type)
    old_query = query
    if query is None:
        query = Dialog().input(translate(30124) + ": " + translate(30125 + search_type))
    elif search_action == SEARCH_EDIT:
        query = Dialog().input(translate(30124) + ": " + translate(30125 + search_type), defaultt=old_query)
    if query:
        if search_action == SEARCH_STORE:
            with SearchHistory() as s:
                try:
                    s.add_entry(search_type, query)
                except sqlite3.IntegrityError:
                    # In case the query already exists, just update the timestamp
                    s.update_entry(search_type, query, query)
        elif search_action == SEARCH_UPDATE:
            with SearchHistory() as s:
                s.update_entry(search_type, query, query)
        elif search_action == SEARCH_EDIT:
            if old_query is None:
                return
            with SearchHistory() as s:
                try:
                    s.update_entry(search_type, old_query, query)
                except sqlite3.IntegrityError:
                    # In case the new query already exists, ignore
                    pass

        if search_type == 3:
            executebuiltin(media(play_query, query=query))
            if search_action in (SEARCH_STORE, SEARCH_UPDATE, SEARCH_EDIT):
                container_refresh()
        else:
            plugin_update(handle_search, search_type=search_type, query=query)


@plugin.route("/search/<search_type>")
@query_arg("page", required=False)
@query_arg("query")
@handle_view
def handle_search(search_type, **kwargs):
    search_type = int(search_type)
    kwargs.setdefault("include_adult", include_adult_content())
    if search_type == 0:
        setContent(plugin.handle, MOVIES_TYPE)
        data = tmdbsimple.Search().movie(**kwargs)
        for movie in progress(*tmdb.get_movies(data)):
            add_movie(movie)
    elif search_type == 1:
        setContent(plugin.handle, SHOWS_TYPE)
        data = tmdbsimple.Search().tv(**kwargs)
        for show in progress(*tmdb.get_shows(data)):
            add_show(show)
    elif search_type == 2:
        data = tmdbsimple.Search().person(**kwargs)
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
    for m, is_movie in progress(*tmdb.get_person_media(person_id)):
        add_movie(m) if is_movie else add_show(m)
    endOfDirectory(plugin.handle)


@plugin.route("/handle_show/<show_id>")
def handle_show(show_id):
    setContent(plugin.handle, SHOWS_TYPE)
    for season in tmdb.Show(show_id).seasons(get_unaired=show_unaired_episodes()):
        add_season(season)
    endOfDirectory(plugin.handle)


@plugin.route("/handle_season/<show_id>/<season_number>")
@query_arg("show_title", required=False)
def handle_season(show_id, season_number, show_title=None):
    setContent(plugin.handle, EPISODES_TYPE)
    for episode in tmdb.Season(show_id, season_number, show_title).episodes(get_unaired=show_unaired_episodes()):
        add_episode(episode)
    endOfDirectory(plugin.handle)


@plugin.route("/play_trailer/<media_type>/<tmdb_id>")
@plugin.route("/play_trailer/<media_type>/<tmdb_id>/<season_number>")
@plugin.route("/play_trailer/<media_type>/<tmdb_id>/<season_number>/<episode_number>")
def play_trailer(media_type, tmdb_id, season_number=None, episode_number=None, language=None, fallback_language="en"):
    if media_type == "movie":
        tmdb_obj = tmdbsimple.Movies(tmdb_id)
    elif media_type == "show":
        tmdb_obj = tmdbsimple.TV(tmdb_id)
    elif media_type == "season":
        if season_number is None:
            logging.error("season_number attribute is required for seasons")
            return
        tmdb_obj = tmdbsimple.TV_Seasons(tmdb_id, season_number)
    elif media_type == "episode":
        if season_number is None or episode_number is None:
            logging.error("both season_number and episode_number attributes are required for episodes")
            return
        tmdb_obj = tmdbsimple.TV_Episodes(tmdb_id, season_number, episode_number)
    else:
        logging.error("Invalid media type '%s' used", media_type)
        return

    if language is None:
        language = get_language()

    for result in tmdb_obj.videos(language=language)["results"]:
        if result["type"] == "Trailer" and result["site"] == "YouTube":
            play_youtube_video(result["key"])
            return

    if language == fallback_language:
        notification(translate(30108))
        setResolvedUrl(plugin.handle, False, ListItem())
    else:
        play_trailer(
            media_type, tmdb_id,
            season_number=season_number,
            episode_number=episode_number,
            language=fallback_language,
            fallback_language=fallback_language)


@plugin.route("/providers/play_query")
@query_arg("query")
def play_query(query):
    play_search(query)


@plugin.route("/set_view")
@query_arg("url")
def set_view(url):
    container_update(url + ("&" if "?" in url else "?") + VIEW_PROPERTY + "=" + str(get_current_view_id()))


plugin.add_route(play_movie, "/providers/play_movie/<movie_id>")
plugin.add_route(play_show, "/providers/play_show/<show_id>")
plugin.add_route(play_season, "/providers/play_season/<show_id>/<season_number>")
plugin.add_route(play_episode, "/providers/play_episode/<show_id>/<season_number>/<episode_number>")


def run():
    try:
        plugin.run()
    except Exception as e:
        logging.error("Caught exception:", exc_info=True)
        notification(str(e))
