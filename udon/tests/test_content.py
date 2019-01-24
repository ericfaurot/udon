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

    def content(self, path = None):
        if path is None:
            path = os.path.join(self.tmpdir.name, "file-%d" % self.count)
            self.count += 1
        return udon.content.ContentFile(path)

    def test_empty(self):
        content = self.content()
        content.write(b'')
        with content.open() as fp:
            data = fp.read()
        self.assertIsInstance(data, bytes)
        self.assertEqual(data, b'')

    def test_file(self):
        content = self.content()
        with open("/etc/passwd", "rb") as fp:
            content.write(fp)
        with content.open() as fp:
            with open("/etc/passwd", "rb") as fp2:
                self.assertEqual(fp.read(),fp2.read())

    def test_cksum(self):
        with open("/etc/passwd", "rb") as fp:
            datain = fp.read()

        content = self.content()
        content.write(datain)
        with content.open() as fp:
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
        content = self.content()
        content.write(b'')
        for key, val in content.headers():
            self.assertIsInstance(key, str)
            self.assertIsInstance(val, str)

    def test_headers2(self):
        content = self.content()
        content.write(b'', headers = [ ("Foo", "Bar"),
                                       ("Baz", 4),
                                       ("Foo2", b"Bar"),
        ])
        for key, val in content.headers():
            self.assertIsInstance(key, str)
            self.assertIsInstance(val, str)

    def test_bad_headers(self):
        content = self.content()

        with self.assertRaises(ValueError):
            content.write(b'', headers = [ ("Foo:", "Bar") ])

        with self.assertRaises(ValueError):
            content.write(b'', headers = [ ("Foo\n", "") ])

        with self.assertRaises(ValueError):
            content.write(b'', headers = [ ("Foo", "Bax\n") ])

        with self.assertRaises(ValueError):
            content.write(b'', headers = [ ("Foo", "Bar" * 999999) ])

        with self.assertRaises(TypeError):
            content.write(b'', headers = [ (1, "Bar") ])

        with self.assertRaises(ValueError):
            content.write(b'', headers = [ ("foo" * 120, "Bar") ])

    def test_expect_size(self):
        content = self.content()
        with self.assertRaises(ValueError):
            content.write(b'foo', expect_size = 2)
        with self.assertRaises(ValueError):
            content.write(b'foo', expect_size = 4)
        content.write(b'foo', expect_size = 3)


    def test_invalid_open(self):
        content = self.content("/etc/passwd")
        with self.assertRaises(ValueError):
            with content.open():
                pass

    def test_broken_file(self):
        content = self.content()
        with open(content.path, "w") as fp:
            fp.write("Checksum-SHA256: 20000\n")
            fp.write("Size: 20\n")
            fp.write("Offset: 20000\n")
            fp.write("Timestamp: 20000\n")
            fp.write("\n")

        with self.assertRaises(AssertionError):
            with content.open():
                pass
