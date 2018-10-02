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

class AbstractCache(object):

    hit = 0
    miss = 0
    skip = 0
    lock = None
    bypass = False

    def setup(self, lock):
        if lock is not None:
            self.lock = lock
        self._clear()

    def enable(self):
        self.bypass = False

    def disable(self):
        self.bypass = True

    def __len__(self):
        return len(self.mapping)

    def __call__(self, *key):
        return self.get(*key)

    def get(self, *key):
        if self.bypass:
            try:
                return self.func(*key)
            except NoCache as res:
                self.skip += 1
                return res.value
        if self.lock:
            with self.lock:
                try:
                    return self._get(*key)
                except NoCache as res:
                    self.skip += 1
                    return res.value
        try:
            return self._get(*key)
        except NoCache as res:
            self.skip += 1
            return res.value

    def clear(self):
        if self.lock:
            with self.lock:
                return self._clear()
        return self._clear()


class LRUCache(AbstractCache):

    def __init__(self, func, size):
        self.func = func
        self.size = size

    def _get(self, *key):
        PREV, NEXT = 0, 1
        mapping, head, tail = self.mapping, self.head, self.tail

        link = mapping.get(key, head)
        if link is head:
            value = self.func(*key)
            self.miss += 1
            if len(mapping) >= self.size:
                old_prev, old_next, old_key, old_value = head[NEXT]
                head[NEXT] = old_next
                old_next[PREV] = head
                del mapping[old_key]
            last = tail[PREV]
            link = [last, tail, key, value]
            mapping[key] = last[NEXT] = tail[PREV] = link
        else:
            self.hit += 1
            link_prev, link_next, key, value = link
            link_prev[NEXT] = link_next
            link_next[PREV] = link_prev
            last = tail[PREV]
            last[NEXT] = tail[PREV] = link
            link[PREV] = last
            link[NEXT] = tail
        return value

    def _clear(self):
        self.mapping = {}
        PREV, NEXT, KEY, VALUE = 0, 1, 2, 3         # link fields
        self.head = [None, None, None, None]        # oldest
        self.tail = [self.head, None, None, None]   # newest
        self.head[NEXT] = self.tail

def lru_cache(size, lock = None):
    def _(func):
        cache = LRUCache(func, size)
        cache.setup(lock)
        return cache
    return _


class DelayCache(AbstractCache):

    def __init__(self, func, delay):
        self.func = func
        self.delay = delay

    def _get(self, *key):
        timeout, data = self.mapping.get(key, (0, None))
        if timeout < time.time():
            data = self.func(*key)
            self.mapping[key] = time.time() + self.delay, data
            self.miss += 1
        else:
            self.hit += 1
        return data

    def _clear(self):
        self.mapping = {}


def delay_cache(delay, lock = None):
    def _(func):
        cache = DelayCache(func, delay)
        cache.setup(lock)
        return cache
    return _
