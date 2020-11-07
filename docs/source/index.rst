Welcome to Flix's documentation!
================================

Flix, a movie scraper for `Kodi`_. It uses `TMDB`_ api for scraping data and allows for custom providers.

.. _Kodi: https://kodi.tv
.. _TMDB: https://www.themoviedb.org/

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   license
   flix_api

Features
--------

- Cross-platform.
- No extra service running in the background.
- Use of `TMDB`_ api for scraping data.
- Cache all api calls (this can be disabled in settings).
- Use of providers, if any, for playing media.
- Use of `OpenSubtitles <https://www.opensubtitles.org/>`_ api for searching subtitles.

What is a provider?
-------------------

Providers are normal `Kodi`_ script `addons <https://kodi.wiki/view/Add-ons>`_ and thus can be installed/updated/distributed just like any other addon.
However, a provider must follow a set of rules:

- The provider name must follow the format **script.flix.{name}**, otherwise it won't be discovered.
- Provide a `xbmc.python.script` extension point: see `this <https://kodi.wiki/view/HOW-TO:Script_addon>`_.
- Implement the `Provider` API: see :class:`flix.provider.Provider`.

See `script.flix.dummy <https://github.com/i96751414/script.flix.dummy>`_, a dummy provider mainly used for testing providers integration.

Installation
------------

Get the latest release from `github <https://github.com/i96751414/plugin.video.flix/releases/latest>`_ and `Install from zip <https://kodi.wiki/view/Add-on_manager#How_to_install_from_a_ZIP_file>`_ within Kodi_.

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
