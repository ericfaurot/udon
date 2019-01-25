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
import datetime
import os
import stat
import zipfile


EntryInfo = collections.namedtuple('EntryInfo', ['path', 'size', 'mtime', 'is_dir'])


class BaseTree:

    def walk(self):
        raise NotImplementedError

    def info(self, filename):
        raise NotImplementedError

    def open(self, filename):
        raise NotImplementedError

    def checkfilename(self, filename):
        if not isinstance(filename, str):
            raise TypeError('must be a string')
        if len(filename) == 0:
            raise ValueError('invalid path')
        for component in filename.split('/'):
            if component in ('', '.', '..'):
                raise ValueError('invalid path')




def _zipinfo_to_info(info):
    timestamp = int(datetime.datetime(*info.date_time).timestamp())
    return EntryInfo(info.filename, info.file_size, timestamp, info.is_dir())


class ZipTree(BaseTree):

    def __init__(self, path):
        self.path = path

    def walk(self):
        with zipfile.ZipFile(self.path) as zfp:
            for info in zfp.infolist():
                yield _zipinfo_to_info(info)

    def info(self, filename):
        with zipfile.ZipFile(self.path) as zfp:
            return _zipinfo_to_info(zfp.getinfo(filename))

    def open(self, filename):
        with zipfile.ZipFile(self.path) as zfp:
            return zfp.open(filename)


def _stat_to_info(path, st):
    return EntryInfo(path, st.st_size, int(st.st_mtime), stat.S_ISDIR(st.st_mode))

class DirTree(BaseTree):

    def __init__(self, root):
        # make sure it ends with "/"
        self.root = os.path.join(root, "")

    def realpath(self, filename):
        self.checkfilename(filename)
        path = os.path.join(self.root, filename)
        assert path.startswith(self.root)
        return path

    def walk(self):
        for root, dirs, files in os.walk(self.root):
            for name in files + dirs:
                path = os.path.join(root, name)
                assert path.startswith(self.root)
                yield _stat_to_info(path[len(self.root):], os.stat(path))

    def info(self, filename):
        try:
            return _stat_to_info(filename, os.stat(self.realpath(filename)))
        except FileNotFoundError:
            raise KeyError(filename)

    def open(self, filename):
        try:
            return open(self.realpath(filename), "rb")
        except FileNotFoundError:
            raise KeyError(filename)

    def subtree(self, path):
        return DirTree(self.realpath(path))
