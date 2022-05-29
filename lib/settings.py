from lib.api.flix.kodi import get_boolean_setting, get_int_setting, get_setting, \
    get_language_iso_639_1, set_any_setting, translate_path


def is_cache_enabled():
    return get_boolean_setting("cache_enabled")


def is_search_history_enabled():
    return get_boolean_setting("enable_search_history")


def get_cache_expiration_days():
    return get_int_setting("cache_expiration")


def prefer_original_titles():
    return get_boolean_setting("prefer_original_titles")


def get_language():
    language = get_setting("language")
    if language == "Kodi":
        return get_language_iso_639_1()
    return language


def get_providers_timeout():
    return get_int_setting("providers_timeout")


def get_resolve_timeout():
    return get_int_setting("resolve_timeout")


def include_adult_content():
    return get_setting("include_adult_content")


def get_os_username():
    return get_setting("os_username")


def get_os_password():
    return get_setting("os_password")


def get_os_folder():
    return translate_path(get_setting("os_folder"))


def get_scraper_threads():
    return get_int_setting("scraper_threads")


def auto_choose_media():
    return get_boolean_setting("auto_choose_media")


def save_last_result():
    return get_boolean_setting("save_last_result")


def get_library_path():
    return translate_path(get_setting("library_path"))


def add_unaired_episodes():
    return get_boolean_setting("add_unaired_episodes")


def add_special_episodes():
    return get_boolean_setting("add_special_episodes")


def update_kodi_library():
    return get_boolean_setting("update_kodi_library")


def library_auto_update():
    return get_boolean_setting("library_auto_update")


def get_library_auto_update_rate():
    return get_int_setting("library_auto_update_rate") * 86400


def get_library_auto_update_last():
    return get_int_setting("library_auto_update_last")


def set_library_auto_update_last(value):
    set_any_setting("library_auto_update_last", value)


def library_auto_add():
    return get_boolean_setting("library_auto_add")


def get_library_auto_add_rate():
    return get_int_setting("library_auto_add_rate") * 86400


def library_auto_add_pages():
    return get_int_setting("library_auto_add_pages")


def get_library_auto_add_last():
    return get_int_setting("library_auto_add_last")


def set_library_auto_add_last(value):
    set_any_setting("library_auto_add_last", value)


def is_library_progress_enabled():
    return get_boolean_setting("enable_library_progress")


def propagate_view_type():
    return get_boolean_setting("propagate_view_type")


def show_unaired_episodes():
    return get_boolean_setting("show_unaired_episodes")
