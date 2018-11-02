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
import time


class NoCache(Exception):
    def __init__(self, value):
        self.value = value


class _NoLock:
    def __enter__(self):
        pass
    def __exit__(self, _type, _value, _traceback):
        pass


class AbstractCache:

    hit = 0
    miss = 0
    skip = 0
    lock = _NoLock()

    def __init__(self, func, lock = None):
        self.func = func
        if lock is not None:
            self.lock = lock

    def __call__(self, *key):
        with self.lock:
            try:
                return self.do_get(*key)
            except NoCache as res:
                self.skip += 1
                return res.value

    def __len__(self):
        with self.lock:
            return self.do_size()

    def clear(self):
        with self.lock:
            return self.do_clear()

    def do_compute(self, *key):
        return self.func(*key)

    def do_get(self, *key):
        raise NotImplementedError

    def do_size(self):
        raise NotImplementedError

    def do_clear(self):
        raise NotImplementedError



_UNDEFINED = object()
class LRUNode:

    __slots__ = "prev", "next", "key", "value"

    def __init__(self, key = _UNDEFINED, value = _UNDEFINED):
        if key is not _UNDEFINED:
            self.key = key
        if value is not _UNDEFINED:
            self.value = value

    def remove(self):
        self.prev.next = self.next
        self.next.prev = self.prev

    def insert_before(self, node):
        self.next = node
        self.prev = prev = node.prev
        prev.next = node.prev = self


class LRUCache(AbstractCache):

    def __init__(self, func, size, lock = None):
        super().__init__(func, lock = lock)
        self.size = size
        self.mapping = {}
        self.head = LRUNode()
        self.tail = LRUNode()
        self.head.next = self.tail
        self.tail.prev = self.head

    def do_size(self):
        return len(self.mapping)

    def do_get(self, *key):
        node = self.mapping.get(key)
        if node is None:
            self.miss += 1
            value = self.do_compute(*key)
            if len(self.mapping) >= self.size:
                old = self.head.next
                old.remove()
                del self.mapping[old.key]
            self.mapping[key] = node = LRUNode(key, value)
            node.insert_before(self.tail)
        else:
            self.hit += 1
            node.remove()
            node.insert_before(self.tail)
        return node.value

    def do_clear(self):
        self.mapping.clear()
        self.head.next = self.tail
        self.tail.prev = self.head


def lru_cache(size, lock = None):
    def _(func):
        return LRUCache(func, size, lock = lock)
    return _


class DelayCache(AbstractCache):

    def __init__(self, func, delay, lock = None):
        super().__init__(func, lock = lock)
        self.delay = delay
        self.mapping = {}
        self.next_purge = time.time() + delay

    def do_purge(self):
        now = time.time()
        self.mapping = { key: (timeout, data)
                         for key, (timeout, data) in self.mapping.items()
                         if timeout > now }
        self.next_purge = now + self.delay

    def do_size(self):
        if time.time() > self.next_purge:
            self.do_purge()
        return len(self.mapping)

    def do_get(self, *key):
        if time.time() > self.next_purge:
            self.do_purge()
        timeout, data = self.mapping.get(key, (0, None))
        if timeout < time.time():
            self.miss += 1
            data = self.do_compute(*key)
            self.mapping[key] = time.time() + self.delay, data
        else:
            self.hit += 1
        return data

    def do_clear(self):
        self.mapping.clear()


def delay_cache(delay, lock = None):
    def _(func):
        return DelayCache(func, delay, lock = lock)
    return _
