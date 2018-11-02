import unittest
import time

import udon.cache


class TestCache(unittest.TestCase):

    
    calls = 0
    def cached_function(self, *keys):
        self.calls += 1
        return self.calls

    def test_lru_cache(self):
        size = 20
        calls = 100

        self.calls = 0
        cache = udon.cache.LRUCache(self.cached_function, size = size)
        for i in range(calls):
            cache(i)
        self.assertEqual(len(cache), size)
        self.assertEqual(cache.hit, 0)
        self.assertEqual(cache.miss, calls)
        self.assertEqual(self.calls, calls)

        for i in range(calls - size, calls):
            cache(i)
        self.assertEqual(len(cache), size)
        self.assertEqual(cache.hit, size)
        self.assertEqual(cache.miss, calls)
        self.assertEqual(self.calls, calls)


    def test_delay_cache(self):
        calls = 100
        delay = .1
        self.calls = 0
        
        cache = udon.cache.DelayCache(self.cached_function, delay = delay)

        for i in range(calls):
            cache(i)
        self.assertEqual(len(cache), calls)
        self.assertEqual(cache.hit, 0)
        self.assertEqual(cache.miss, calls)
        self.assertEqual(self.calls, calls)

        for i in range(calls):
            cache(i)
        self.assertEqual(len(cache), calls)
        self.assertEqual(cache.hit, calls)
        self.assertEqual(cache.miss, calls)
        self.assertEqual(self.calls, calls)

        time.sleep(delay)
        self.assertEqual(len(cache), 0)
        
        cache("foo")
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.hit, calls)
        self.assertEqual(cache.miss, calls + 1)
        self.assertEqual(self.calls, calls + 1)
