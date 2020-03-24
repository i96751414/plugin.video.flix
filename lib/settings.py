from lib.kodi import get_boolean_setting, get_int_setting, get_setting


def is_cache_enabled():
    return get_boolean_setting("cache_enabled")


def get_cache_expiration_days():
    return get_int_setting("cache_expiration")


def prefer_original_titles():
    return get_boolean_setting("prefer_original_titles")


def get_language():
    return get_setting("language")
