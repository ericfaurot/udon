import itertools
import asyncio

import udon.log
import udon.async

def coro(name, period):
    for n in itertools.count():
        udon.log.info("%s: %d", name, n)
        if (name, n) == ("task C", 4):
            udon.async.stop()
        yield from asyncio.sleep(period)

tasks = []

def main():
    udon.log.info("starting")

    tasks.append(asyncio.ensure_future(coro("task A", 1)))
    tasks.append(asyncio.ensure_future(coro("task B", 1.3)))
    tasks.append(asyncio.ensure_future(coro("task C", 1.7)))

    try:
        yield from asyncio.sleep(10)
    except asyncio.CancelledError:
        udon.log.info("interrupted")

    for n, task in enumerate(tasks):
        udon.log.info("cancelling task %d", n)
        task.cancel()

    udon.log.info("done")

udon.log.init(foreground = True)
udon.async.start(main)
