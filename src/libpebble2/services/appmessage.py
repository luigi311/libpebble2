__author__ = "katharine"

import struct
import uuid
from collections.abc import Mapping
from typing import ClassVar, cast

from libpebble2.communication import PebbleConnection
from libpebble2.events.mixin import EventSourceMixin
from libpebble2.protocol.appmessage import (
    AppMessage,
    AppMessageACK,
    AppMessageNACK,
    AppMessagePush,
    AppMessageTuple,
)
from libpebble2.protocol.base import PebblePacket

__all__ = [
    "AppMessageService",
    "ByteArray",
    "CString",
    "Int8",
    "Int16",
    "Int32",
    "Uint8",
    "Uint16",
    "Uint32",
]


class AppMessageService(EventSourceMixin):
    """
    Provides a mechanism for sending and receiving
    `AppMessages <https://developer.getpebble.com/docs/c/Foundation/AppMessage/>`_ to and from
    the Pebble.

    Incoming messages will trigger an ``appmessage`` event with the arguments
    ``(transaction_id, app_uuid, data)``, where ``data`` is a python :func:`dict`
    containing the received values as native Python types.

    :class:`AppMessageService` can also be used to interact with non-AppMessage endpoints that
    use the same protocol, such as the legacy app state endpoint.

    Args:
        pebble (PebbleConnection): The connection on which to operate.
        message_type (PebblePacket, optional): The endpoint to operate on, if not the default
        ``AppMessage`` endpoint.
    """

    _type_mapping: ClassVar[dict[tuple[AppMessageTuple.Type, int], str]] = {
        (AppMessageTuple.Type.Int, 1): "b",
        (AppMessageTuple.Type.Int, 2): "h",
        (AppMessageTuple.Type.Int, 4): "i",
        (AppMessageTuple.Type.Uint, 1): "B",
        (AppMessageTuple.Type.Uint, 2): "H",
        (AppMessageTuple.Type.Uint, 4): "I",
    }

    def __init__(self, pebble: PebbleConnection, message_type: type = AppMessage) -> None:
        self._pebble = pebble
        self._current_txid = 1
        self._pending_messages: dict[int, uuid.UUID] = {}
        self._message_type = message_type
        super().__init__()
        self._handle = self._pebble.register_endpoint(self._message_type, self._handle_message)

    def _handle_message(self, packet: PebblePacket) -> None:
        if not isinstance(packet, AppMessage):
            return

        if isinstance(packet.data, AppMessagePush):
            message = packet.data
            result = {}
            # Field descriptor at class-level; at instance-level this is a list
            tuples = cast("list[AppMessageTuple]", message.dictionary)
            for t in tuples:
                if not isinstance(t, AppMessageTuple):
                    continue

                if t.type == AppMessageTuple.Type.ByteArray:
                    result[t.key] = bytearray(cast("bytes", t.data))
                elif t.type == AppMessageTuple.Type.CString:
                    data_bytes = cast("bytes", t.data)
                    result[t.key] = data_bytes.split(b"\x00")[0].decode("utf-8", errors="replace")
                else:
                    (result[t.key],) = struct.unpack(
                        self._type_mapping[(t.type, t.length)],
                        cast("bytes", t.data),
                    )
            self._broadcast_event("appmessage", packet.transaction_id, message.uuid, result)
            self._pebble.send_packet(
                AppMessage(transaction_id=packet.transaction_id, data=AppMessageACK())
            )
        else:
            if packet.transaction_id in self._pending_messages:
                app_uuid = self._pending_messages[packet.transaction_id]
                del self._pending_messages[packet.transaction_id]
            else:
                app_uuid = None
            if isinstance(packet.data, AppMessageACK):
                self._broadcast_event("ack", packet.transaction_id, app_uuid)
            elif isinstance(packet.data, AppMessageNACK):
                self._broadcast_event("nack", packet.transaction_id, app_uuid)

    def send_message(
        self,
        target_app: uuid.UUID,
        dictionary: Mapping[int, "AppMessageType"],
    ) -> int:
        """
        Send a message to the given app, which should be currently running on the Pebble (unless
        using a non-standard AppMessage endpoint, in which case its rules apply).

        AppMessage can only represent flat dictionaries with integer keys; as such, ``dictionary``
        must be flat and have integer keys.

        Because the AppMessage dictionary type is more expressive than Python's native types allow,
        all entries in the dictionary provided must be wrapped in one of the value types:

        =======================  =============  ============
        AppMessageService type    C type        Python type
        =======================  =============  ============
        :class:`Uint8`           ``uint8_t``    :any:`int`
        :class:`Uint16`          ``uint16_t``   :any:`int`
        :class:`Uint32`          ``uint32_t``   :any:`int`
        :class:`Int8`            ``int8_t``     :any:`int`
        :class:`Int16`           ``int16_t``    :any:`int`
        :class:`Int32`           ``int32_t``    :any:`int`
        :class:`CString`         ``char *``     :any:`str`
        :class:`ByteArray`       ``uint8_t *``  :any:`bytes`
        =======================  =============  ============

        For instance: ::

           appmessage.send_message(UUID("6FEAF2DE-24FA-4ED3-AF66-C853FA6E9C3C"), {
               16: Uint8(62),
               6428356: CString("friendship"),
           })

        Args:
            target_app (uuid.UUID): The UUID of the app to which to send a message.
            dictionary (dict): The dictionary to send.

        Returns:
            int: The transaction ID sent message, as used in the ``ack`` and ``nack`` events.
        """
        tid = self._get_txid()
        message = self._message_type(transaction_id=tid)
        tuples = []
        for k, v in dictionary.items():
            if not isinstance(k, int):
                msg = "AppMessage keys must be ints"
                raise TypeError(msg)
            if isinstance(v, AppMessageNumber):
                fmt = self._type_mapping[(v.type, v.length)]
                tuples.append(AppMessageTuple(key=k, type=v.type, data=struct.pack(fmt, v.value)))
            elif isinstance(v, CString):
                tuples.append(
                    AppMessageTuple(key=k, type=v.type, data=v.value.encode("utf-8") + b"\x00"),
                )
            elif isinstance(v, ByteArray):
                tuples.append(AppMessageTuple(key=k, type=v.type, data=v.value))
            else:
                msg = f"Unsupported AppMessage value for key {k}: {type(v).__name__}"
                raise TypeError(msg)
        message.data = AppMessagePush(uuid=target_app, dictionary=tuples)
        self._pending_messages[tid] = target_app
        self._pebble.send_packet(message)
        return tid

    def shutdown(self) -> None:
        """
        Unregisters the :class:`AppMessageService` from the :class:`PebbleConnection` that was
        passed into the constructor.

        After calling this method, no more events will be fired.
        """
        self._pebble.unregister_endpoint(self._handle)

    def _get_txid(self) -> int:
        self._current_txid = 1 if self._current_txid >= 254 else self._current_txid + 1
        return self._current_txid


class AppMessageType:
    type = None
    length = None
    value: int | str | bytes

    def __init__(self, value: int | str | bytes) -> None:
        self.value = value


class AppMessageNumber(AppMessageType):
    value: int

    def __init__(self, value: int) -> None:
        super().__init__(value)

class Uint8(AppMessageNumber):
    """Represents a uint8_t."""

    type = AppMessageTuple.Type.Uint
    length = 1


class Uint16(AppMessageNumber):
    """Represents a uint16_t."""

    type = AppMessageTuple.Type.Uint
    length = 2


class Uint32(AppMessageNumber):
    """Represents a uint32_t."""

    type = AppMessageTuple.Type.Uint
    length = 4


class Int8(AppMessageNumber):
    """Represents an int8_t."""

    type = AppMessageTuple.Type.Int
    length = 1


class Int16(AppMessageNumber):
    """Represents an int16_t."""

    type = AppMessageTuple.Type.Int
    length = 2


class Int32(AppMessageNumber):
    """Represents an int32_t."""

    type = AppMessageTuple.Type.Int
    length = 4


class CString(AppMessageType):
    """Represents a char *."""

    type = AppMessageTuple.Type.CString
    value: str

    def __init__(self, value: str) -> None:
        super().__init__(value)


class ByteArray(AppMessageType):
    """Represents a uint8_t *."""

    type = AppMessageTuple.Type.ByteArray
    value: bytes

    def __init__(self, value: bytes) -> None:
        super().__init__(value)
