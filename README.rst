Flix
====

.. image:: https://readthedocs.org/projects/flix/badge/?version=latest
    :target: https://flix.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

Flix, a movie scraper for `Kodi`_. It uses `TMDB`_ api for scraping data and allows for custom providers.

.. _Kodi: https://kodi.tv
.. _TMDB: https://www.themoviedb.org/

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
- Implement the `Provider` API: see `flix.provider.Provider <https://flix.readthedocs.io/en/latest/flix_api.html#flix.provider.Provider>`_.

Installation
------------

Get the latest release from `github <https://github.com/i96751414/plugin.video.flix/archive/master.zip>`_ and `Install from zip <https://kodi.wiki/view/Add-on_manager#How_to_install_from_a_ZIP_file>`_ within Kodi_.

Screenshots
-----------

.. image:: https://raw.githubusercontent.com/i96751414/plugin.video.flix/master/resources/screenshots/screenshot-1.jpg
    :alt: Screenshot 1

.. image:: https://raw.githubusercontent.com/i96751414/plugin.video.flix/master/resources/screenshots/screenshot-2.jpg
    :alt: Screenshot 2

.. image:: https://raw.githubusercontent.com/i96751414/plugin.video.flix/master/resources/screenshots/screenshot-3.jpg
    :alt: Screenshot 3
