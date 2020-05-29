import os
import time
from datetime import datetime

from xbmc import makeLegalFilename, executebuiltin

from lib.api.flix.kodi import ADDON_ID
from lib.tmdb import Season


class Library(object):
    def __init__(self, directory, add_unaired_episodes=False, add_specials=False, update_library=False):
        if not os.path.isdir(directory):
            raise ValueError("Library directory does not exist")

        self._directory = directory
        self._add_unaired_episodes = add_unaired_episodes
        self._add_specials = add_specials
        self._update_library = update_library
        self._movies_directory = os.path.join(self._directory, "Movies")
        self._shows_directory = os.path.join(self._directory, "TV Shows")

        if not os.path.exists(self._movies_directory):
            os.makedirs(self._movies_directory)
        if not os.path.exists(self._shows_directory):
            os.makedirs(self._shows_directory)

    def add_movie(self, item):
        name = item.get_info("originaltitle")
        year = item.get_info("year")
        if year:
            name += " ({})".format(year)

        movie_path = os.path.join(self._movies_directory, name)
        if not os.path.isdir(movie_path):
            os.makedirs(movie_path)

        with open(makeLegalFilename(os.path.join(movie_path, name + ".strm")), "w") as f:
            f.write("plugin://{}/providers/play_movie/{}".format(ADDON_ID, item.movie_id))

        if self._update_library:
            self.update_movies()

    def add_show(self, item):
        show_title = item.get_info("originaltitle")
        year = item.get_info("year")
        show_folder = show_title
        if year:
            show_folder += " ({})".format(year)

        show_path = os.path.join(self._shows_directory, show_folder)
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

                name = "{} S{:02d}E{:02d}".format(show_title, episode.season_number, episode.episode_number)
                with open(makeLegalFilename(os.path.join(show_path, name + ".strm")), "w") as f:
                    f.write("plugin://{}/providers/play_episode/{}/{}/{}".format(
                        ADDON_ID, episode.show_id, episode.season_number, episode.episode_number))

        if self._update_library:
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
