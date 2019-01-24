#
# Copyright (c) 2019 Eric Faurot <eric@faurot.net>
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
import os
import stat
import zipfile


EntryInfo = collections.namedtuple('EntryInfo', ['filename', 'size', 'is_dir'])


class BaseTree:

    def walk(self):
        raise NotImplementedError

    def info(self, filename):
        raise NotImplementedError

    def open(self, filename):
        raise NotImplementedError


class ZipTree(BaseTree):

    def __init__(self, path):
        self.path = path

    def walk(self):
        with zipfile.ZipFile(self.path) as zfp:
            for info in zfp.infolist():
                yield EntryInfo(info.filename, info.file_size, info.is_dir())

    def info(self, filename):
        with zipfile.ZipFile(self.path) as zfp:
            info = zfp.getinfo(filename)
            return EntryInfo(info.filename, info.file_size, info.is_dir())

    def open(self, filename):
        with zipfile.ZipFile(self.path) as zfp:
            return zfp.open(filename)


class DirTree(BaseTree):

    def __init__(self, root):
        # make sure it ends with "/"
        self.root = os.path.join(root, "")

    def walk(self):
        for root, _, files in os.walk(self.root):
            for name in files:
                path = os.path.join(root, name)
                st = os.stat(path)
                filename = path[len(self.root):]
                yield EntryInfo(filename, st.st_size, stat.S_ISDIR(st))

    def info(self, filename):
        st = os.stat(os.path.join(self.root, filename))
        EntryInfo(filename, st.st_size, stat.S_ISDIR(st))

    def open(self, filename):
        return open(os.path.join(self.root, filename), "rb")
