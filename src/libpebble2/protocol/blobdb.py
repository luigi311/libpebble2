__author__ = "katharine"

from enum import IntEnum

from .base import PebblePacket
from .base.types import BinaryArray, Uint8, Uint16, Union

__all__ = [
    "BlobCommand",
    "BlobDatabaseID",
    "BlobResponse",
    "BlobStatus",
    "ClearCommand",
    "DeleteCommand",
    "InsertCommand",
]


class InsertCommand(PebblePacket):
    """
    Represents an Insert command packet for the Pebble BlobDB protocol.

    This command is used to insert a key-value pair into the BlobDB database.
    The packet contains the following fields:
        - key_size (Uint8): The length of the key in bytes.
        - key (BinaryArray): The key data, with length specified by key_size.
        - value_size (Uint16): The length of the value in bytes.
        - value (BinaryArray): The value data, with length specified by value_size.
    """

    key_size = Uint8()
    key = BinaryArray(length=key_size)
    value_size = Uint16()
    value = BinaryArray(length=value_size)


class DeleteCommand(PebblePacket):
    """
    Represents a command to delete an entry from the BlobDB database.

    Attributes:
        key_size (Uint8): The size of the key to be deleted.
        key (BinaryArray): The key identifying the entry to delete, with length specified
            by key_size.
    """

    key_size = Uint8()
    key = BinaryArray(length=key_size)


class ClearCommand(PebblePacket):
    """
    Represents a command to clear all entries in the BlobDB.

    This class is used to send a clear operation to the Pebble device's BlobDB,
    removing all stored data of the specified type.

    Inheritance:
        PebblePacket: Base class for Pebble protocol packets.
    """


class BlobDatabaseID(IntEnum):
    """
    Enumeration of Blob Database IDs used in the Pebble protocol.

    Attributes:
        Test (int): Identifier for test blobs.
        Pin (int): Identifier for pin blobs.
        App (int): Identifier for application blobs.
        Reminder (int): Identifier for reminder blobs.
        Notification (int): Identifier for notification blobs.
        AppGlance (int): Identifier for AppGlance blobs.
    """

    Test = 0
    Pin = 1
    App = 2
    Reminder = 3
    Notification = 4
    AppGlance = 11


class BlobCommand(PebblePacket):
    """
    Represents a command packet for interacting with the Pebble's BlobDB database.

    Attributes:
        command (Uint8): The command type to execute (e.g., insert, delete, clear).
        token (Uint16): A unique token identifying the command instance.
        database (Uint8): The target BlobDB database, specified by BlobDatabaseID enum.
        content (Union): The command-specific content, determined by the value of `command`:
            - 0x01: InsertCommand
            - 0x04: DeleteCommand
            - 0x05: ClearCommand

    Meta:
        endpoint (int): The protocol endpoint for BlobDB commands (0xB1DB).
        register (bool): Indicates if the endpoint should be registered (False).
        endianness (str): Byte order for serialization ("<" for little-endian).
    """

    class Meta:
        """
        Meta class holds protocol configuration for the BlobDB endpoint.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0xB1DB).
            register (bool): Indicates if registration is required (False).
            endianness (str): Byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0xB1DB
        register = False
        endianness = "<"

    command = Uint8()
    token = Uint16()
    database = Uint8(enum=BlobDatabaseID)
    content = Union(
        command,
        {
            0x01: InsertCommand,
            0x04: DeleteCommand,
            0x05: ClearCommand,
        },
    )


class BlobStatus(IntEnum):
    """
    Enumeration representing possible status codes for BlobDB operations.

    Attributes:
        Success (int): Operation completed successfully.
        GeneralFailure (int): Operation failed due to a general error.
        InvalidOperation (int): The requested operation is not valid.
        InvalidDatabaseID (int): The specified database ID is invalid.
        InvalidData (int): The provided data is invalid.
        KeyDoesNotExist (int): The specified key does not exist in the database.
        DatabaseFull (int): The database is full and cannot accept more data.
        DataStale (int): The data is stale and may need to be refreshed.
        NotSupported (int): The requested operation is not supported.
        Locked (int): The database is currently locked.
        TryLater (int): The operation should be retried later.
    """

    Success = 0x01
    GeneralFailure = 0x02
    InvalidOperation = 0x03
    InvalidDatabaseID = 0x04
    InvalidData = 0x05
    KeyDoesNotExist = 0x06
    DatabaseFull = 0x07
    DataStale = 0x08
    NotSupported = 0x09
    Locked = 0xA
    TryLater = 0xB


class BlobResponse(PebblePacket):
    """
    Represents a response packet for BlobDB operations in the Pebble protocol.

    Attributes:
        token (Uint16): A unique identifier for the BlobDB request.
        response (Uint8): The status of the BlobDB operation, represented as a BlobStatus enum.

    Meta:
        endpoint (int): The protocol endpoint for BlobDB responses (0xB1DB).
        endianness (str): The byte order used for serialization ("<" for little-endian).
    """

    class Meta:
        """
        Meta class containing protocol configuration for BlobDB responses.

        Attributes:
            endpoint (int): The protocol endpoint for BlobDB responses (0xB1DB).
            endianness (str): The byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0xB1DB
        endianness = "<"

    token = Uint16()
    response = Uint8(enum=BlobStatus)
