__author__ = "katharine"

import random
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from queue import Queue
from typing import NamedTuple

from libpebble2.communication import PebbleConnection
from libpebble2.events.mixin import EventSourceMixin
from libpebble2.exceptions import TimeoutError
from libpebble2.protocol.base import PebblePacket
from libpebble2.protocol.blobdb import (
    BlobCommand,
    BlobDatabaseID,
    BlobResponse,
    BlobStatus,
    ClearCommand,
    DeleteCommand,
    InsertCommand,
)

__all__ = ["BlobDBClient", "SyncWrapper"]


class BlobDBClient(EventSourceMixin):
    """
    Provides a mechanism for interacting with the Pebble's BlobDB service. All methods are
    asynchronous. Messages will be retried automatically if they time out, but all error
    responses from the watch are considered final and will be reported.

    If you want to interact synchronously with BlobDB, see :class:`SyncWrapper`.

    .. note:
       Avoid having multiple :class:`BlobDBClient` instances attached to a single
       :class:`PebbleConnection`. They are likely to interfere and cause failures.

    Args:
        pebble (PebbleConnection): The connection on which to operate.
        timeout (float, optional): The timeout before resending a BlobDB command (default
            5 seconds).
    """

    class _PendingItem(NamedTuple):
        token: int
        data: PebblePacket
        callback: Callable[[BlobStatus], None] | None

    class _PendingAck(NamedTuple):
        timestamp: float
        data: PebblePacket
        callback: Callable[[BlobStatus], None] | None

    def __init__(self, pebble: PebbleConnection, timeout: float = 5) -> None:
        self._pebble = pebble
        self._timeout = timeout
        self._pending_ack = OrderedDict()
        self._queue: Queue[BlobDBClient._PendingItem] = Queue()
        self._lock = threading.Lock()
        self._running = True
        self._pebble.register_endpoint(BlobResponse, self._handle_response)
        self._start_threads()
        EventSourceMixin.__init__(self)

    def _start_threads(self) -> None:
        self._pending_ack_thread = threading.Thread(
            target=self._check_pending_acks,
            daemon=True,
            name="BlobDB-Ack",
        )
        self._queued_data_thread = threading.Thread(
            target=self._send_queued_data,
            daemon=True,
            name="BlobDB-Queue",
        )
        self._pending_ack_thread.start()
        self._queued_data_thread.start()

    def _enqueue(self, item: _PendingItem) -> None:
        self._queue.put(item)

    def insert(
        self,
        database: BlobDatabaseID,
        key: uuid.UUID,
        value: bytes,
        callback: Callable[[BlobStatus], None] | None = None,
    ) -> None:
        """
        Insert an item into the given database.

        Args:
            database (BlobDatabaseID): The database into which to insert the value.
            key (uuid.UUID): The key to insert.
            value (bytes): The value to insert.
            callback (callable, optional): A callback to be called on success or failure.
        """
        token = self._get_token()
        self._enqueue(
            self._PendingItem(
                token,
                BlobCommand(
                    token=token,
                    database=database,
                    content=InsertCommand(key=key.bytes, value=value),
                ),
                callback,
            ),
        )

    def delete(
        self,
        database: BlobDatabaseID,
        key: uuid.UUID,
        callback: Callable[[BlobStatus], None] | None = None,
    ) -> None:
        """
        Delete an item from the given database.

        Args:
            database (BlobDatabaseID): The database from which to delete the value.
            key (uuid.UUID): The key to delete.
            callback (callable, optional): A callback to be called on success or failure.
        """
        token = self._get_token()
        self._enqueue(
            self._PendingItem(
                token,
                BlobCommand(token=token, database=database, content=DeleteCommand(key=key.bytes)),
                callback,
            ),
        )

    def clear(
        self,
        database: BlobDatabaseID,
        callback: Callable[[BlobStatus], None] | None = None,
    ) -> None:
        """
        Wipe the given database. This only affects items inserted remotely; items inserted on the
        watch (e.g. alarm clock timeline pins) are not removed.

        Args:
            database (BlobDatabaseID): The database to wipe.
            callback (callable, optional): A callback to be called on success or failure.
        """
        token = self._get_token()
        self._enqueue(
            self._PendingItem(
                token,
                BlobCommand(token=token, database=database, content=ClearCommand()),
                callback,
            ),
        )

    def _check_pending_acks(self) -> None:
        while self._running:
            with self._lock:
                # check pending acks
                now = time.time()
                for token, pending in list(self._pending_ack.items()):
                    if now - pending.timestamp > self._timeout:
                        del self._pending_ack[token]
                        self._enqueue(self._PendingItem(token, pending.data, pending.callback))
            time.sleep(5)

    def _send_queued_data(self) -> None:
        while True:
            token, data, callback = self._queue.get()
            with self._lock:
                self._pending_ack[token] = self._PendingAck(time.time(), data, callback)
                self._pebble.send_packet(data)
            time.sleep(0.05)

    @staticmethod
    def _get_token() -> int:
        return random.randrange(1, 2**16 - 1, 1)

    def _handle_response(self, packet: BlobResponse) -> None:
        if packet.response == BlobStatus.TryLater:
            # Do nothing, wait for the packet to timeout and re-send
            return

        with self._lock:
            if packet.token in self._pending_ack:
                pending = self._pending_ack[packet.token]
                del self._pending_ack[packet.token]

                if callable(pending.callback):
                    pending.callback(packet.response)


class SyncWrapper:
    """
    Wraps a :class:`BlobDBClient` call and returns when it completes.

    Use it like this: ::

       SyncWrapper(blobdb_client.insert, some_key, some_value).wait()

    Args:
        method (callable): The :class:`BlobDBClient` method to call.
        *args: Arguments to pass to the method.
        **kwargs: Keyword arguments to pass to the method.
    """

    def __init__(self, method: Callable, *args: object, **kwargs: object) -> None:
        self.event = threading.Event()
        self.result = None
        method(*args, callback=self.callback, **kwargs)

    def wait(self, timeout: float = 15) -> object:
        """
        Waits for the BlobDB operation to complete or times out.

        Args:
            timeout (float, optional): The maximum time to wait for the operation to complete
                (default is 15 seconds).

        Returns:
            object: The result of the BlobDB operation.

        Raises:
            TimeoutError: If the operation does not complete within the specified timeout.
        """
        if not self.event.wait(timeout):
            msg = "BlobDB operation timed out"
            raise TimeoutError(msg)
        return self.result

    def callback(self, *args: object) -> None:
        """
        Callback method to be invoked when the BlobDB operation completes.

        Args:
            *args (object): Positional arguments, where the first argument is the result.
        """
        self.result = args[0]
        self.event.set()
