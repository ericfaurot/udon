#
# Copyright (c) 2018 Eric Faurot <eric@faurot.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
import asyncio
import inspect
import logging
import signal
import time
import types


def _logger(logger):
    return logger if logger is not None else logging.getLogger(__name__)


_running = None
def stop():
    _running.cancel()

def start(func, logger = None):
    global _running
    assert _running is None

    logger = _logger(logger)

    logger.debug("starting")

    def _signal(signame):
        def _():
            logger.debug("got signal %s", signame)
            if _running:
                _running.cancel()
        return _

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, _signal('SIGINT'))
    loop.add_signal_handler(signal.SIGTERM, _signal('SIGTERM'))

    try:
        _running = asyncio.ensure_future(func())
        loop.run_until_complete(_running)
    except asyncio.CancelledError:
        logger.debug("cancelled")
    else:
        logger.debug("stopped normally")
    finally:
        logger.debug("closing event loop")
        loop.close()

    logger.debug("done")


def collect_future(future, logger = None):
    logger = _logger(logger)
    if future.cancelled():
        logger.warning("FUTURE CANCELLED")
    elif future.exception():
        try:
            raise future.exception()
        except:
            logger.exception("FUTURE EXCEPTION")
    else:
        result = future.result()
        if result is not None:
            logger.warning("FUTURE RESULT: %r", result)


class Schedulable:

    timestamp = None
    _period = None
    _suspended = False
    _cancelled = False

    def __init__(self, thread):
        self.thread = thread

    def set_period(self, period = None):
        self._period = period

    def schedule(self, delay = 0, period = None):
        if period is not None:
            self._period = period
        self.schedule_at(time.time() + delay)

    def schedule_at(self, timestamp):
        if timestamp is None:
            timestamp = time.time()
        self.timestamp = timestamp
        self.thread._scheduled.add(self)
        self.thread._wakeup()

    def cancel(self):
        if self._cancelled:
            return
        self._cancelled = True
        self.unschedule()
        self.thread._uninstall(self)

    def unschedule(self):
        self.thread._scheduled.discard(self)
        self.thread._wakeup()

    def is_scheduled(self):
        return self in self.thread._scheduled

    def is_pending(self):
        return self in self.thread._pending

    def suspend(self):
        if self._suspended:
            return
        self._suspended = True
        self.unschedule()

    def resume(self):
        if not self._suspended:
            return
        del self._suspended
        if not self._cancelled:
            self.schedule_at(self.timestamp)

    def _reschedule(self):
        # reschedule periodic events if not scheduled already.
        if self._period is not None and not self.is_scheduled():
            self.schedule(self._period)
        if self._suspended:
            self.unschedule()


class DataMixin:

    _data =  None

    def update(self, obj):
        if obj:
            for key, value in obj.items():
                self[key] = value

    def __contains__(self, key):
        if self._data is None:
            return False
        return key in self._data

    def __getitem__(self, key):
        if self._data is None:
            raise KeyError(key)
        return self._data[key]

    def __setitem__(self, key, value):
        if self._data is None:
            self._data = {}
        self._data[key] = value

    def __delitem__(self, key):
        if self._data is None:
            raise KeyError(key)
        return self._data[key]


class EventMixin:

    thread = None

    def is_signal(self):
        return False

    def trigger(self):
        self.timestamp = time.time()
        self.thread._scheduled.discard(self)
        self.thread._pending.add(self)
        self.thread._wakeup()


class Event(Schedulable, EventMixin, DataMixin):

    def __init__(self, thread, params = None):
        Schedulable.__init__(self, thread)
        if params:
            self.update(params)

class Signal(EventMixin, DataMixin):

    def __init__(self, thread, params = None):
        self.thread = thread
        if params:
            self.update(params)

    def is_signal(self):
        return True


class Tasklet(Schedulable, DataMixin):

    _running = False
    _handler = None

    def __init__(self, thread, params = None):
        Schedulable.__init__(self, thread)
        if params:
            self.update(params)

    def set_handler(self, handler):
        self._handler = handler

    def is_running(self):
        return self._running

    async def run(self):
        if self._suspended or self._cancelled:
            return

        self._running = True
        try:
            value = self._handler(self)
            if isinstance(value, types.CoroutineType):
                value = await value
            elif isinstance(value, types.GeneratorType):
                value = await value
        except asyncio.CancelledError:
            self.thread.logger.warning("cancelled: %r", self)
        except:
            self.thread.logger.exception("exception: %r", self)
        del self._running

        # the task has cancelled itself.
        if self._cancelled:
            return

        self._reschedule()


class Threadlet:

    _future = None
    _coro = None
    _stopping = False
    _ready = None

    def __init__(self, logger = None):
        self.logger = _logger(logger)
        self._schedulables = {}
        self._schedulables_rev = {}
        self._pending = set()
        self._scheduled = set()

    def __contains__(self, key):
        return key in self._schedulables

    def __getitem__(self, key):
        return self._schedulables[key]

    def is_running(self):
        return self._coro is not None

    def is_stopping(self):
        return self._stopping

    def start(self, func = None, when_done = None, delay = 0):
        assert not self.is_running()

        async def default_func(thread):
            await thread.idle()

        def default_done(future):
            collect_future(future, self.logger)

        async def run():
            if delay:
                await asyncio.sleep(delay)
            await (func or default_func)(self)

        def done(future):
            self._pending.clear()
            self._scheduled.clear()
            try:
                (when_done or default_done)(future)
            except:
                self.logger.exception("done: %r", self)
            del self._coro

        if func is not None and not inspect.iscoroutinefunction(func):
            raise TypeError("not a coroutine function")

        self._coro = asyncio.ensure_future(run())
        self._coro.add_done_callback(done)

    def stop(self):
        if not self._stopping:
            self._stopping = True
            self._wakeup()

    def join(self, loop = None):
        if loop is None:
            loop = asyncio.get_event_loop()
        loop.run_until_complete(self._coro)

    def __await__(self):
        yield from self._coro

    async def idle(self):
        async for _ in self:
            pass

    async def __aiter__(self):
        while not self._stopping:
            if not self._ready:
                # wait for the next batch of events
                self._ready = await self._wait_for_events()
                continue
            item = self._ready.pop(0)
            if isinstance(item, Tasklet):
                await item.run()
            elif isinstance(item, Signal):
                yield item
            elif isinstance(item, Event):
                yield item
                item._reschedule()

    async def _wait_for_events(self):
        while not self._stopping:
            # get the set of scheduled events that are ready
            now = time.time()
            events = { evt for evt in self._scheduled if evt.timestamp <= now }
            self._scheduled.difference_update(events)
            # if there are pending events or signals, add them to the set
            if self._pending:
                events.update(self._pending)
                self._pending.clear()
            if events:
                return sorted(events, key = lambda x: x.timestamp)
            await self._sleep()

    def _task(self, func, name, params = None):
        task = Tasklet(self, params = params)
        task.set_handler(func)
        if name is not None:
            self._register_schedulable(name, task)
        return task

    def _event(self, name, params = None):
        event = Event(self, params = params)
        if name is not None:
            self._register_schedulable(name, event)
        return event

    def _register_schedulable(self, name, schedulable):
        if name in self._schedulables:
            raise KeyError(name)
        self._schedulables[name] = schedulable
        self._schedulables_rev[schedulable] = name

    def _unregister_schedulable(self, schedulable):
        name = self._schedulables_rev.pop(schedulable, None)
        if name is not None:
            self._schedulables.pop(name)

    def event(self, name = None, **kwargs):
        if name is not None:
            kwargs["name"] = name
        return self._event(name, params = kwargs)

    def signal(self, name = None, **kwargs):
        if name is not None:
            kwargs["name"] = name
        sig = Signal(self, params = kwargs)
        sig.trigger()

    def tasklet(self, name = None, suspend = False, delay = 0, period = None, **kwargs):
        def _(func):
            sname = name
            if sname is None:
                sname = func.__name__
            task = self._task(func, sname, params = kwargs)
            task.set_period(period)
            task.schedule(delay)
            if suspend:
                task.suspend()
            return func
        return _

    def set_tasklet(self, func, **kwargs):
        self.tasklet(**kwargs)(func)

    def schedule(self, func, delay = 0, name = None):
        """
        Register an delayed call
        """
        def _(task):
            return func()
        task = self._task(_, name)
        task.schedule(delay)
        return task

    async def _sleep(self):
        self._future = asyncio.Future()
        try:
            if self._scheduled:
                timestamp = min(entry.timestamp for entry in self._scheduled)
                delay = max(0.0001, timestamp - time.time())
                await asyncio.wait_for(self._future, delay)
            else:
                await self._future
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            pass
        finally:
            if self._future:
                del self._future

    def _wakeup(self):
        if not self._future:
            return

        future = self._future
        del self._future
        if future.done():
            if future.cancelled():
                self.logger.warning("%r._wakeup(): future cancelled", self)
            elif future.exception():
                self.logger.warning("%r._wakeup(): future exception: %s", self, future.exception())
            else:
                self.logger.warning("%r._wakeup(): future result: %r", self, future.result())
        else:
            future.set_result(None)

    def _uninstall(self, schedulable):
        assert schedulable.thread is self
        del schedulable.thread
        self._unregister_schedulable(schedulable)


class ThreadMixin:

    __thread = None

    @property
    def thread(self):
        if self.__thread is None:
            self.__thread = Threadlet()
        return self.__thread

    def thread_start(self):
        self.thread.start(self.thread_run, when_done = self.__thread_exit)

    def __thread_exit(self, future):
        collect_future(future)
        self.thread_exit(self.thread)

    async def thread_run(self, thread):
        await thread.idle()

    def thread_exit(self, thread):
        pass
