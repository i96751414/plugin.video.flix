import logging
import os
import re
import struct
from io import FileIO

import requests


class DataStruct(object):
    _ARRAY_TYPES = (list, tuple)
    _SPEC_FIELD = "_spec"

    @classmethod
    def attributes(cls):
        return [attr for attr in (
            getattr(value.fset, cls._SPEC_FIELD)
            for clazz in cls.__mro__
            for value in clazz.__dict__.values()
            if isinstance(value, property) and value.fset is not None
        ) if attr is not None]

    @classmethod
    def from_data(cls, data, strict=False):
        obj = cls()

        if strict:
            for attribute, attribute_type, params in cls.attributes():
                # We can use obj as sentinel as well
                value = data.get(attribute, obj)
                if value is not obj:
                    obj.__setattr__(attribute, cls._convert_from_data(attribute, attribute_type, value, params, strict))
                else:
                    default = params.get("default", obj)
                    if default is not obj:
                        obj.__setattr__(attribute, default)
                    else:
                        raise ValueError("No value for attribute {}".format(attribute))
        else:
            obj.__dict__.update(data)

        return obj

    @classmethod
    def _convert_from_data(cls, attribute, attribute_type, value, params, strict=False):
        nullable = params.get("nullable")
        converter = params.get("from_converter")

        if converter and not (nullable and value is None):
            value = converter(value)

        if attribute_type is not None:
            if isinstance(attribute_type, cls._ARRAY_TYPES):
                if not isinstance(value, cls._ARRAY_TYPES):
                    raise ValueError(
                        "Unexpected value type for attribute '{}'. Received {} but expecting [{}]".format(
                            attribute, value.__class__, attribute_type[0]))
                value = [cls._convert_from_data(attribute + "[...]", attribute_type[0], v, {}, strict) for v in value]
            elif issubclass(attribute_type, DataStruct) and isinstance(value, dict):
                value = attribute_type.from_data(value, strict=strict)

        return value

    @classmethod
    def attr(cls, attribute, clazz=None, **params):
        if clazz:
            cls._validate_class_type(attribute, clazz)

        def setter(self, value):
            if clazz and not (params.get("nullable") and value is None):
                cls._validate_attribute_value(attribute, clazz, value)
            self.__dict__[attribute] = value

        def getter(self):
            return self.__dict__.get(attribute)

        setattr(setter, cls._SPEC_FIELD, (attribute, clazz, params))
        return property(getter, setter)

    @classmethod
    def _validate_class_type(cls, attribute, clazz):
        while isinstance(clazz, cls._ARRAY_TYPES):
            if len(clazz) != 1:
                raise TypeError("Type definition for arrays must be a list/tuple of size 1")
            clazz = clazz[0]

        if type(clazz) is not type:
            raise TypeError("Invalid type provided {} for attribute {}".format(clazz, attribute))

    @classmethod
    def _validate_attribute_value(cls, attribute, clazz, value):
        if isinstance(clazz, cls._ARRAY_TYPES):
            if not isinstance(value, cls._ARRAY_TYPES):
                raise TypeError("Expecting a {} type for '{}' attribute".format(clazz, attribute))
            for v in value:
                cls._validate_attribute_value(attribute + "[...]", clazz[0], v)
        elif not isinstance(value, clazz):
            raise TypeError("Expecting a {} type for '{}' attribute, but received {}".format(
                clazz, attribute, value.__class__))

    @classmethod
    def _convert_to_data(cls, value):
        if isinstance(value, DataStruct):
            value = {attribute: cls._convert_to_data(value.__dict__.get(attribute))
                     for attribute, _, _ in value.attributes()}
        elif isinstance(value, cls._ARRAY_TYPES):
            value = [cls._convert_to_data(v) for v in value]
        return value

    def to_dict(self):
        return self._convert_to_data(self)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise AttributeError("No such attribute '{}'".format(k))
            self.__setattr__(k, v)

    def __repr__(self):
        return str(self.to_dict())


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
