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
import json
import signal
import time
import types

import udon.log
import udon.run

_running = None
def stop():
    _running.cancel()

def start(func):
    global _running
    assert _running is None

    udon.log.debug("async: starting")

    def _signal(signame):
        def _():
            udon.log.debug("async: got signal %s", signame)
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
        udon.log.debug("async: cancelled")
    else:
        udon.log.debug("async: stopped normally")
    finally:
        udon.log.debug("async: closing event loop")
        loop.close()

    udon.log.debug("async: done")


class JSONStreamProtocol(asyncio.Protocol):

    ibuf = None
    transport = None

    LINEMAX = 2 ** 20

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        pass

    def data_received(self, data):
        if self.ibuf:
            data = self.ibuf + data
            del self.ibuf

        for line in data.splitlines(True):
            if not line.endswith(b'\n'):
                self.ibuf = line
                break
            try:
                self.received(json.loads(line.decode().strip()))
            except:
                self.transport.close()
                raise

        if self.ibuf and len(self.ibuf) >= self.LINEMAX:
            udon.log.warn('line too long: %d', len(self.ibuf))
            self.transport.close()

    def send(self, obj):
        self.transport.write(json.dumps(obj).encode() + b'\n')

    def received(self, obj):
        udon.log.info('received: %r', obj)

##
class Schedulable(object):

    timestamp = None
    _period = None
    _suspended = False
    _cancelled = False

    def __init__(self, thread, name = None):
        self.thread = thread
        if name is not None:
            self.name = name

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
        self.thread._uninstall(self, self.name)

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

class DataMixin(object):

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


class Event(Schedulable, DataMixin):

    def __init__(self, thread, name, signal = False, params = None):
        Schedulable.__init__(self, thread, name)
        self._signal = signal
        if params:
            self.update(params)
        if name is not None:
            self['name'] = name

    def is_signal(self):
        return self._signal

    def trigger(self):
        self.timestamp = time.time()
        self.thread._scheduled.discard(self)
        self.thread._pending.add(self)
        self.thread._wakeup()


class Tasklet(Schedulable, DataMixin):

    run_count = 0
    _running = False

    def __init__(self, thread, name, func, params = None):
        Schedulable.__init__(self, thread, name)
        self.func = func
        if params:
            self.update(params)
        if name is not None:
            self['name'] = name

    def set_function(self, func):
        self.func = func

    def is_running(self):
        return self._running

    def run(self):
        if self._suspended or self._cancelled:
            return

        self._running = True
        try:
            value = self.func(self)
            if isinstance(value, types.GeneratorType):
                value = yield from value
        except asyncio.CancelledError:
            udon.log.warn("async: cancelled: %r", self)
        except Exception:
            udon.log.exception("async: exception: %r", self)
        del self._running
        self.run_count += 1

        # the task has cancelled itself.
        if self._cancelled:
            return

        self._reschedule()


class Threadlet(object):

    _future = None
    _coro = None
    _stopping = False

    def __init__(self, name = None):
        self.name = name
        self._schedulables = {}
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

        def default_func(thread):
            while not thread.is_stopping():
                events = yield from thread.idle()

        def default_done(future):
            udon.log.future(future)

        def run():
            if delay:
                yield from asyncio.sleep(delay)
            yield from (func or default_func)(self)

        def done(future):
            self._pending.clear()
            self._scheduled.clear()
            try:
                (when_done or default_done)(future)
            except:
                udon.log.exception("async: done: %r", self)
            del self._coro

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

    def wait(self):
        yield from self._coro

    def idle(self):
        """
        Block until some event or signals occurs.
        Run registered tasks automatically.

        Return the set of events/signals that were triggered,
        or () when the thread is stopping.
        """
        if self._stopping:
            return ()

        while True:
            self._process_scheduled()

            if not self._pending:
                # wait for an event to occur
                yield from self._sleep()
                if self._stopping:
                    return ()
                continue

            # process all pending events
            events = set()
            for item in self._pending:
                if isinstance(item, Tasklet):
                    yield from item.run()
                    if self._stopping:
                        return ()
                elif isinstance(item, Event):
                    events.add(item)
                    if not item._signal:
                        item._reschedule()
            self._pending.clear()

            # clear pending events and return the set of events if necessary
            events = { evt for evt in events if not evt._cancelled }
            if events:
                return events

    def _task(self, func, name = None, params = None):
        task = Tasklet(self, name, func, params = params)
        if name is not None:
            if name in self._schedulables:
                raise KeyError(name)
            self._schedulables[name] = task
        return task

    def _event(self, name = None, signal = False, params = None):
        evt = Event(self, name, signal = signal, params = params)
        if not signal and name is not None:
            if name in self._schedulables:
                raise KeyError(name)
            self._schedulables[name] = evt
        return evt

    def event(self, name = None, **kwargs):
        return self._event(name = name, params = kwargs)

    def signal(self, name = None, **kwargs):
        sig = Event(self, name, signal = True, params = kwargs)
        sig.trigger()

    def tasklet(self, name = None, suspend = False, delay = 0, period = None, **kwargs):
        def _(func):
            sname = name
            if sname is None:
                sname = func.__name__
            task = self._task(func, name = sname, params = None)
            task.set_period(period)
            task.schedule(delay)
            if suspend:
                task.suspend()
            return func
        return _

    def schedule(self, func, delay = 0, name = None):
        """
        Register an delayed call
        """
        def _(task):
            return func()
        task = self._task(_, name = name)
        task.schedule(delay)
        return task

    def _process_scheduled(self):
        now = time.time()
        ready = { evt for evt in self._scheduled if evt.timestamp <= now }
        self._pending.update(ready)
        self._scheduled.difference_update(ready)

    def _sleep(self):
        self._future = asyncio.Future()
        try:
            if self._scheduled:
                timestamp = min(entry.timestamp for entry in self._scheduled)
                delay = max(0.0001, timestamp - time.time())
                yield from asyncio.wait_for(self._future, delay)
            else:
                yield from self._future
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
                udon.log.warn("%r._wakeup(): future cancelled", self)
            elif future.exception():
                udon.log.warn("%r._wakeup(): future exception: %s", self, future.exception())
            else:
                udon.log.warn("%r._wakeup(): future result: %r", self, future.result())
        else:
            future.set_result(None)

    def _uninstall(self, schedulable, name):
        assert schedulable.thread is self
        del schedulable.thread
        self._schedulables.pop(name, None)
