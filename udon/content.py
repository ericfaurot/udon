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
import hashlib
import os
import tempfile
import time


class HeaderTooLarge(Exception):
    pass

class InvalidFileFormat(Exception):
    pass


def open_content(path):
    fp = open(path, "rb")
    try:
        fp.headers = []
        offset = None
        while True:
            line = fp.readline()
            if not line or line == b"\n":
                break
            try:
                key, value = line.decode().split(":", 1)
                if key == 'Offset':
                    offset = int(value)
                fp.headers.append((key, value.strip()))
            except:
                raise InvalidFileFormat("Invalid header line")
        if offset is None:
            raise InvalidFileFormat("No offset found")
        fp.seek(offset)
    except:
        fp.close()
        raise
    return fp


def write_content(path, body, headers = None, chunk_size = 2**16, expect_size = None):

    with tempfile.NamedTemporaryFile(dir = os.path.dirname(path), delete = False) as fp:
        try:
            content = ContentWriter(fp, expect_size = expect_size)
            if headers:
                content.write_headers(headers)
            if isinstance(body, bytes):
                content.write(body)
            else:
                while 1:
                    buf = body.read(chunk_size)
                    if not buf:
                        break
                    content.write(buf)
            content.close()
            os.rename(fp.name, path)
        except:
            try:
                os.unlink(fp.name)
            except:
                pass
            raise


class ContentWriter:

    RESERVED_HDRS = set(("Checksum-SHA256",
                         "Offset",
                         "Size",
                         "Timestamp"))
    MAX_OFFSET = 2 ** 20
    MAX_SIZE = 2 ** 48

    headers_written = False

    def __init__(self, fp, expect_size = None):
        self.expect_size = expect_size
        self.cksum = hashlib.sha256()
        self.fp = fp
        self.size = 0
        self.pos = 0
        self.header_pos = {}

    def write(self, data):
        if not self.headers_written:
            self.write_headers()
        self.cksum.update(data)
        self.fp.write(data)
        self.size += len(data)

    def write_headers(self, headers = None):
        assert not self.headers_written

        self._write_header("Checksum-SHA256", self.cksum.hexdigest())
        self._write_header("Size", self.MAX_SIZE)
        self._write_header("Offset", self.MAX_OFFSET)
        self._write_header("Timestamp", int(time.time()))
        for key, value in headers or ():
            if not isinstance(key, str):
                raise TypeError("Key must be a string")
            if ":" in key:
                raise ValueError("Key must not contain ':'")
            if "\n" in key:
                raise ValueError("Key must not contain '\n'")
            if key in self.RESERVED_HDRS:
                raise ValueError("Reserved header")
            self._write_header(key, self._coerce_value(value))
        self.fp.write(b"\n")
        self.offset = self.pos + 1
        if self.offset >= self.MAX_OFFSET:
            raise HeaderTooLarge(self.offset)
        self.headers_written = True

    def _coerce_value(self, value):
        value = value.decode() if isinstance(value, bytes) else str(value)
        if "\n" in value:
            raise ValueError("Value must not contain '\n'")
        return value

    def _write_header(self, header, value):
        hdr = b"%s: " % header.encode('utf-8')
        val = self._coerce_value(value).encode('utf-8')
        self.header_pos[header] = self.pos + len(hdr), len(val)
        self.fp.write(hdr)
        self.fp.write(val)
        self.fp.write(b'\n')
        self.pos += len(hdr) + len(val) + 1

    def _update_header(self, header, value):
        value = self._coerce_value(value).encode('utf-8')
        offset, size = self.header_pos[header]
        missing = size - len(value)
        if missing < 0:
            raise ValueError("Updated value too large for key \"%s\" (%d/%d)" % (header, len(value), size))
        self.fp.seek(offset)
        if missing:
            self.fp.write(b' ' * missing)
        self.fp.write(value)

    def _finalize_headers(self):
        self._update_header("Checksum-SHA256", self.cksum.hexdigest())
        self._update_header("Offset", self.offset)
        self._update_header("Size", self.size)

    def close(self):
        if not self.headers_written:
            self.write_headers()
        self._finalize_headers()
        self.fp.close()
        if self.expect_size not in (None, self.size):
            raise ValueError("Content has incorrect size")



class ContentFile:

    def __init__(self, path):
        self.path = path

    def headers(self):
        with open_content(self.path) as fp:
            return fp.headers

    def open(self):
        return open_content(self.path)

    def write(self, body, meta = (), chunk_size = 2**16, expect_size = None):
        return write_content(self.path, body, meta, chunk_size = chunk_size, expect_size = expect_size)
