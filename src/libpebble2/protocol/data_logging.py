__author__ = "katharine"

from enum import IntEnum

from .base import PebblePacket
from .base.types import (
    UUID,
    BinaryArray,
    Boolean,
    FixedList,
    Uint8,
    Uint16,
    Uint32,
    Union,
)

__all__ = [
    "DataLogging",
    "DataLoggingACK",
    "DataLoggingCloseSession",
    "DataLoggingDespoolOpenSession",
    "DataLoggingDespoolSendData",
    "DataLoggingEmptySession",
    "DataLoggingGetSendEnableRequest",
    "DataLoggingGetSendEnableResponse",
    "DataLoggingNACK",
    "DataLoggingReportOpenSessions",
    "DataLoggingSetSendEnable",
    "DataLoggingTimeout",
]


class DataLoggingReportOpenSessions(PebblePacket):
    """
    Represents a packet reporting open data logging sessions.

    Attributes:
        sessions (FixedList[Uint8]): A fixed-size list containing session identifiers as
            unsigned 8-bit integers.
    """

    sessions = FixedList(Uint8())


class DataLoggingDespoolOpenSession(PebblePacket):
    """
    Represents a packet for opening a data logging despool session on a Pebble device.

    Attributes:
        session_id (Uint8): Identifier for the despool session.
        app_uuid (UUID): UUID of the application associated with the data log.
        timestamp (Uint32): Timestamp indicating when the session was opened.
        log_tag (Uint32): Tag identifying the specific log.
        data_item_type (Uint8): Type of data items in the log, defined by ItemType enum.
        data_item_size (Uint16): Size of each data item in bytes.

    Classes:
        ItemType (IntEnum): Enum specifying the type of data items:
            - ByteArray (0x00): Raw byte array.
            - UnsignedInt (0x02): Unsigned integer.
            - SignedInt (0x03): Signed integer.
    """

    class ItemType(IntEnum):
        """
        Enumeration of item types used in data logging.

        Attributes:
            ByteArray (int): Represents a byte array item type (value: 0x00).
            UnsignedInt (int): Represents an unsigned integer item type (value: 0x02).
            SignedInt (int): Represents a signed integer item type (value: 0x03).
        """

        ByteArray = 0x00
        UnsignedInt = 0x02
        SignedInt = 0x03

    session_id = Uint8()
    app_uuid = UUID()
    timestamp = Uint32()
    log_tag = Uint32()
    data_item_type = Uint8(enum=ItemType)
    data_item_size = Uint16()


class DataLoggingDespoolSendData(PebblePacket):
    """
    Represents a packet sent during the data logging despool process.

    Attributes:
        session_id (Uint8): The identifier for the data logging session.
        items_left (Uint32): The number of items remaining to be sent.
        crc (Uint32): The CRC checksum for the data.
        data (BinaryArray): The actual data being sent in the packet.
    """

    session_id = Uint8()
    items_left = Uint32()
    crc = Uint32()
    data = BinaryArray()


class DataLoggingCloseSession(PebblePacket):
    """
    Represents a packet to close a data logging session on the Pebble device.

    Attributes:
        session_id (Uint8): The identifier of the data logging session to be closed.
    """

    session_id = Uint8()


class DataLoggingACK(PebblePacket):
    """
    Represents an acknowledgment packet for data logging operations.

    Attributes:
        session_id (Uint8): The identifier for the data logging session being acknowledged.
    """

    session_id = Uint8()


class DataLoggingNACK(PebblePacket):
    """
    Represents a negative acknowledgment (NACK) packet for data logging operations.

    Attributes:
        session_id (Uint8): The identifier for the data logging session that received the NACK.
    """

    session_id = Uint8()


class DataLoggingTimeout(PebblePacket):
    """
    Represents a timeout event in the Pebble data logging protocol.

    This packet is sent when a data logging operation exceeds the allowed time limit.
    """


class DataLoggingEmptySession(PebblePacket):
    """
    Represents an empty data logging session packet for Pebble communication.

    Attributes:
        session_id (Uint8): The identifier for the data logging session.
    """

    session_id = Uint8()


class DataLoggingGetSendEnableRequest(PebblePacket):
    """
    Represents a request packet to get the send enable status for data logging.

    Attributes:
        session_id (Uint8): The identifier for the data logging session.
    """

    session_id = Uint8()


class DataLoggingGetSendEnableResponse(PebblePacket):
    """
    Represents a response packet for the get send enable status request.

    Attributes:
        enabled (Boolean): Indicates whether data logging is enabled.
    """

    enabled = Boolean()


class DataLoggingSetSendEnable(PebblePacket):
    """
    Represents a request packet to set the send enable status for data logging.

    Attributes:
        session_id (Uint8): The identifier for the data logging session.
        enabled (Boolean): Indicates whether to enable or disable data logging.
    """

    session_id = Uint8()
    enabled = Boolean()


class DataLogging(PebblePacket):
    """
    Represents a Pebble data logging packet, used for communication with the Pebble device's data
    logging subsystem.

    Attributes:
        command (Uint8): The command identifier for the data logging operation.
        data (Union): The payload associated with the command, dynamically selected based on the
            command value.
            Supported command values and their corresponding payload types:
                0x01: DataLoggingDespoolOpenSession
                0x02: DataLoggingDespoolSendData
                0x03: DataLoggingCloseSession
                0x84: DataLoggingReportOpenSessions
                0x85: DataLoggingACK
                0x86: DataLoggingNACK
                0x07: DataLoggingTimeout
                0x88: DataLoggingEmptySession
                0x89: DataLoggingGetSendEnableRequest
                0x0A: DataLoggingGetSendEnableResponse
                0x8B: DataLoggingSetSendEnable

    Meta:
        endpoint (int): The protocol endpoint for data logging (0x1A7A).
        endianness (str): Byte order for serialization ("<" for little-endian).
    """

    class Meta:
        """
        Meta class containing protocol configuration for data logging.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0x1A7A).
            endianness (str): The byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0x1A7A
        endianness = "<"

    command = Uint8()
    data = Union(
        command,
        {
            0x01: DataLoggingDespoolOpenSession,
            0x02: DataLoggingDespoolSendData,
            0x03: DataLoggingCloseSession,
            0x84: DataLoggingReportOpenSessions,
            0x85: DataLoggingACK,
            0x86: DataLoggingNACK,
            0x07: DataLoggingTimeout,
            0x88: DataLoggingEmptySession,
            0x89: DataLoggingGetSendEnableRequest,
            0x0A: DataLoggingGetSendEnableResponse,
            0x8B: DataLoggingSetSendEnable,
        },
    )
