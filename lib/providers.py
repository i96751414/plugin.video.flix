# noinspection PyProtectedMember
from lib.api.flix.provider import get_providers, send_to_providers, ProviderListener
from lib.settings import get_providers_timeout


def run_providers_method(method, *args, **kwargs):
    providers = get_providers()
    with ProviderListener(providers, method, timeout=get_providers_timeout()) as listener:
        send_to_providers(providers, method, *args, **kwargs)
    return listener.data
