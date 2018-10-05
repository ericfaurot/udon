import asyncio
import itertools
import logging

import udon.log
import udon.async

TESTS = []
def test():
    def _(func):
        TESTS.append(func)
    return _

@test()
def test_0():
    thread = udon.async.Threadlet()
    thread.start()
    thread.stop()
    thread.join()

@test()
def test_1():
    def run(thread):
        yield from thread.idle()
    thread = udon.async.Threadlet()
    thread.start(run)
    thread.stop()
    thread.join()

@test()
def test_2():
    def run(thread):
        thread.stop()
        yield from thread.idle()
    thread = udon.async.Threadlet()
    thread.start(run)
    thread.join()

@test()
def test_3():
    thread = udon.async.Threadlet()
    thread.schedule(thread.stop, delay = 1)
    thread.start()
    thread.join()

@test()
def test_4():
    thread = udon.async.Threadlet()
    thread.schedule(thread.stop, delay = 1)
    def tick():
        print("tick!")
        thread.schedule(tick, delay = .1)
    thread.schedule(tick)
    thread.start()
    thread.join()

@test()
def test_5():
    thread = udon.async.Threadlet()
    thread.schedule(thread.stop, delay = 1)
    @thread.tasklet(period = .1)
    def tick(task):
        print("tick!")
    thread.start()
    thread.join()

@test()
def test_6():
    thread = udon.async.Threadlet()
    @thread.tasklet(period = .1)
    def tick(task):
        print("tick!")
        if task.run_count == 5:
            thread.stop()
    thread.start()
    thread.join()

@test()
def test_7():
    thread = udon.async.Threadlet()
    @thread.tasklet(period = .1)
    def tick(task):
        print("tick!")
        if task.run_count == 5:
            task.cancel()
    @thread.tasklet(period = .1)
    def tack(task):
        print("tack!")
        if task.run_count == 10:
            thread.stop()
    thread.start()
    thread.join()

@test()
def test_8():

    thread = udon.async.Threadlet()
    def run(thread):
        while not thread.is_stopping():
            events = yield from thread.idle()
            for event in events:
                logging.info("%s: %s",
                             'signal' if event.is_signal() else 'event',
                              event['name'])
        logging.info("done")
    thread.start(run)

    thread2 = udon.async.Threadlet()
    @thread2.tasklet(period = .2)
    def tick(task):
        thread.signal("blip")
    thread2.schedule(thread.stop, delay = 1)
    thread2.start()

    thread.join()
    thread2.stop()
    thread2.join()

@test()
def test_9():

    def run(thread):
        stop = thread.event("stop")
        ev0 = thread.event("ev0")
        ev1 = thread.event("ev1")
        ev2 = thread.event("ev2")

        stop.schedule(5)
        ev0.schedule(.1)
        ev2.schedule()
        while not thread.is_stopping():
            events = yield from thread.idle()
            for event in events:
                logging.info("event: %s", event['name'])
                if event is stop:
                    return
                elif event is ev0:
                    ev1.schedule(1)
                elif event is ev1:
                    ev0.schedule(1)
                    ev2.unschedule()
                elif event is ev2:
                    ev2.schedule(.1)

        logging.info("done")

    thread = udon.async.Threadlet()
    thread.start(run)
    thread.join()

@test()
def test_10():

    def run(thread):

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

        while not thread.is_stopping():
            events = yield from thread.idle()
            for event in events:
                logging.info("event: %s", event['name'])

        logging.info("done")

    thread = udon.async.Threadlet()
    thread.start(run)
    thread.join()

@test()
def test_11():
    thread = udon.async.Threadlet()
    @thread.tasklet()
    def tick(task):
        if task.run_count == 10:
            thread.stop()
            return
        print("tick, delay:", task['delay'])
        task['delay'] *= 1.2
        task.schedule(task['delay'])
    thread['tick']['delay'] = .1
    thread.start()
    thread.join()

@test()
def test_12():

    def run(thread):
        evt = thread.event("foo")
        evt.set_period(.2)
        evt.schedule()
        evt = thread.event("bar")
        evt.set_period(.5)
        evt.schedule()
        n = 0
        while not thread.is_stopping():
            events = yield from thread.idle()
            for event in events:
                logging.info("%s: %s",
                             'signal' if event.is_signal() else 'event',
                             event['name'])
            n += 1
            if n == 10:
                thread.stop()

    thread = udon.async.Threadlet()
    thread.start(run)
    thread.join()

def main():
    logging.info("starting")

    for test in TESTS:
        logging.info("===> %s" % test.__name__)
        test()

    logging.info("exit")

if __name__ == "__main__":
    udon.log.init(foreground = True, level = "DEBUG")
    main()
