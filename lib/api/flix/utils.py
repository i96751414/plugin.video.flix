"""
Module `utils` provides some compatibility utilities for both Python 2 and 3.

.. data:: PY3

    Indicates if running on Python 3+ (:class:`bool`).

.. data:: string_types

    Available string types for current Python version (:class:`type`).

.. function:: str_to_bytes(s)

    Convert string to bytes. This is a noop for Python 2.

.. function:: bytes_to_str(s)

    Convert bytes to string. This is a noop for Python 2.

.. function:: assure_unicode(s)

    Convert string to unicode if necessary. This is a noop for Python 3.

.. function:: assure_str(s)

    Convert unicode to string if necessary. This is a noop for Python 3.

"""

import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor

PY3 = sys.version_info.major >= 3
RESERVED_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*%+]')

if PY3:
    string_types = str

    def str_to_bytes(s):
        return s.encode()

    def bytes_to_str(b):
        return b.decode()

    def assure_unicode(s):
        return s

    def assure_str(s):
        return s

else:
    # noinspection PyUnresolvedReferences
    string_types = basestring  # noqa

    def str_to_bytes(s):
        return s

    def bytes_to_str(b):
        return b

    def assure_unicode(s):
        if isinstance(s, str):
            # noinspection PyUnresolvedReferences
            s = s.decode("utf-8")
        return s

    def assure_str(s):
        # noinspection PyUnresolvedReferences
        if isinstance(s, unicode):  # noqa
            s = s.encode("utf-8")
        return s


def get_data(func, iterable, threads=5, **kwargs):
    """
    Apply `func` to each element in `iterable`, collecting the results in a generator that is returned.

    :param func: The function to apply to each element.
    :param iterable: Iterable containing `func` inputs.
    :param threads: Number of workers.
    :keyword yield_exceptions: Yield (or not) exceptions. If not set, exceptions are raised.
    """
    yield_exceptions = kwargs.get("yield_exceptions")
    with ThreadPoolExecutor(threads) as pool:
        for result in [pool.submit(func, args) for args in iterable]:
            try:
                yield result.result()
            except Exception as e:
                if yield_exceptions is None:
                    raise e
                if yield_exceptions:
                    yield e
                else:
                    logging.error("Failed while performing get_data: %s", e, exc_info=True)


def make_legal_name(name):
    """
    Create a legal file name from the passed string.

    :param name: The name to make legal.
    :return: The legal file name.
    :rtype: str
    """
    return RESERVED_PATH_CHARS_RE.sub("", name)


def make_hash(obj, hash_func=hash):
    """
    Return the hash value for the given object.

    :param obj: The object which to calculate the hash.
    :param hash_func: Hash function to use.
    :return: The hash value.
    """
    if isinstance(obj, (tuple, list)):
        return hash_func((type(obj), tuple(make_hash(e, hash_func) for e in obj)))
    elif isinstance(obj, (set, frozenset)):
        return hash_func((type(obj), tuple(make_hash(e, hash_func) for e in sorted(obj))))
    elif isinstance(obj, dict):
        return hash_func((type(obj), tuple((k, make_hash(obj[k]), hash_func) for k in sorted(obj))))
    return hash_func(obj)


def args_rep(*args, **kwargs):
    """
    Return the representation of args and kwargs.

    :return: The representation string.
    :rtype: str
    """
    a = ", ".join(repr(a) for a in args)
    k = ", ".join(k + "=" + repr(kwargs[k]) for k in sorted(kwargs))
    s = ", " if a and k else ""
    return "(" + a + s + k + ")"
