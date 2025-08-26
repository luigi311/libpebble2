__author__ = "katharine"

from collections.abc import Callable

from libpebble2.events.threaded import ThreadedEventHandler


class EventSourceMixin:
    """A convenient mixin to save on repeatedly exposing generic event handler functionality."""

    def __init__(self) -> None:
        self.__handler = ThreadedEventHandler()

    def register_handler(self, event: object, handler: Callable) -> object:
        """
        Registers a handler to be triggered by an event.

        Args:
            event (object): The event to handle.
            handler (Callable): The handler callable.

        Returns:
            object: A handle that can be used to unregister the handler.
        """
        return self.__handler.register_handler(event, handler)

    def unregister_handler(self, handle: object) -> None:
        """
        Unregisters an event handler.

        Args:
            handle (object): The handle for the registration to remove.
        """
        self.__handler.unregister_handler(handle)

    def wait_for_event(self, event: object, timeout: float = 10) -> object:
        """
        Block waiting for the given event. Returns the event params.

        Args:
            event (object): The event to handle.
            timeout (float): The maximum time to wait before raising :exc:`.TimeoutError`.

        Returns:
            object: The event params.
        """
        return self.__handler.wait_for_event(event, timeout=timeout)

    def _broadcast_event(self, event: object, *args: object) -> object:
        return self.__handler.broadcast_event(event, *args)
