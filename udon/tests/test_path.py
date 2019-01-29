import os
import unittest

import udon.path


class Fail(Exception):
    pass


class TestCache(unittest.TestCase):

    def test_temporary(self):
        with udon.path.temporary() as fp:
            fp.write(b'foo')
        self.assertTrue(os.path.isfile(fp.name))

        with open(fp.name, 'rb') as fp2:
            self.assertEqual(fp2.read(), b'foo')

    def test_temporary_fail(self):
        with self.assertRaises(Fail):
            with udon.path.temporary() as fp:
                fp.write(b'foo')
                raise Fail
        self.assertFalse(os.path.isfile(fp.name))

    def test_overwriting(self):
        with udon.path.temporary() as target:
            target.write(b'one')

        with udon.path.overwriting(target.name) as fp:
            fp.write(b'two')
            with open(target.name, 'rb') as rfp:
                self.assertEqual(rfp.read(), b'one')
        self.assertFalse(os.path.isfile(fp.name))

        with open(target.name, 'rb') as fp:
            self.assertEqual(fp.read(), b'two')

    def test_overwriting_fail(self):
        with udon.path.temporary() as target:
            target.write(b'one')

        with self.assertRaises(Fail):
            with udon.path.overwriting(target.name) as fp:
                fp.write(b'two')
                with open(target.name, 'rb') as rfp:
                    self.assertEqual(rfp.read(), b'one')
                raise Fail
        self.assertFalse(os.path.isfile(fp.name))

        with open(target.name, 'rb') as fp:
            self.assertEqual(fp.read(), b'one')
