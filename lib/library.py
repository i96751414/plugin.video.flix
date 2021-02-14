import logging
import os
import time
from threading import Lock

from tmdbsimple import Discover
from xbmc import Monitor

from lib.api.flix.kodi import ADDON_ID, ADDON_NAME, translate, Progress, update_library, clean_library
from lib.api.flix.utils import make_legal_name
from lib.settings import get_library_path, add_special_episodes, add_unaired_episodes, update_kodi_library, \
    include_adult_content, is_library_progress_enabled
from lib.storage import Storage
from lib.tmdb import Season, Movie, Show, get_movies, get_shows


class LibraryMonitor(Monitor):
    def __init__(self, library="video"):
        super(LibraryMonitor, self).__init__()
        self._library = library
        self._lock = Lock()
        self._scan_started = self._scan_finished = False
        self._clean_started = self._clean_finished = False

    def onScanStarted(self, library):
        self._on_action("_scan_started", library)

    def onScanFinished(self, library):
        self._on_action("_scan_finished", library)

    def onCleanStarted(self, library):
        self._on_action("_clean_started", library)

    def onCleanFinished(self, library):
        self._on_action("_clean_finished", library)

    def _on_action(self, attr, library):
        if library == self._library:
            with self._lock:
                setattr(self, attr, True)
                logging.debug("%s on %s library", attr, library)

    def wait_scan_start(self, timeout=0):
        return self._wait("_scan_started", timeout)

    def wait_scan_finish(self, timeout=0):
        return self._wait("_scan_finished", timeout)

    def wait_clean_start(self, timeout=0):
        return self._wait("_clean_started", timeout)

    def wait_clean_finish(self, timeout=0):
        return self._wait("_clean_finished", timeout)

    def _wait(self, attr, timeout):
        start_time = time.time()
        while not getattr(self, attr) and not self.waitForAbort(1):
            if 0 < timeout < time.time() - start_time:
                return False
        return True

    def start_scan(self, path=None, wait=False):
        logging.debug("Starting scan with path='%s' and wait=%s", path, wait)
        with self._lock:
            self._scan_started = self._scan_finished = False
            update_library(self._library, path)
        if wait:
            if self.wait_scan_start(10):
                self.wait_scan_finish()

    def clean_library(self, wait=False):
        logging.debug("Cleaning library with wait=%s", wait)
        with self._lock:
            self._clean_started = self._clean_finished = False
            clean_library(self._library)
        if wait:
            if self.wait_clean_start(10):
                self.wait_clean_finish()


class Library(object):
    MOVIE_TYPE = "movie"
    SHOW_TYPE = "show"

    def __init__(self):
        self._directory = get_library_path()
        if not os.path.isdir(self._directory):
            raise ValueError(translate(30135))

        self._add_unaired_episodes = add_unaired_episodes()
        self._add_specials = add_special_episodes()
        self._update_kodi_library = update_kodi_library()
        self._movies_directory = os.path.join(self._directory, "Movies")
        self._shows_directory = os.path.join(self._directory, "TV Shows")

        if not os.path.exists(self._movies_directory):
            os.makedirs(self._movies_directory)
        if not os.path.exists(self._shows_directory):
            os.makedirs(self._shows_directory)

        self._storage = Storage(os.path.join(self._directory, "library.sqlite"))
        self._table_name = "library"
        self._storage.execute_and_commit(
            "CREATE TABLE IF NOT EXISTS `{}` ("
            "id INTEGER NOT NULL, "
            "type TEXT NOT NULL, "
            "path TEXT CHECK(path <> '') NOT NULL, "
            "PRIMARY KEY (id, type)"
            ");".format(self._table_name))

    def _storage_has_item(self, item_id, item_type):
        return self._storage_get_path(item_id, item_type) is not None

    def _storage_get_path(self, item_id, item_type):
        row = self._storage.execute(
            "SELECT path FROM `{}` WHERE id = ? AND type = ?;".format(self._table_name),
            (item_id, item_type)).fetchone()
        return row and row[0]

    def _storage_count_entries(self):
        return self._storage.count(self._table_name)

    def _storage_get_entries(self):
        return self._storage.fetch_items("SELECT * FROM `{}`;".format(self._table_name))

    def _storage_count_entries_by_type(self, item_type):
        return self._storage.execute(
            "SELECT COUNT(*) FROM `{}` WHERE type = ?;".format(self._table_name), (item_type,)).fetchone()[0]

    def _storage_get_entries_by_type(self, item_type):
        return self._storage.fetch_items(
            "SELECT id, path FROM `{}` WHERE type = ?;".format(self._table_name), (item_type,))

    def _storage_add_item(self, item_id, item_type, path):
        self._storage.execute_and_commit(
            "INSERT INTO `{}` (id, type, path) VALUES(?, ?, ?);".format(self._table_name),
            (item_id, item_type, path))

    def _add_movie(self, item, name, override_if_exists=True):
        movie_dir = os.path.join(self._movies_directory, name)
        if not os.path.isdir(movie_dir):
            os.makedirs(movie_dir)

        movie_path = os.path.join(movie_dir, name + ".strm")
        if override_if_exists or not os.path.exists(movie_path):
            with open(movie_path, "w") as f:
                f.write("plugin://{}/providers/play_movie/{}".format(ADDON_ID, item.movie_id))

    def add_movie(self, item):
        if self._storage_has_item(item.movie_id, self.MOVIE_TYPE):
            logging.debug("Movie %s was previously added", item.movie_id)
            return False

        name = item.get_info("originaltitle")
        year = item.get_info("year")
        if year:
            name += " ({})".format(year)
        name = make_legal_name(name)

        self._add_movie(item, name)
        self._storage_add_item(item.movie_id, self.MOVIE_TYPE, name)
        if self._update_kodi_library:
            self.update_movies()

        return True

    def _add_show(self, item, name, override_if_exists=True):
        show_dir = os.path.join(self._shows_directory, name)
        if not os.path.isdir(show_dir):
            os.makedirs(show_dir)

        for season in item.seasons(get_unaired=self._add_unaired_episodes):
            if not self._add_specials and season.season_number == 0:
                continue
            for episode in Season(item.show_id, season.season_number).episodes(get_unaired=self._add_unaired_episodes):
                episode_name = u"{} S{:02d}E{:02d}".format(name, episode.season_number, episode.episode_number)
                episode_path = os.path.join(show_dir, episode_name + ".strm")
                if override_if_exists or not os.path.exists(episode_path):
                    with open(episode_path, "w") as f:
                        f.write("plugin://{}/providers/play_episode/{}/{}/{}".format(
                            ADDON_ID, episode.show_id, episode.season_number, episode.episode_number))

    def add_show(self, item):
        if self._storage_has_item(item.show_id, self.SHOW_TYPE):
            logging.debug("Show %s was previously added", item.show_id)
            return False

        name = item.get_info("originaltitle")
        year = item.get_info("year")
        if year:
            name += " ({})".format(year)
        name = make_legal_name(name)

        self._add_show(item, name)
        self._storage_add_item(item.show_id, self.SHOW_TYPE, name)
        if self._update_kodi_library:
            self.update_shows()

        return True

    def rebuild(self):
        items_iter = self._storage_get_entries()
        if is_library_progress_enabled():
            items_iter = Progress(items_iter, self._storage_count_entries(),
                                  heading=ADDON_NAME, message=translate(30142))
        for item_id, item_type, path in items_iter:
            if item_type == self.MOVIE_TYPE:
                self._add_movie(Movie(item_id), path)
            elif item_type == self.SHOW_TYPE:
                self._add_show(Show(item_id), path)
            else:
                logging.error("Unknown item type '%s' for id '%s' and path '%s'", item_type, item_id, path)

        if self._update_kodi_library:
            self.update_movies(wait=True)
            self.update_shows(wait=True)

    def update_library(self):
        items_iter = self._storage_get_entries_by_type(self.SHOW_TYPE)
        if is_library_progress_enabled():
            items_iter = Progress(items_iter, self._storage_count_entries_by_type(self.SHOW_TYPE),
                                  heading=ADDON_NAME, message=translate(30141))
        for item_id, path in items_iter:
            logging.debug("Updating show %s on %s", item_id, path)
            self._add_show(Show(item_id), path, override_if_exists=False)
        if self._update_kodi_library:
            self.update_movies(wait=True)
            self.update_shows(wait=True)

    def discover_contents(self, pages):
        include_adult = include_adult_content()
        api = Discover()
        pages_iter = range(1, pages + 1)
        if is_library_progress_enabled():
            pages_iter = Progress(pages_iter, pages, heading=ADDON_NAME, message=translate(30140))
        for page in pages_iter:
            for movie in get_movies(api.movie(page=page, include_adult=include_adult))[0]:
                logging.debug("Adding movie %s to library", movie.movie_id)
                self.add_movie(movie)
            for show in get_shows(api.tv(page=page, include_adult=include_adult))[0]:
                logging.debug("Adding show %s to library", show.show_id)
                self.add_show(show)
        if self._update_kodi_library:
            self.update_movies(wait=True)
            self.update_shows(wait=True)

    def update_shows(self, wait=False):
        LibraryMonitor().start_scan(self._shows_directory, wait)

    def update_movies(self, wait=False):
        LibraryMonitor().start_scan(self._movies_directory, wait)

    def close(self):
        self._storage.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
