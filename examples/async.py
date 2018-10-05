import asyncio
import itertools
import logging

import udon.log
import udon.async

def coro(name, period):
    for n in itertools.count():
        logging.info("%s: %d", name, n)
        if (name, n) == ("task C", 4):
            udon.async.stop()
        yield from asyncio.sleep(period)

tasks = []

def main():
    logging.info("starting")

    tasks.append(asyncio.ensure_future(coro("task A", 1)))
    tasks.append(asyncio.ensure_future(coro("task B", 1.3)))
    tasks.append(asyncio.ensure_future(coro("task C", 1.7)))

    try:
        yield from asyncio.sleep(10)
    except asyncio.CancelledError:
        logging.info("interrupted")

    for n, task in enumerate(tasks):
        logging.info("cancelling task %d", n)
        task.cancel()

    logging.info("done")

udon.log.init(foreground = True, level = "DEBUG")
udon.async.start(main)
