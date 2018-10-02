import itertools
import asyncio

import udon.log
import udon.async

class Client(udon.async.JSONStreamProtocol):

    def received(self, obj):
        udon.log.info("received: %r", obj)
        self.send(obj)

def main():
    udon.log.info("starting")

    loop = asyncio.get_event_loop()
    server = yield from loop.create_server(Client,
                                           host = "127.0.0.1",
                                           port = 5554)

    try:
        while True:
            yield from asyncio.sleep(30)
    except asyncio.CancelledError:
        udon.log.info("interrupted")

    server.close()

    udon.log.info("done")

udon.log.init(foreground = True)
udon.async.start(main)
