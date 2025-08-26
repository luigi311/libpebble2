__author__ = "katharine"

import logging
import queue
import threading
from collections.abc import Callable, Iterator

from libpebble2.exceptions import TimeoutError

from . import BaseEventHandler, BaseEventQueue

logger = logging.getLogger("libpebble2.events")


class ThreadedEventHandler(BaseEventHandler):
    """A threaded implementation of :class:`.BaseEventHandler`."""

    def __init__(self) -> None:
        self._handlers = {}
        self._handle_map = {}
        self._counter = 0
        self._handler_lock = threading.RLock()

    def register_handler(self, event: object, handler: Callable) -> object:
        """Registers a handler to be triggered by an event."""
        with self._handler_lock:
            self._counter += 1
            self._handlers.setdefault(event, {})[self._counter] = handler
            self._handle_map[self._counter] = event
            return self._counter

    def unregister_handler(self, handle: object) -> None:
        """Unregisters an event handler."""
        with self._handler_lock:
            if handle not in self._handle_map:
                return
            del self._handlers[self._handle_map[handle]][handle]
            del self._handle_map[handle]

    def wait_for_event(self, event: object, timeout: float = 10) -> object:
        """Block waiting for the given event. Returns the event params."""
        return _BlockingEventWait(self, event).wait(timeout=timeout)

    def queue_events(self, event: object) -> BaseEventQueue:
        """Returns a :class:`BaseEventQueue` from which events can be read as they arrive."""
        return _QueuedEventWait(self, event)

    def broadcast_event(self, event: object, *args: object) -> object:
        """Broadcasts an event to all subscribers for that event."""
        with self._handler_lock:
            handlers = list(self._handlers.get(event, {}).values())
        for handler in handlers:
            try:
                handler(*args)
            except Exception:
                logger.exception("Event handler for %r threw", event)


class _BlockingEventWait:
    def __init__(self, events: ThreadedEventHandler, event: object) -> None:
        self.block = threading.Event()
        self.event_handler = events
        self.result = None
        self.handle = self.event_handler.register_handler(event, self.handle_result)

    def handle_result(self, *args: object) -> None:
        (self.result,) = args
        self.event_handler.unregister_handler(self.handle)
        self.block.set()

    def wait(self, timeout: float = 10) -> object:
        if not self.block.wait(timeout=timeout):
            raise TimeoutError
        return self.result


class _QueuedEventWait(BaseEventQueue):
    def __init__(self, events: ThreadedEventHandler, event: object) -> None:
        self.queue = queue.Queue()
        self.event_handler = events
        self.handle = self.event_handler.register_handler(event, self._handle_event)

    def _handle_event(self, arg: object) -> None:
        self.queue.put(arg)

    def close(self) -> None:
        self.event_handler.unregister_handler(self.handle)

    def get(self, timeout: float = 10) -> object:
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError

    def __iter__(self) -> Iterator[object]:
        """Iterate over events in the queue. Blocks if no more items are available."""
        while True:
            yield self.get()
