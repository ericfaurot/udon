import asyncio
import itertools
import logging

import udon.log
import udon.asynchronous

TESTS = []
def test():
    def _(func):
        TESTS.append(func)
    return _

@test()
def test_0():
    thread = udon.asynchronous.Threadlet()
    thread.start()
    thread.stop()
    thread.join()

@test()
def test_1():
    async def run(thread):
        await thread.idle()
    thread = udon.asynchronous.Threadlet()
    thread.start(run)
    thread.stop()
    thread.join()

@test()
def test_2():
    async def run(thread):
        thread.stop()
        await thread.idle()
    thread = udon.asynchronous.Threadlet()
    thread.start(run)
    thread.join()

@test()
def test_3():
    thread = udon.asynchronous.Threadlet()
    thread.schedule(thread.stop, delay = 1)
    thread.start()
    thread.join()

@test()
def test_4():
    thread = udon.asynchronous.Threadlet()
    thread.schedule(thread.stop, delay = 1)
    def tick():
        print("tick!")
        thread.schedule(tick, delay = .1)
    thread.schedule(tick)
    thread.start()
    thread.join()

@test()
def test_5():
    thread = udon.asynchronous.Threadlet()
    thread.schedule(thread.stop, delay = 1)
    def tick(task):
        print("tick!")
    thread.set_tasklet(tick, period = .1)
    thread.start()
    thread.join()

@test()
def test_6():
    thread = udon.asynchronous.Threadlet()
    def tick(task):
        print("tick!")
        if task["count"] == 5:
            task.thread.stop()
        task["count"] += 1
    thread.set_tasklet(tick, period = .1, count = 0)
    thread.start()
    thread.join()

@test()
def test_7():
    def tick(task):
        print("tick!")
        if task["count"] == 5:
            task.cancel()
        task["count"] += 1
    def tack(task):
        print("tack!")
        if task["count"] == 10:
            task.thread.stop()
        task["count"] += 1
    thread = udon.asynchronous.Threadlet()
    thread.set_tasklet(tick, period = .1, count = 0)
    thread.set_tasklet(tack, period = .1, count = 0)
    thread.start()
    thread.join()

@test()
def test_8():

    thread = udon.asynchronous.Threadlet()
    async def run(thread):
        async for event in thread:
            logging.info("%s: %s",
                         'signal' if event.is_signal() else 'event',
                         event['name'])
        logging.info("done")
    thread.start(run)

    def tick(task):
        thread.signal("blip")
    thread2 = udon.asynchronous.Threadlet()
    thread2.set_tasklet(tick, period = .2)
    thread2.schedule(thread.stop, delay = 1)
    thread2.start()

    thread.join()
    thread2.stop()
    thread2.join()

@test()
def test_9():

    async def run(thread):
        stop = thread.event("stop")
        ev0 = thread.event("ev0")
        ev1 = thread.event("ev1")
        ev2 = thread.event("ev2")

        stop.schedule(5)
        ev0.schedule(.1)
        ev2.schedule()
        async for event in thread:
            logging.info("event: %s", event['name'])
            if event is stop:
                break
            elif event is ev0:
                ev1.schedule(1)
            elif event is ev1:
                ev0.schedule(1)
                ev2.unschedule()
            elif event is ev2:
                ev2.schedule(.1)
        logging.info("done")

    thread = udon.asynchronous.Threadlet()
    thread.start(run)
    thread.join()

@test()
def test_10():

    async def run(thread):

        @thread.tasklet(delay = 5)
        def stop(task):
            thread.stop()

        @thread.tasklet(delay = .1, period = 1)
        def ev0(task):
            logging.info("task: ev0")
            task.suspend()
            thread['ev1'].resume()

        @thread.tasklet(delay = .1, period = 1)
        def ev1(task):
            logging.info("task: ev1")
            task.suspend()
            thread['ev0'].resume()
            if 'ev2' in thread:
                thread['ev2'].cancel()

        @thread.tasklet(period = .1)
        def ev2(task):
            logging.info("task: ev2")

        async for event in thread:
            logging.info("event: %s", event['name'])

        logging.info("done")

    thread = udon.asynchronous.Threadlet()
    thread.start(run)
    thread.join()

@test()
def test_11():
    def tick(task):
        if task["count"] == 10:
            task.thread.stop()
            return
        print("tick, delay:", task['delay'])
        task['delay'] *= 1.2
        task['count'] += 1
        task.schedule(task['delay'])
    thread = udon.asynchronous.Threadlet()
    thread.set_tasklet(tick, count = 0)
    thread['tick']['delay'] = .1
    thread.start()
    thread.join()

@test()
def test_12():

    async def run(thread):
        evt = thread.event("foo")
        evt.set_period(.2)
        evt.schedule()
        evt = thread.event("bar")
        evt.set_period(.5)
        evt.schedule()
        n = 0
        async for event in thread:
            logging.info("%s: %s",
                         'signal' if event.is_signal() else 'event',
                         event['name'])
            n += 1
            if n == 10:
                thread.stop()

    thread = udon.asynchronous.Threadlet()
    thread.start(run)
    thread.join()

@test()
def test_13():

    async def run1(thread):
        logging.info("run1: starting...")
        await asyncio.sleep(1)
        logging.info("run1: done")

    async def run2(thread):
        logging.info("run2: waiting thread1...")
        await thread1
        logging.info("run2: done")

    thread1 = udon.asynchronous.Threadlet()
    thread1.start(run1)
    thread2 = udon.asynchronous.Threadlet()
    thread2.start(run2)
    thread2.join()

def main():
    logging.info("starting")

    for test in TESTS:
        logging.info("===> %s" % test.__name__)
        test()

    logging.info("exit")

if __name__ == "__main__":
    udon.log.init(foreground = True, level = "DEBUG")
    main()
