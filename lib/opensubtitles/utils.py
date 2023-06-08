import logging
import os
import re
import struct
from io import FileIO

import requests


class DataStruct(object):
    ARRAY_TYPES = (list, tuple)

    @classmethod
    def attributes(cls):
        return [getattr(value.fset, "_spec") for value in cls.__dict__.values() if isinstance(value, property)]

    @classmethod
    def from_data(cls, data, strict=False):
        obj = cls()

        if strict:
            for attribute, attribute_type, kwargs in cls.attributes():
                # We can use obj as sentinel as well
                value = data.get(attribute, obj)
                if value is not obj:
                    if attribute_type is not None and not (kwargs.get("nullable") and value is None):
                        value = cls._convert(attribute, attribute_type, value, strict)
                    obj.__setattr__(attribute, value)
                else:
                    default = kwargs.get("default", obj)
                    if default is not obj:
                        obj.__setattr__(attribute, default)
        else:
            obj.__dict__.update(data)

        return obj

    @classmethod
    def _convert(cls, attribute, attribute_type, value, strict=False):
        if isinstance(attribute_type, cls.ARRAY_TYPES):
            if not isinstance(value, cls.ARRAY_TYPES):
                raise ValueError(
                    "Unexpected value type for attribute '{}'. Received {} but expecting [{}]".format(
                        attribute, value.__class__, attribute_type[0]))
            value = [cls._convert("{}[...]".format(attribute), attribute_type[0], v, strict) for v in value]
        elif issubclass(attribute_type, DataStruct) and isinstance(value, dict):
            value = attribute_type.from_data(value, strict=strict)
        elif not isinstance(value, attribute_type):
            raise ValueError(
                "Unexpected value type for attribute '{}'. Received {} but expecting {}".format(
                    attribute, value.__class__, attribute_type))
        return value

    @classmethod
    def attr(cls, attribute, clazz=None, **kwargs):
        def setter(self, value):
            if clazz and not (kwargs.get("nullable") and value is None):
                if isinstance(clazz, cls.ARRAY_TYPES):
                    if len(clazz) != 1 or type(clazz[0]) is not type:
                        raise TypeError("Type definition for arrays must be a list/tuple of size 1")
                    if not (isinstance(value, cls.ARRAY_TYPES) and all([isinstance(v, clazz[0]) for v in value])):
                        raise TypeError("Expecting a [{}] type for '{}' attribute".format(clazz[0], attribute))
                elif not isinstance(value, clazz):
                    raise TypeError("Expecting a {} type for '{}' attribute".format(clazz, attribute))
            self.__dict__[attribute] = value

        def getter(self):
            return self.__dict__.get(attribute)

        setter._spec = (attribute, clazz, kwargs)
        return property(getter, setter)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise AttributeError("No such attribute '{}'".format(k))
            self.__setattr__(k, v)

    def __repr__(self):
        return str(self.__dict__)


def calculate_hash(path, chunk_size=65536):
    if re.match("https?://", path):
        # r = requests.head(path)
        r = requests.get(path, stream=True)
        r.close()
        length = int(r.headers.get("Content-Length", 0))
        if not (r.headers.get("Accept-Ranges") == "bytes" and length >= chunk_size):
            logging.debug("%s can't be hashed: %s", path, r.headers)
            return None

        range_fmt = "bytes={:d}-{:d}"
        data = requests.get(path, headers={"Range": range_fmt.format(0, chunk_size - 1)}).content
        data += requests.get(path, headers={"Range": range_fmt.format(length - chunk_size, length - 1)}).content
    elif os.path.isfile(path):
        length = os.path.getsize(path)
        if length < chunk_size:
            logging.debug("File '%s' size (%s) is too small", path, length)
            return None
        with FileIO(path, "rb") as f:
            data = f.read(chunk_size)
            f.seek(length - chunk_size)
            data += f.read(chunk_size)
    else:
        logging.warning("Unknown path type: %s", path)
        return None

    long_long_fmt = "<q"
    long_long_size = struct.calcsize(long_long_fmt)
    file_hash = length
    for i in range(0, chunk_size * 2, long_long_size):
        (value,) = struct.unpack(long_long_fmt, data[i:i + long_long_size])
        file_hash = (file_hash + value) & 0xFFFFFFFFFFFFFFFF

    return "{:016x}".format(file_hash)
