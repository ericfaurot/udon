import asyncio
import unittest

import udon.asynchronous


class TestThreadlet(unittest.TestCase):

    def test_none(self):
        thread = udon.asynchronous.Threadlet()
        thread.start()
        thread.stop()
        thread.join()

    def test_double_start(self):
        thread = udon.asynchronous.Threadlet()
        thread.start()
        with self.assertRaises(AssertionError):
            thread.start()
        thread.stop()
        thread.join()

    def test_need_coroutine(self):
        def _(thread):
            pass
        thread = udon.asynchronous.Threadlet()
        with self.assertRaises(TypeError):
            thread.start(_)

    def test_empty(self):
        async def _(thread):
            pass
        thread = udon.asynchronous.Threadlet()
        thread.start(_)
        thread.join()

    def test_wait(self):
        async def _(thread):
            await asyncio.sleep(.1)
        thread = udon.asynchronous.Threadlet()
        thread.start(_)
        thread.join()

    def test_schedule(self):
        thread = udon.asynchronous.Threadlet()
        thread.schedule(thread.stop, .1)
        thread.start()
        thread.join()

    def test_signal(self):
        def _signal():
            thread.signal("foo")
        async def _main(thread):
            async for event in thread:
                self.assertTrue(event.is_signal())
                self.assertEqual(event['name'], "foo")
                break
        thread = udon.asynchronous.Threadlet()
        thread.schedule(_signal, .1)
        thread.start(_main)
        thread.join()

    def test_iterevents(self):

        def _signal():
            thread.signal("foo")
        def _signal2():
            thread.signal("bar")
            thread.signal("baz")

        seen = []
        async def _main(thread):
            async for event in thread:
                seen.append(event["name"])
                if event["name"] == "bar":
                    break
            async for event in thread:
                seen.append(event["name"])

        thread = udon.asynchronous.Threadlet()
        thread.schedule(_signal, .1)
        thread.schedule(_signal2, .2)
        thread.schedule(_signal, .3)
        thread.schedule(thread.stop, 1)
        thread.start(_main)
        thread.join()
        self.assertEqual(seen, ["foo", "bar", "baz", "foo"])
