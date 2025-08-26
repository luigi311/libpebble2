import threading
import time

import pytest
from libpebble2.events.mixin import EventSourceMixin
from libpebble2.events.threaded import ThreadedEventHandler
from libpebble2.exceptions import TimeoutError


def test_threaded_event_handler_basic():
    ev = ThreadedEventHandler()
    got = []

    h = ev.register_handler("x", lambda v: got.append(v))
    ev.broadcast_event("x", 123)
    time.sleep(0.01)
    assert got == [123]

    ev.unregister_handler(h)
    ev.broadcast_event("x", 456)
    time.sleep(0.01)
    assert got == [123]  # unchanged


def test_threaded_event_handler_wait_and_queue():
    ev = ThreadedEventHandler()

    def later():
        time.sleep(0.02)
        ev.broadcast_event(("A", 1), "ok")

    threading.Thread(target=later, daemon=True).start()
    assert ev.wait_for_event(("A", 1), timeout=0.5) == "ok"

    q = ev.queue_events(("A", 2))
    ev.broadcast_event(("A", 2), "one")
    ev.broadcast_event(("A", 2), "two")
    assert q.get(timeout=0.1) == "one"
    assert q.get(timeout=0.1) == "two"
    q.close()
    with pytest.raises(TimeoutError):
        q.get(timeout=0.01)


def test_event_source_mixin_routes():
    class E(EventSourceMixin):
        def __init__(self):
            super().__init__()

        def go(self):
            self._broadcast_event("t", 5)

    e = E()
    seen = []
    handle = e.register_handler("t", lambda v: seen.append(v))
    e.go()
    time.sleep(0.01)
    assert seen == [5]
    e.unregister_handler(handle)
