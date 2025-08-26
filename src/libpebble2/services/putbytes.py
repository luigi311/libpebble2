__author__ = "katharine"

from enum import IntFlag

from libpebble2.communication import PebbleConnection
from libpebble2.events.mixin import EventSourceMixin
from libpebble2.exceptions import PutBytesError
from libpebble2.protocol import transfers
from libpebble2.util import stm32_crc

__all__ = ["PutBytes", "PutBytesType"]


class PutBytesType(IntFlag):
    """
    Enumeration of types for PutBytes operations.

    Attributes:
        Firmware (int): Used for firmware files.
        Recovery (int): Used for recovery files.
        SystemResources (int): Used for system resource files.
        Resources (int): Used for general resource files.
        Binary (int): Used for binary files.
        File (int): Used for generic files.
        Worker (int): Used for worker files.
    """

    Firmware = 1
    Recovery = 2
    SystemResources = 3
    Resources = 4
    Binary = 5
    File = 6
    Worker = 7


class PutBytes(EventSourceMixin):
    """
    Synchronously sends data to the watch over PutBytes.

    Args:
        pebble (PebbleConnection): The Pebble to send data to.
        object_type (int): The type of data being sent.
        object (bytes): The data to send.
        bank (int, optional): The bank to install the data to, if applicable.
        filename (str, optional): The filename of the data, if applicable
        app_install_id (int, optional): This is used during app installations on 3.x.
            It is mutually exclusive with ``bank`` and ``filename``.
    """

    def __init__(
        self,
        pebble: PebbleConnection,
        object_type: int,
        object: bytes,
        bank: int = 0,
        filename: str = "",
        app_install_id: int | None = None,
    ) -> None:
        self._pebble = pebble
        self._object = object
        self._bank = bank
        self._filename = filename
        self._app_install_id = app_install_id
        obj_type_value = object_type
        if app_install_id is not None:
            obj_type_value |= 1 << 7
        self._object_type = PutBytesType(obj_type_value)
        EventSourceMixin.__init__(self)

    def send(self) -> None:
        """
        Sends the object to the watch. Block until completion.

        During transmission, a "progress" event will be periodically emitted with the following
        signature: ::
           (sent_this_interval, sent_so_far, total_object_size)

        Raises:
            PutBytesError: If the request fails.
        """
        # Prepare the watch to receive something.
        cookie = self._prepare()

        # Send it.
        self._send_object(cookie)

        # Commit it.
        self._commit(cookie)

        # Install it.
        self._install(cookie)

    def _assert_success(self, result: transfers.PutBytesResponse) -> None:
        if result.result == transfers.PutBytesResponse.Result.NACK:
            msg = "Watch NACKed PutBytes request."
            raise PutBytesError(msg)

    def _prepare(self) -> int:
        if self._app_install_id is not None:
            packet = transfers.PutBytesApp(
                data=transfers.PutBytesAppInit(
                    object_size=len(self._object),
                    object_type=self._object_type,
                    app_id=self._app_install_id,
                ),
            )
        else:
            packet = transfers.PutBytes(
                data=transfers.PutBytesInit(
                    object_size=len(self._object),
                    object_type=self._object_type,
                    bank=self._bank,
                    filename=self._filename,
                ),
            )
        result = self._pebble.send_and_read(packet, transfers.PutBytesResponse)
        self._assert_success(result)
        return result.cookie

    def _send_object(self, cookie: int) -> None:
        sent = 0
        length = 2000
        while sent < len(self._object):
            chunk = self._object[sent : sent + length]
            packet = transfers.PutBytes(data=transfers.PutBytesPut(cookie=cookie, payload=chunk))
            self._assert_success(self._pebble.send_and_read(packet, transfers.PutBytesResponse))
            sent += len(chunk)
            self._broadcast_event("progress", len(chunk), sent, len(self._object))

    def _commit(self, cookie: int) -> None:
        crc = stm32_crc.crc32(self._object)
        packet = transfers.PutBytes(data=transfers.PutBytesCommit(cookie=cookie, object_crc=crc))
        self._assert_success(self._pebble.send_and_read(packet, transfers.PutBytesResponse))

    def _install(self, cookie: int) -> None:
        packet = transfers.PutBytes(data=transfers.PutBytesInstall(cookie=cookie))
        self._assert_success(self._pebble.send_and_read(packet, transfers.PutBytesResponse))
