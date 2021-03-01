import importlib
import os
import sys
from xml.etree import ElementTree  # nosec

import xbmc
import xbmcaddon

PY3 = sys.version_info.major >= 3


class UndefinedModuleError(ImportError):
    pass


def register_module(name, py2_module=None, py3_module=None):
    try:
        importlib.import_module(name)
        xbmc.log("{} module is already installed".format(name), xbmc.LOGDEBUG)
    except ImportError:
        xbmc.log("Failed to import module. Going to register it.", xbmc.LOGDEBUG)
        module = py3_module if PY3 else py2_module
        if module is None:
            raise UndefinedModuleError("No module was defined")
        install_and_register_module(name, module)


def install_and_register_module(name, module):
    xbmc.log("Installing and registering module {}:{}".format(name, module), xbmc.LOGINFO)
    xbmc.executebuiltin("InstallAddon(" + module + ")", wait=True)
    path = xbmcaddon.Addon(module).getAddonInfo("path")
    if not PY3:
        # noinspection PyUnresolvedReferences
        path = path.decode("utf-8")
    tree = ElementTree.parse(os.path.join(path, "addon.xml"))
    library_path = tree.find("./extension[@point='xbmc.python.module']").attrib["library"]
    sys.path.append(os.path.join(path, library_path))
