import itertools
import logging
import asyncio

import udon.log
import udon.async

class Client(udon.async.JSONStreamProtocol):

    def received(self, obj):
        logging.info("received: %r", obj)
        self.send(obj)

def main():
    logging.info("starting")

    loop = asyncio.get_event_loop()
    server = yield from loop.create_server(Client,
                                           host = "127.0.0.1",
                                           port = 5554)

    try:
        while True:
            yield from asyncio.sleep(30)
    except asyncio.CancelledError:
        logging.info("interrupted")

    server.close()

    logging.info("done")

udon.log.init(foreground = True, level = "DEBUG")
udon.async.start(main)
