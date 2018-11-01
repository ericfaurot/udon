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

        sumin = hashlib.sha256(datain).hexdigest()
        sumout = hashlib.sha256(dataout).hexdigest()

        self.assertEqual(len(datain), len(dataout))
        self.assertEqual(datain, dataout)
        self.assertEqual(sumin, sumout)

        has_size = False
        has_cksum = False
        for key, val in content.headers():
            if key == "Size":
                self.assertFalse(has_size)
                self.assertEqual(len(datain), int(val))
                has_size = True
            if key == "Checksum-SHA256":
                self.assertFalse(has_cksum)
                self.assertEqual(sumin, val)
                has_cksum = True

        self.assertTrue(has_size)
        self.assertTrue(has_cksum)
                
    def test_headers(self):
        content = self.content()
        content.write(b'')
        for key, val in content.headers():
            self.assertIsInstance(key, str)
            self.assertIsInstance(val, str)

    def test_meta(self):
        content = self.content()
        content.write(b'', meta = [
            ("Foo", "Bar"),
            ("Baz", 4),
            ("Foo2", b"Bar"),
        ])
        for key, val in content.headers():
            self.assertIsInstance(key, str)
            self.assertIsInstance(val, str)

    def test_bad_meta(self):
        content = self.content()

        with self.assertRaises(ValueError):
            content.write(b'', meta = [ ("Foo:", "Bar") ])

        with self.assertRaises(ValueError):
            content.write(b'', meta = [ ("Foo\n", "") ])

        with self.assertRaises(ValueError):
            content.write(b'', meta = [ ("Foo", "Bax\n") ])

        with self.assertRaises(ValueError):
            content.write(b'', meta = [ ("Foo", "Bax\n") ])

    def test_too_large(self):
        content = self.content()
        with self.assertRaises(udon.content.HeaderTooLarge):
            content.write(b'', meta = [ ("Foo", "Bar" * 999999) ])

    def test_invalid_open(self):
        content = self.content("/etc/passwd")
        with self.assertRaises(udon.content.InvalidFileFormat):
            with content.open():
                pass

    def test_invalid_headers(self):
        content = self.content("/etc/passwd")
        with self.assertRaises(udon.content.InvalidFileFormat):
            content.headers()

    @unittest.skip
    def test_broken_file(self):
        content = self.content()
        with open(content.path, "w") as fp:
            fp.write("Offset: 20000\n")

        with self.assertRaises(udon.content.InvalidFileFormat):
            with content.open():
                pass
