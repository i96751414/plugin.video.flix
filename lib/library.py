import logging
import os
import time
from datetime import datetime

from xbmc import executebuiltin

from lib.api.flix.kodi import ADDON_ID, translate
from lib.api.flix.utils import make_legal_name
from lib.settings import get_library_path, add_special_episodes, add_unaired_episodes, update_library
from lib.storage import Storage
from lib.tmdb import Season, Movie, Show


class Library(object):
    MOVIE_TYPE = "movie"
    SHOW_TYPE = "show"

    def __init__(self):
        self._directory = get_library_path()
        if not os.path.isdir(self._directory):
            raise ValueError(translate(30135))

        self._add_unaired_episodes = add_unaired_episodes()
        self._add_specials = add_special_episodes()
        self._update_library = update_library()
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
            ")".format(self._table_name))

    def _storage_has_item(self, item_id, item_type):
        return self._storage_get_path(item_id, item_type) is not None

    def _storage_get_path(self, item_id, item_type):
        row = self._storage.execute(
            "SELECT path FROM `{}` WHERE id = ? AND type = ?;".format(self._table_name),
            (item_id, item_type)).fetchone()
        return row and row[0]

    def _storage_get_entries(self):
        return self._storage.get_all_iter_items(self._table_name, 20)

    def _storage_add_item(self, item_id, item_type, path):
        self._storage.execute_and_commit(
            "INSERT INTO `{}` (id, type, path) VALUES(?, ?, ?);".format(self._table_name),
            (item_id, item_type, path))

    def _add_movie(self, item, name):
        movie_path = os.path.join(self._movies_directory, name)
        if not os.path.isdir(movie_path):
            os.makedirs(movie_path)

        with open(os.path.join(movie_path, name + ".strm"), "w") as f:
            f.write("plugin://{}/providers/play_movie/{}".format(ADDON_ID, item.movie_id))

    def add_movie(self, item):
        if self._storage_has_item(item.movie_id, self.MOVIE_TYPE):
            logging.error("Movie %s was previously added", item.movie_id)
            return False

        name = item.get_info("originaltitle")
        year = item.get_info("year")
        if year:
            name += " ({})".format(year)
        name = make_legal_name(name)

        self._add_movie(item, name)
        self._storage_add_item(item.movie_id, self.MOVIE_TYPE, name)
        if self._update_library:
            self.update_movies()

        return True

    def _add_show(self, item, name):
        show_path = os.path.join(self._shows_directory, name)
        if not os.path.isdir(show_path):
            os.makedirs(show_path)

        now = datetime.now()
        for season in item.seasons():
            if not self._add_specials and season.season_number == 0:
                continue
            if not self._add_unaired_episodes:
                air_date = season.get_info("premiered")
                if not air_date or datetime(*time.strptime(air_date, "%Y-%m-%d")[:6]) > now:
                    continue
            for episode in Season(item.show_id, season.season_number).episodes():
                if not self._add_unaired_episodes:
                    air_date = episode.get_info("aired")
                    if not air_date or datetime(*time.strptime(air_date, "%Y-%m-%d")[:6]) > now:
                        continue

                episode_name = "{} S{:02d}E{:02d}".format(name, episode.season_number, episode.episode_number)
                with open(os.path.join(show_path, episode_name + ".strm"), "w") as f:
                    f.write("plugin://{}/providers/play_episode/{}/{}/{}".format(
                        ADDON_ID, episode.show_id, episode.season_number, episode.episode_number))

    def add_show(self, item):
        if self._storage_has_item(item.show_id, self.SHOW_TYPE):
            logging.error("Show %s was previously added", item.show_id)
            return False

        name = item.get_info("originaltitle")
        year = item.get_info("year")
        if year:
            name += " ({})".format(year)
        name = make_legal_name(name)

        self._add_show(item, name)
        self._storage_add_item(item.show_id, self.SHOW_TYPE, name)
        if self._update_library:
            self.update_shows()

        return True

    def rebuild(self):
        for item_id, item_type, path in self._storage_get_entries():
            if item_type == self.MOVIE_TYPE:
                self._add_movie(Movie(item_id), path)
            elif item_type == self.SHOW_TYPE:
                self._add_show(Show(item_id), path)
            else:
                logging.error("Unknown item type '%s' for id '%' and path '%s'", item_type, item_id, path)

        if self._update_library:
            self.update_movies()
            self.update_shows()

    @staticmethod
    def update_library(path=None):
        args = ["video"]
        if path:
            args.append(path)
        executebuiltin("UpdateLibrary(" + ",".join(args) + ")")

    def update_shows(self):
        self.update_library(self._shows_directory)

    def update_movies(self):
        self.update_library(self._movies_directory)

    @staticmethod
    def clean_library():
        executebuiltin("CleanLibrary(video)")

    def close(self):
        self._storage.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
