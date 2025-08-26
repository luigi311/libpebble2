__author__ = "katharine"

from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterator


class BaseEventHandler(metaclass=ABCMeta):

    @abstractmethod
    def register_handler(self, event: object, handler: Callable) -> object:
        """
        Register a handler for an event.

        Args:
            event (object): The event to handle.
            handler (Callable): The handler callable.

        Returns:
            object: A handle that can be used to unregister the handler.
        """

    @abstractmethod
    def unregister_handler(self, handle: object) -> None:
        """
        Remove a handler for an event using a handle returned by :meth:`register_handler`.

        Args:
            handle (object): The handle for the registration to remove.
        """

    @abstractmethod
    def wait_for_event(self, event: object, timeout: float = 10) -> object:
        """
        A blocking wait for an event to be fired.

        Args:
            event (object): The event to wait on.
            timeout (float): How long to wait before raising :exc:`.TimeoutError`

        Returns:
            object: The arguments that were passed to :meth:`broadcast_event`.
        """

    @abstractmethod
    def queue_events(self, event: object) -> "BaseEventQueue":
        """
        Returns a :class:`BaseEventQueue` from which events can be read as they arrive, even if
        the arrive faster than they are removed.

        Args:
            event (object): The events to add to the queue.

        Returns:
            BaseEventQueue: An event queue.
        """

    @abstractmethod
    def broadcast_event(self, event: object, *args: object) -> object:
        """
        Broadcasts an event to all subscribers for that event, as added by :meth:`register_handler`
        :meth:`wait_for_event` and :meth:`queue_events`. All arguments after `event` are passed on
        to the listeners.

        Args:
            event (object): The event to broadcast.
            *args (object): Any arguments to pass on.
        """


class BaseEventQueue(metaclass=ABCMeta):
    """A queue of events, as returned by :meth:`.BaseEventHandler.queue_events`."""

    @abstractmethod
    def close(self) -> None:
        """
        Stop adding events to this queue. It is illegal to call :meth:`get` or iterate over this
        queue after calling :meth:`close`.
        """

    @abstractmethod
    def get(self, timeout: float = 10) -> object:
        """Get the next event in the queue. Blocks until an item is available."""

    @abstractmethod
    def __iter__(self) -> Iterator[object]:
        """Iterate over events in the queue. Blocks if no more items are available."""
