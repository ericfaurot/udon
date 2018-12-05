#
# Copyright (c) 2018 Eric Faurot <eric@faurot.net>
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

class AtomicFile(object):
    """
    Open a temporary file in the destination directory that gets
    rename to the final location on close.
    """
    def __init__(self, target, mode = "wb"):
        self.target = target
        fd, path = tempfile.mkstemp(dir = os.path.dirname(target))
        try:
            self._file = os.fdopen(fd, mode)
        except:
            os.close(fd)
            os.unlink(path)
            raise

        self._path = path
        self.write = self._file.write
        self.seek = self._file.seek

    def _close(self):
        self._file.close()
        del self._file
        del self.write
        del self.seek
        
    def close(self, overwrite = True):
        self._close()
        try:
            os.rename(self._path, self.target)
        except:
            os.unlink(self._path)
            raise
        finally:
            del self._path

    def unlink(self):
        self._close()
        os.unlink(self._path)
        del self._path


class HeaderTooLarge(Exception):
    pass

class InvalidFileFormat(Exception):
    pass


class ContentFile(object):

    RESERVED_HDRS = set(("Checksum-SHA256",
                         "Size",
                         "Offset",
                         "Timestamp"))

    def __init__(self, path):
        self.path = path

    def _iter_headers(self, fp):
        while True:
            line = fp.readline()
            if not line or line == b"\n":
                return
            try:
                key, value = line.decode().split(":", 1)
            except:
                raise InvalidFileFormat("Invalid header line")
            yield key, value.strip()

    def headers(self):
        with self.open() as fp:
            return fp.headers

    def open(self):
        fp = open(self.path, "rb")
        try:
            offset = None
            fp.headers = []
            for key, value in self._iter_headers(fp):
                fp.headers.append((key, value))
                if key == 'Offset':
                    offset = int(value)
            if offset is None:
                raise InvalidFileFormat("No offset found")
            fp.seek(offset)
            return fp
        except:
            fp.close()
            raise

    def write(self, body, meta = (), chunk_size=2**16, expect_size = None):

        if isinstance(body, bytes):
            size = len(body)
            cksum = hashlib.sha256(body)
        else:
            offset = body.tell()
            body.seek(0, 2)
            size = body.tell() - offset
            body.seek(offset)
            cksum = hashlib.sha256()

        if expect_size not in (None, size):
            raise ValueError("Content has incorrect size")

        hdrs = []
        hdrs.append("Checksum-SHA256: %s" % cksum.hexdigest())
        hdrs.append("Timestamp: %d" % int(time.time()))
        hdrs.append("Size: %d" % size)
        # Format headers
        def _fix_key(key):
            if not isinstance(key, str):
                raise TypeError("Key must be a string")
            if ":" in key:
                raise ValueError("Key must not contain ':'")
            if key in self.RESERVED_HDRS:
                raise ValueError("Reserved header")
            return key
        def _fix_val(val):
            return val.decode() if isinstance(val, bytes) else str(val)
        for key, val in meta:
            line = "%s: %s" % (_fix_key(key), _fix_val(val))
            if "\n" in line:
                raise ValueError("Newline not allowed in headers")
            hdrs.append(line)
        hdrs.append("\n")
        head = "\n".join(hdrs).encode("utf-8")

        out = AtomicFile(self.path)
        try:
            # Write headers
            OFFSET_MAX = 999999
            OFFSET_FMT = b"Offset: %-6d\n"
            OFFSET_MIN = len(OFFSET_FMT % OFFSET_MAX)
            start = len(head) + OFFSET_MIN
            if start > OFFSET_MAX:
                raise HeaderTooLarge(start)
            out.write(OFFSET_FMT % start)
            out.write(head)

            if isinstance(body, bytes):
                out.write(body)
            else:
                # Write content
                while 1:
                    buf = body.read(chunk_size)
                    if not buf:
                        break
                    cksum.update(buf)
                    out.write(buf)
                body.seek(offset)
                # Alter headers
                out.seek(OFFSET_MIN + len(b"Checksum-SHA256: "))
                out.write(cksum.hexdigest().encode())

        except:
            out.unlink()
            raise
        else:
            out.close()
