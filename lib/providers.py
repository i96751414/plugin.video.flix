import logging
import sys

from xbmcgui import DialogProgressBG, ListItem
from xbmcplugin import setResolvedUrl

from lib.api.flix.kodi import ADDON_NAME, Busy, translate, notification
# noinspection PyProtectedMember
from lib.api.flix.provider import get_providers, send_to_providers, ProviderListener, ProviderResult
from lib.dialog_select import dialog_select
from lib.settings import get_providers_timeout, get_resolve_timeout
from lib.tmdb import VideoItem, Movie, Show, Season


class ResolveTimeoutError(Exception):
    pass


class ProviderListenerDialog(ProviderListener):
    def __init__(self, providers, method, timeout=10):
        super(ProviderListenerDialog, self).__init__(providers, method, timeout=timeout)
        self._total = len(providers)
        self._count = 0
        self._dialog = DialogProgressBG()

    def on_receive(self, sender):
        self._count += 1
        self._dialog.update(int(100 * self._count / self._total))

    def __enter__(self):
        self._dialog.create(ADDON_NAME, translate(30111))
        return super(ProviderListenerDialog, self).__enter__()

    def __exit__(self, *args, **kwargs):
        self._dialog.close()
        return super(ProviderListenerDialog, self).__exit__(*args, **kwargs)


def run_providers_method(timeout, method, *args, **kwargs):
    providers = get_providers()
    with ProviderListenerDialog(providers, method, timeout=timeout) as listener:
        send_to_providers(providers, method, *args, **kwargs)
    return listener.data


def run_provider_method(provider, timeout, method, *args, **kwargs):
    with ProviderListener((provider,), method, timeout=timeout) as listener:
        send_to_providers((provider,), method, *args, **kwargs)
    try:
        return listener.data[provider]
    except KeyError:
        raise ResolveTimeoutError("Timeout reached")


def get_providers_results(method, *args, **kwargs):
    results = []
    data = run_providers_method(get_providers_timeout(), method, *args, **kwargs)
    for provider, provider_results in data.items():
        if not isinstance(provider_results, (tuple, list)):
            logging.error("Expecting list or tuple as results for %s:%s", provider, method)
            continue
        for provider_result in provider_results:
            try:
                _provider_result = ProviderResult(provider_result)
            except Exception as e:
                logging.error("Invalid format on provider '%s' result (%s): %s", provider, provider_result, e)
            else:
                if _provider_result.url or _provider_result.provider_data:
                    results.append((provider, _provider_result))
    return results


def play(item, method, *args, **kwargs):
    with Busy():
        results = get_providers_results(method, *args, **kwargs)
    handle = int(sys.argv[1])
    if results:
        dialog = dialog_select(translate(30113))
        for provider, provider_result in results:
            try:
                dialog.add_item(label=provider_result.label, label2=provider_result.label2, icon=provider_result.icon)
            except Exception as e:
                logging.error("Invalid result from provider %s: %s", provider, e, exc_info=True)
        dialog.doModal()
        if dialog.selected >= 0:
            provider, provider_result = results[dialog.selected]
            if provider_result.url:
                logging.debug("Going to play url '%s' from provider %s", provider_result.url, provider)
                setResolvedUrl(handle, True, item.to_list_item(path=provider_result.url))
            else:
                logging.debug("Need to call 'resolve' from provider %s", provider)
                try:
                    url = run_provider_method(provider, get_resolve_timeout(), "resolve", provider_result.provider_data)
                except ResolveTimeoutError:
                    logging.warning("Provider %s took too much time to resolve", provider)
                    setResolvedUrl(handle, False, ListItem())
                    notification(translate(30129))
                else:
                    logging.debug("Going to play resolved url '%s' from provider %s", url, provider)
                    setResolvedUrl(handle, True, item.to_list_item(path=url))
    else:
        setResolvedUrl(handle, False, ListItem())
        notification(translate(30112))


def play_search(query):
    play(VideoItem(title=query, art={"icon": "DefaultVideo.png"}), "search", query)


def play_movie(movie_id):
    item = Movie(movie_id)
    year = item.get_info("year")
    year = int(year) if year else None
    play(item, "search_movie", movie_id, item.get_info("originaltitle"), item.alternative_titles, year=year)


def play_episode(show_id, season_number, episode_number):
    show = Show(show_id)
    play(
        Season(show_id, season_number).get_episode(episode_number),
        "search_episode",
        show_id,
        show.get_info("originaltitle"),
        season_number,
        episode_number,
        show.alternative_titles,
    )
