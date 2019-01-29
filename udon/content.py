#
# Copyright (c) 2018,2019 Eric Faurot <eric@faurot.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import collections
import contextlib
import hashlib
import os
import tempfile
import time


import udon.path


ContentInfo = collections.namedtuple('ContentInfo', ['size', 'timestamp', 'offset', 'sha256', 'headers' ])


def reader(path):
    fp = open(path, "rb")
    try:
        info = {}
        headers = []
        while True:
            line = fp.readline()
            if line == b'\n':
                break
            key, value = line.split(b':', 1)
            value = value.strip()
            if key == b'Timestamp':
                info['timestamp'] = int(value)
            elif key == b'Size':
                info['size'] = int(value)
            elif key == b'Checksum-SHA256':
                info['sha256'] = value.decode()
            headers.append((key.decode(), value.decode('utf-8')))
        fp.info = ContentInfo(headers = headers, offset = fp.tell(), **info)
        assert os.fstat(fp.fileno()).st_size == fp.info.size + fp.info.offset
    except:
        fp.close()
        raise
    return fp


@contextlib.contextmanager
def writer(path, expect_size = None, tmpdir = None):
    with udon.path.overwriting(path, tmpdir = tmpdir) as fp:
        wrt = ContentWriter(fp, expect_size = expect_size)
        yield wrt
        wrt.close()


def _chunks(source, chunk_size = 2 ** 16):
    if isinstance(source, bytes):
        yield source
    else:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                return
            yield chunk


class ContentWriter:

    RESERVED_HDRS = set(("Checksum-SHA256",
                         "Size",
                         "Timestamp"))
    MAX_KEY_LEN = 128
    MAX_VALUE_LEN = 2 ** 14
    MAX_SIZE = 2 ** 48

    _headers_done = False
    size = 0
    wpos = 0

    def __init__(self, fp, expect_size = None):
        self.expect_size = expect_size
        self.cksum = hashlib.sha256()
        self.timestamp = int(time.time())
        self.fp = fp
        self._headers = {}

    def write(self, data):
        if not self._headers_done:
            self._end_headers()
        self.cksum.update(data)
        self.fp.write(data)
        self.size += len(data)

    def write_header(self, hdr, value):
        assert not self._headers_done
        if not self._headers:
            self._write_internal_headers()

        if not isinstance(hdr, str):
            raise TypeError("Key must be a string")
        if len(hdr) >= self.MAX_KEY_LEN:
            raise ValueError("Key too large")
        if ":" in hdr:
            raise ValueError("Key must not contain ':'")
        if "\n" in hdr:
            raise ValueError("Key must not contain '\n'")
        if hdr in self.RESERVED_HDRS:
            raise ValueError("Reserved header")
        self._write_header(hdr, value)

    def update_header(self, hdr, value):
        offset, size = self._headers[hdr]
        value = self._coerce_value(value)
        missing = size - len(value)
        if missing < 0:
            raise ValueError("Updated value too large for key \"%s\" (%d/%d)" % (hdr, len(value), size))
        self.fp.seek(offset)
        if missing:
            self.fp.write(b' ' * missing)
        self.fp.write(value)

    def close(self):
        if not self._headers_done:
            self._end_headers()
        self.update_header("Checksum-SHA256", self.cksum.hexdigest())
        self.update_header("Size", self.size)
        self.fp.close()
        if self.expect_size not in (None, self.size):
            raise ValueError("Content has incorrect size")

    def _coerce_value(self, value):
        if not isinstance(value, bytes):
            value = str(value).encode('utf-8')
        if b'\n' in value:
            raise ValueError("Value must not contain '\n'")
        if len(value) >= self.MAX_VALUE_LEN:
            raise ValueError("Value too large")
        return value

    def _write_internal_headers(self):
        self._write_header("Checksum-SHA256", self.cksum.hexdigest())
        self._write_header("Size", self.MAX_SIZE)
        self._write_header("Timestamp", self.timestamp)

    def _write_header(self, header, value):
        hdr = b"%s: " % header.encode('utf-8')
        val = self._coerce_value(value)
        self._headers[header] = self.wpos + len(hdr), len(val)
        self.fp.write(hdr)
        self.fp.write(val)
        self.fp.write(b'\n')
        self.wpos += len(hdr) + len(val) + 1

    def _end_headers(self):
        if not self._headers:
            self._write_internal_headers()
        self.fp.write(b"\n")
        self.wpos += 1
        self._headers_done = True
