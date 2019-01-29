import os
import tempfile
import unittest
import hashlib

import udon.content


class TestContent(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.count = 0

    def tearDown(self):
        self.tmpdir.cleanup()

    def content_path(self):
        path = os.path.join(self.tmpdir.name, "content-%d" % self.count)
        self.count += 1
        return path

    def test_empty(self):
        path = self.content_path()
        with udon.content.writer(path) as fp:
            fp.write(b'')
        with udon.content.reader(path) as fp:
            data = fp.read()
        self.assertIsInstance(data, bytes)
        self.assertEqual(data, b'')

    def test_file(self):
        path = self.content_path()
        with open("/etc/passwd", "rb") as fp:
            with udon.content.writer(path) as cfp:
                cfp.write(fp.read())

        with udon.content.reader(path) as fp:
            with open("/etc/passwd", "rb") as cfp:
                self.assertEqual(fp.read(), cfp.read())

    def test_cksum(self):
        with open("/etc/passwd", "rb") as fp:
            datain = fp.read()

        path = self.content_path()
        with udon.content.writer(path) as fp:
            fp.write(datain)
        with udon.content.reader(path) as fp:
            dataout = fp.read()
            info = fp.info

        sumin = hashlib.sha256(datain).hexdigest()
        sumout = hashlib.sha256(dataout).hexdigest()

        self.assertEqual(len(datain), len(dataout))
        self.assertEqual(datain, dataout)
        self.assertEqual(sumin, sumout)
        self.assertEqual(len(datain), info.size)
        self.assertEqual(sumin, info.sha256)

    def test_headers(self):
        path = self.content_path()

        with udon.content.writer(path) as fp:
            fp.write(b'')

        with udon.content.reader(path) as fp:
            for key, val in fp.info.headers:
                self.assertIsInstance(key, str)
                self.assertIsInstance(val, str)

    def test_headers2(self):
        path = self.content_path()

        with udon.content.writer(path) as fp:
            fp.write_header("Foo", "Bar")
            fp.write_header("Baz", 4)
            fp.write_header("Foo2", b"Bar")

        with udon.content.reader(path) as fp:
            for key, val in fp.info.headers:
                self.assertIsInstance(key, str)
                self.assertIsInstance(val, str)

    def test_bad_headers(self):
        def _content_write_headers(headers):
            with udon.content.writer(self.content_path()) as fp:
                for key, val in headers:
                    fp.write_header(key, val)

        with self.assertRaises(ValueError):
            _content_write_headers([ ("Foo:", "Bar") ])
        with self.assertRaises(ValueError):
            _content_write_headers([ ("Foo\n", "") ])
        with self.assertRaises(ValueError):
            _content_write_headers([ ("Foo", "Bax\n") ])
        with self.assertRaises(ValueError):
            _content_write_headers([ ("Foo", "Bar" * 999999) ])
        with self.assertRaises(TypeError):
            _content_write_headers([ (1, "Bar") ])
        with self.assertRaises(ValueError):
            _content_write_headers([ ("foo" * 120, "Bar") ])

    def test_expect_size(self):
        with self.assertRaises(ValueError):
            with udon.content.writer(self.content_path(), expect_size = 2) as fp:
                fp.write(b'foo')
        with self.assertRaises(ValueError):
            with udon.content.writer(self.content_path(), expect_size = 4) as fp:
                fp.write(b'foo')
        with udon.content.writer(self.content_path(), expect_size = 3) as fp:
            fp.write(b'foo')

    def test_invalid_open(self):
        with self.assertRaises(ValueError):
            with udon.content.reader("/etc/passwd"):
                pass

    def test_broken_file(self):
        path = self.content_path()

        with open(path, "w") as fp:
            fp.write("Checksum-SHA256: 20000\n")
            fp.write("Size: 20\n")
            fp.write("Offset: 20000\n")
            fp.write("Timestamp: 20000\n")
            fp.write("\n")

        with self.assertRaises(AssertionError):
            with udon.content.reader(path):
                pass
