import logging
import os
import re
import struct
from io import FileIO

import requests


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
