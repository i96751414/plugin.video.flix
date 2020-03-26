import datetime

from simplecache import SimpleCache

from lib.api.flix.kodi import ADDON_ID
from lib.settings import get_cache_expiration_days


class KodiCache(object):
    def __init__(self):
        self._cache = SimpleCache()

    @staticmethod
    def _identifier(identifier):
        return "{}.{}".format(ADDON_ID, identifier)

    def get(self, identifier):
        return self._cache.get(self._identifier(identifier))

    def set(self, identifier, data):
        return self._cache.set(self._identifier(identifier), data,
                               expiration=datetime.timedelta(days=get_cache_expiration_days()))

    def close(self):
        self._cache.close()
