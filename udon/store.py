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
import errno
import hashlib
import os
import tempfile


def _mkdirs(*path):
    result = os.path.join(*path)
    try:
        os.makedirs(result)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
    return result


class AbstractStore(object):
    """
    """

    def __init__(self, root):
        self.root = root
        _mkdirs(self.root, "temporary")

    def _filename(self, key):
        """
        Construct the full-path for the key.
        """
        return os.path.join(self.root, key[:2], key)

    def _dirname(self, key):
        """
        Construct the directory name for the key.
        """
        return os.path.join(self.root, key[:2])

    def _tempfile(self):
        """
        Create a temporay file.
        """
        fd, path = tempfile.mkstemp(dir = os.path.join(self.root, "temporary"))
        try:
            return os.fdopen(fd, "wb"), path
        except:
            os.unlink(path)
            os.close(fd)
            raise

    def _commit(self, key, tmppath, overwrite = True):
        """
        Move the temporary file to it's permanent location.
        Return True if the key didn't exists before.
        """
        exists = self.has(key)
        if exists:
            if not overwrite:
                os.unlink(tmppath)
                return False
        else:
            _mkdirs(self._dirname(key))
        os.rename(tmppath, self._filename(key))
        return not exists

    def delete(self, key):
        """
        Remove the key
        """
        try:
            os.unlink(self._filename(key))
        except FileNotFoundError:
            raise KeyError(key)

    def has(self, key):
        """
        Check if the store contains a key.
        """
        return os.path.isfile(self._filename(key))

    def open(self, key):
        """
        Open the file given by it's key for reading.
        """
        try:
            return open(self._filename(key), "rb")
        except FileNotFoundError:
            raise KeyError(key)

    def stat(self, key):
        """
        Return the result of os.stat() in the file.
        """
        try:
            return os.stat(self._filename(key))
        except FileNotFoundError:
            raise KeyError(key)

    def walk(self):
        """
        Iterate over all existing keys.
        """
        for root, dirs, files in os.walk(self.root):
            for filename in files:
                if self.is_key(filename):
                    yield filename

    def is_key(self, val):
        """
        Check if the given value is a valid key for this store.
        """
        raise NotImplementedError


class KeyStore(AbstractStore):

    def is_key(self, key):
        return True

    def put(self, key, content):
        temp = KeyStoreTemporaryFile(self)
        temp.write(content)
        return temp.close(key)


class KeyStoreTemporaryFile(object):

    def __init__(self, store):
        self.store = store
        self.tempfile, self.path = store._tempfile()

    def write(self, data):
        self.tempfile.write(data)

    def close(self, key):
        self.tempfile.close()
        self.store._commit(key, self.path)
        return key


class SHA256Store(AbstractStore):

    def is_key(self, key):
        return len(key) == 64

    def put(self, content):
        temp = HashStoreTemporaryFile(self, hashlib.sha256())
        temp.write(content)
        return temp.close()


class HashStoreTemporaryFile(object):
    def __init__(self, store, hash):
        self.store = store
        self.tempfile, self.path = store._tempfile()
        self.hash = hash

    def write(self, data):
        self.tempfile.write(data)
        self.hash.update(data)

    def close(self):
        self.tempfile.close()
        key = self.hash.hexdigest()
        self.store._commit(key, self.path)
        return key


def backend(uri):
    backend, root = uri.split("://", 1)
    if backend == "sha256":
        return SHA256Store(root)
    if backend == "store":
        return KeyStore(root)
    else:
        raise KeyError(backend)
