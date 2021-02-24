import os

import dependencies  # noqa, pylint: disable=unused-import
from lib.api.flix.kodi import ADDON_DATA
from lib.navigation import run

if not os.path.exists(ADDON_DATA):
    os.makedirs(ADDON_DATA)

run()
