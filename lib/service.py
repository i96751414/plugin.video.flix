import time

import xbmc

from lib import settings
from lib.api.flix.kodi import set_logger
from lib.library import Library


class LibraryMonitor(xbmc.Monitor):
    def watch(self):
        while True:
            if (settings.library_auto_update() and
                    settings.get_library_auto_update_last() + settings.get_library_auto_add_rate() < time.time()):
                with Library() as library:
                    library.update_library()
                settings.set_library_auto_update_last(int(time.time()))

            if (settings.library_auto_add() and
                    settings.get_library_auto_add_last() + settings.get_library_auto_add_rate() < time.time()):
                with Library() as library:
                    library.discover_contents(settings.library_auto_add_pages())
                settings.set_library_auto_add_last(int(time.time()))

            if self.waitForAbort(3600):
                return


def run(delay=10):
    set_logger()
    monitor = LibraryMonitor()
    if not monitor.waitForAbort(delay):
        monitor.watch()
