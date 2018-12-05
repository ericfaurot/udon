import os
import tempfile
import unittest
import hashlib

import udon.store


class TestContent(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.count = 0

    def tearDown(self):
        self.tmpdir.cleanup()

    def store(self):
        return udon.store.KeyStore(self.tmpdir.name)

    def test_has(self):
        store = self.store()
        key = "test_has"
        self.assertFalse(store.has(key))
        store.put(key, b"bar")
        self.assertTrue(store.has(key))

    def test_delete(self):
        store = self.store()
        key = "test_delete"
        self.assertFalse(store.has(key))
        store.put(key, b"nothing")
        self.assertTrue(store.has(key))
        store.delete(key)
        self.assertFalse(store.has(key))

    def test_delete_missing(self):
        store = self.store()
        key = "test_delete_missing"
        with self.assertRaises(KeyError):
            store.delete(key)

    def test_open(self):
        store = self.store()
        key = "test_open"
        value = b'some content'
        store.put(key, value)
        with store.open(key) as stream:
            self.assertEqual(stream.read(), value)

    def test_open_missing(self):
        store = self.store()
        key = "test_open_missing"
        with self.assertRaises(KeyError):
            store.open(key)

    def test_replace(self):
        store = self.store()
        key = "test_open"
        value = b'some content'
        value2 = b'some content2'

        store.put(key, value)
        with store.open(key) as stream:
            self.assertEqual(stream.read(), value)
        store.put(key, value2)
        with store.open(key) as stream:
            self.assertEqual(stream.read(), value2)
